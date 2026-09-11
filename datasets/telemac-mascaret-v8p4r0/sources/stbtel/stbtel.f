!                       *****************
                        SUBROUTINE STBTEL
!                       *****************
!
     &( NPOIN1 , TYPELE , NFOND , PRECIS , NSFOND , TITRE)
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Main STBTEL subroutine
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| X,Y       |<--| Node coordinates
!| ZF        |<--| Node values
!| XR,YR     |<--| Bathymetric coordinates
!| ZR        |<--| Bathymetric values
!| NBAT      |-->| Number of bathymetric values
!| IKLE      |<--| Connectivity
!| IFABOR    |<--| Neighbouring numbers for each side
!| NBOR      |<--| Boundary node number
!| TRAV1,2   |<->| Working array
!| NCOLOR    |<--| Array of node colours
!| NCOLFR    |<--| Array of boundary node colours
!| NOP5      |-->| Working array for parsing simail geomerty file
!| NPOIN1    |-->| Actual number of bathymetric nodes
!|           |   | (npoin is the max node number because
!|           |   | supertab leave holes in the numbering
!| TYPELE    |-->| Element types
!| STD       |-->| Binary standard
!| DECTRI    |-->| Whether to split over-constrained triangles
!| FOND      |-->| Bathymetric file names
!| NFOND     |-->| Logical untis for bathymetric files
!| EPSI      |-->| Minimum distance between 2 nodes defining
!|           |   | duplicated nodes
!| COLOR     |<--| Node colours
!| ELIDEP    |-->| Whether to remave keywords
!| NBFOND    |-->| Number of bathymetric files
!| MAILLE    |-->| Name of the mesh generator
!| DM        |-->| Minimum distance to the border of the domain
!|           |   | for the projection of bathymetry
!| PRECIS    |-->| Parsing format for the node coordinates
!| FONTRI    |-->| Whether the bathymetry is within ngeo
!| CORTRI    |-->| Bathymetric correction for trigrid
!| TFAST1,2  |-->| Working array (fasttabs)
!| ADDFAS    |-->| Whetehr boundary conditions  are within fasttabs
!| VAR       |-->| Double prec. array to parse results
!| ELISEC    |-->| Whether to remove dried elemens
!| ELPSEC    |-->| Marker elim of partially dried elements
!| SEUSEC    |-->| Threshol definining wet/dry
!| ISDRY     |-->| Marker array for zero water depth
!| IHAUT     |-->| Index of water depth within the list of variables
!| MESH      |-->| Mesh
!| NDP       |-->| Number of nodes per element
!| NPOIN     |-->| Total number of nodes in the mesh
!| NELEM     |-->| Total number of elements in the mesh
!| NPMAX     |-->| Actual size of the node-based x and y arrays
!|           |   | (npmax = npoin + 0.1*nelem)
!| NELMAX    |-->| Actual size of the element6based arrays
!|           |   | (nelmax = nelem + 0.2*nelem)
!| NRES      |-->| Index refering to the serafin file
!| NGEO      |-->| Index refering to the mesh generator file
!| NLIM      |-->| Index refering to the dynam file
!| NFO1      |-->| Index refering to the triangle trigrid file
!| NSEC11    |-->| File pointer to nodes (single precision)
!| NSEC12    |-->| File pointer to nodes (double precision)
!| NSEC2     |-->| File pointer to elements
!| NSEC3     |-->| File pointers to the title
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE BIEF_DEF
      USE BIEF, ONLY : VOISIN
      USE DECLARATIONS_TELEMAC
      USE DECLARATIONS_STBTEL
      USE DECLARATIONS_SPECIAL
      USE INTERFACE_STBTEL, EX_STBTEL => STBTEL
!
      IMPLICIT NONE
!
      INTEGER, INTENT(INOUT) :: NPOIN1
      CHARACTER(LEN=11), INTENT(INOUT) :: TYPELE
      INTEGER, INTENT(IN) :: NFOND(5)
      CHARACTER(LEN=6), INTENT(INOUT) :: PRECIS
      INTEGER, INTENT(INOUT) :: NSFOND
      CHARACTER(LEN=80), INTENT(INOUT) :: TITRE
!
      INTEGER NPTFR , NITER, OLD_NPTFR
      INTEGER NDEPAR , IELM
!
!     DUMMY ARRAY USE ONLY BY NEIGHBOURS IN PARALLEL
      INTEGER NACHB(1)
!
      INTEGER NVAR , NVARCL
      INTEGER NPINIT , NEINIT
      INTEGER NUMPB(100), NBPB, I
      INTEGER :: IPARAM(10) = (/ 0,0,0,0,0,0,0,0,0,0 /)
!
      REAL, DIMENSION(:), ALLOCATABLE :: W
      DOUBLE PRECISION,DIMENSION(:)  ,ALLOCATABLE :: WORK,X,Y,ZF
      DOUBLE PRECISION,DIMENSION(:)  ,ALLOCATABLE :: XR,YR,ZR
      DOUBLE PRECISION,DIMENSION(:)  ,ALLOCATABLE :: XINIT,YINIT
      DOUBLE PRECISION,DIMENSION(:)  ,ALLOCATABLE :: VAINIT,VAR
      DOUBLE PRECISION,DIMENSION(:)  ,ALLOCATABLE :: CHBORD
      DOUBLE PRECISION,ALLOCATABLE :: HBOR(:),UBOR(:,:),VBOR(:,:)
      DOUBLE PRECISION,DIMENSION(:,:),ALLOCATABLE :: SHP
      INTEGER, DIMENSION(:)  , ALLOCATABLE :: TRAV1,TRAV2,TRAV3
      INTEGER, DIMENSION(:,:), ALLOCATABLE :: IKLE,IFABOR,IKINIT
      INTEGER, DIMENSION(:)  , ALLOCATABLE :: NBOR,KP1BOR,LIUBOR
      INTEGER, ALLOCATABLE :: OLD_NBOR(:)
      INTEGER, DIMENSION(:)  , ALLOCATABLE :: LIVBOR,LITBOR,LIHBOR
      INTEGER, DIMENSION(:)  , ALLOCATABLE :: ELT,NCOLOR,NCOLFR,NOP5
      INTEGER, DIMENSION(:),ALLOCATABLE :: TFAST1,TFAST2,ISDRY,IPOBO
!
!
      CHARACTER(LEN=32) TEXTE(26) , VARCLA(1)
!
      LOGICAL SORLEO(26)
      LOGICAL SUIT , ECRI , DEBU , LISTIN
!
      INTEGER DATE(3) , TIME(3)
      INTEGER X_ORIG,Y_ORIG
      DOUBLE PRECISION TPSFIN(1)
      INTEGER NVARIN , NVAROU , NVAR2 ,ERR
      INTEGER NSOR , MXPTVS , MXELVS
      TYPE(BIEF_OBJ) :: DUMMY
!
!
!     DYNAMIC ALLOCATION OF SINGLE PRECISION ARRAY
!
      ALLOCATE(W(NPOIN)       ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'W')
      ALLOCATE(WORK(NPMAX)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'WORK')
      ALLOCATE(X(NPMAX)       ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'X')
      ALLOCATE(Y(NPMAX)       ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'Y')
      ALLOCATE(ZF(NPMAX)      ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'ZF')
      ALLOCATE(XR(NBAT)       ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'XR')
      ALLOCATE(YR(NBAT)       ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'YR')
      ALLOCATE(ZR(NBAT)       ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'ZR')
      ALLOCATE(XINIT(NPOIN)   ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'XINIT')
      ALLOCATE(YINIT(NPOIN)   ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'YINIT')
      ALLOCATE(VAINIT(NPOIN)  ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'VAINIT')
      ALLOCATE(VAR(NPMAX)     ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'VAR')
      ALLOCATE(SHP(NPMAX,3)   ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'SHP')
      ALLOCATE(NOP5(INOP5)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'NOP5')
!
!     DYNAMIC ALLOCATION OF INTEGER ARRAY
!
      ALLOCATE(TRAV1(4*NELMAX)  ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'TRAV1')
      ALLOCATE(TRAV2(4*NELMAX)  ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'TRAV2')
      ALLOCATE(TRAV3(NPMAX)     ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'TRAV3')
      ALLOCATE(NCOLOR(NPMAX)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'NCOLOR')
      ALLOCATE(IKLE(NELMAX,4)   ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'IKLE')
      ALLOCATE(IKINIT(NELEM,3)  ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'IKINIT')
      ALLOCATE(IFABOR(NELMAX,4) ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'IFABOR')
      ALLOCATE(ELT(NPMAX)       ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'ELT')
      ALLOCATE(TFAST1(NPMAX)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'TFAST1')
      ALLOCATE(TFAST2(NPMAX)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'TFAST2')
      ALLOCATE(ISDRY(NPMAX)     ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'ISDRY')
!     NPTFR REPLACED BY NPMAX (BY EXCESS VALUE)
      ALLOCATE(NBOR(NPMAX)      ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'NBOR')
      ALLOCATE(OLD_NBOR(NPMAX)      ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'OLD_NBOR')
      ALLOCATE(KP1BOR(NPMAX)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'KP1BOR')
      ALLOCATE(LIUBOR(NPMAX)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'LIUBOR')
      ALLOCATE(LIVBOR(NPMAX)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'LIVBOR')
      ALLOCATE(LITBOR(NPMAX)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'LITBOR')
      ALLOCATE(LIHBOR(NPMAX)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'LIHBOR')
      ALLOCATE(NCOLFR(NPMAX)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'NCOLFR')

      ALLOCATE(CHBORD(NPMAX)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'CHBORD')
      ALLOCATE(HBOR(NPMAX)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'HBOR')
      ALLOCATE(UBOR(NPMAX,2)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'UBOR')
      ALLOCATE(VBOR(NPMAX,2)    ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'VBOR')

!
!=======================================================================
!     PARSING NODE COORDINATES AND COLOURS, OF IKLE AND OF THE TITLE
!=======================================================================
!
      NVARIN = 0
      NPTFR = 1
      NPINIT = NPOIN
      NEINIT = NELEM
!
      TYP_ELEM = TRIANGLE_ELT_TYPE
      ALLOCATE(IPOBO(NPOIN)     ,STAT=ERR)
      CALL CHECK_ALLOCATE(ERR,'IPOBO')
      IF (MAILLE.EQ.'SELAFIN') THEN
        CALL LECSEL (XINIT,YINIT,IKINIT,NPINIT,NEINIT,X,Y,IKLE,TRAV1,
     &               W,TITRE,TEXTE,NVARIN,NVAR2,STD,FUSION,
     &               NGEO,NFO1,IPOBO,IPARAM,DATE,TIME,X_ORIG,Y_ORIG)
        IF(NOMBND2(1:1) .NE. ' ') THEN
          CALL LECSELLIM (NGEO,LIHBOR,LIUBOR,LIVBOR,HBOR,UBOR,VBOR,
     &                    CHBORD,NBOR,NPMAX,NPTFR,NCOLOR)
        ENDIF
      ELSEIF (MAILLE.EQ.'ADCIRC') THEN
        CALL LECADC (X,Y,ZF,IKLE,NGEO)
        NSFOND=1
      ELSEIF (MAILLE.EQ.'SIMAIL') THEN
        CALL LECSIM (X,Y,IKLE,NCOLOR,TITRE,NOP5,NGEO)
      ELSEIF (MAILLE.EQ.'TRIGRID') THEN
        CALL LECTRI (X,Y,IKLE,NCOLOR,NGEO,NFO1)
        TITRE = 'MAILLAGE TRIGRID'
      ELSEIF (MAILLE.EQ.'FASTTABS') THEN
        CALL LECFAS (X,Y,IKLE, NCOLOR, TFAST1, TFAST2, ADDFAS,
     &               NGEO , NFO1)
        TITRE = 'MAILLAGE FASTTABS'
      ELSE
        TYP_ELEM = QUADRANGLE_ELT_TYPE
        CALL LECSTB (X,Y,IKLE,NCOLOR,TITRE,NPOIN1,
     &               NGEO,NSEC2,NSEC3,NSEC11,NSEC12)
      ENDIF
!
!=======================================================================
!     PARSING OF THE MESH
!=======================================================================
!
      IF(MESH.EQ.3.AND.NSOM.GE.3) THEN
        CALL EXTRAC(X,Y,SOM,IKLE,TRAV1,NELEM,NELMAX,NPOIN,NSOM,PROJEX)
      ENDIF
!
!=======================================================================
!     PRINT OUT GEOMETRICAL DATA AND PARAMETERS
!=======================================================================
!
      CALL IMPRIM(NPOIN1,NPOIN,TYPELE,NELEM,TITRE,MAILLE,PRECIS)
!
!=======================================================================
!     DIVIDING ALL ELEMENTS BY 4 TRIANGLES
!=======================================================================
!
      IF(MESH.EQ.3.AND.DIV4) THEN
        CALL DIVISE(X,Y,IKLE,NCOLOR,NPOIN,NELEM,NELMAX,NSOM2,
     &              TRAV1,TRAV2,SHP,ELT,NPMAX)
        OLD_NPTFR = NPTFR
        OLD_NBOR = NBOR
      ELSE
        IF(DIV4) WRITE(LU,3901)
      ENDIF
!
!=======================================================================
!     OPTION TO REMOVE DRIED OR PARTIALLY DRIED ELEMENTS
!=======================================================================
!
      IF(ELISEC) THEN
        IF(MESH.EQ.3) THEN
          WRITE(LU,3007)
          CALL ELMSEC ( ELPSEC, SEUSEC, TPSFIN, X, Y, IKLE,
     &    NCOLOR, ISDRY, IHAUT, NVARIN, VAR, W , TRAV2, STD ,NGEO,TEXTE)
!
!     AFTER REMOVAL, LOOKING FOR BOUNDARY NODES CAUSING TROUBLE
!
          CALL VERIFI(X,Y,IKLE,NCOLOR,TRAV1,EPSI,
     &                MESH,NDP,NPOIN,NELEM,NELMAX)
          IELM = 11
          CALL VOISIN(IFABOR,NELEM,NELMAX,IELM,IKLE,NELMAX,NPOIN,
     &                       NACHB,NBOR,NPTFR,TRAV1,TRAV2)
          CALL VERIFS (IFABOR,IKLE,TRAV1,NPTFR,NUMPB,NBPB)
          IF (NBPB.GT.0) THEN
            DO I=1,NBPB
              WRITE(LU,3001) NUMPB(I)
            ENDDO
            CALL ELMPB (NBPB, NUMPB, X,Y,IKLE,NCOLOR,ISDRY,TRAV2)
          ELSE
            WRITE(LU,3009)
          ENDIF
        ELSE
          WRITE(LU,4002)
        ENDIF
      ENDIF
!
!=======================================================================
!     FORMATTING MESH TO THE TELEMAC STANDRAD
!=======================================================================
!
      IF(.NOT.DIV4) THEN
        CALL VERIFI(X,Y,IKLE,NCOLOR,TRAV1,EPSI,
     &              MESH,NDP,NPOIN,NELEM,NELMAX)
      ENDIF
!
!=======================================================================
!     BUILDING THE ARRAY IFABOR
!=======================================================================
!
      IELM = 21
      IF (MESH.EQ.3) IELM = 11
!
      CALL VOISIN(IFABOR,NELEM,NELMAX,IELM,IKLE,NELMAX,NPOIN,
     &            NACHB,NBOR,NPTFR,TRAV1,TRAV2)
!
!=======================================================================
!     BUILDING OF BOUNDARY NODE NUMBERS
!    (SORTED BY TRIGONOMETRIC ORDER FOR THE OUTTER BOUNDARY AND IN
!     REVERSE ORDER FOR THE ISLAND)
!=======================================================================
!
      CALL RANBO(NBOR,KP1BOR,IFABOR,IKLE,NCOLOR,TRAV1,NPTFR,X,Y,
     &           NCOLFR,NDP,NPOIN,NELEM,NELMAX,MESH)
!
!=======================================================================
!     SETTING BOUDNARY INFO AFTER A REFINEMENT
!=======================================================================
!
      IF(MESH.EQ.3.AND.DIV4) THEN
!     FILL_LIM ONLY WORKS IF THE WHOLE MESH IS REFINED
        IF(NSOM.LT.3) THEN
          CALL FILL_LIM
     &   (OLD_NPTFR,NPMAX,0,LIHBOR,LIUBOR,LIVBOR,DUMMY,
     &    HBOR,UBOR,VBOR,CHBORD,DUMMY,DUMMY,DUMMY,NBOR,OLD_NBOR,KP1BOR)
        ENDIF
      ENDIF
!
!=======================================================================
!     REMOVING OVER-CONSTRAINED TRIANGLES
!=======================================================================
!
      IF(MESH.EQ.3.AND.DECTRI) THEN
!
        CALL SURCON (X,Y,IKLE,TRAV1,NBOR,NPTFR,NCOLOR,IFABOR,COLOR)
!
      ELSE
        IF (DECTRI) WRITE(LU,3900)
      ENDIF
!
!=======================================================================
!     RENUMBERING NODES FOR ASSEMBLING OPTIMISATION
!=======================================================================
!
      IF(OPTASS) THEN
        IF(DIV4.OR.NSOM2.GT.0) THEN
          WRITE(LU,*) 'RENUMBERING IS NOT POSSIBLE IF '//
     &                'YOU ARE DOING A REFINEMENT.'
          WRITE(LU,*) 'YOU WILL NEED TO DO IT IN ANOTHER RUN'
          CALL PLANTE(1)
          STOP
        ENDIF
        CALL RENUM
     &  (X,Y,WORK,IKLE,NBOR,TRAV1,TRAV2,TRAV3,NCOLOR,COLOR,NPTFR)
      ENDIF
!
!=======================================================================
!     RENUMBERING ELEMENTS TO AVOID BACKWARD DEPENDENCIES
!=======================================================================
!
      IF (ELIDEP) THEN
!
        WRITE(LU,3011)
        CALL SHUFLE (IKLE,X)
!
        NITER = 0
!
10      CONTINUE
!
        CALL CORDEP (IKLE,LGVEC)
!
!=======================================================================
!       CHECKING BACKWARD DEPENDENCIES
!=======================================================================
!
        CALL DEPARR (IKLE,NDEPAR,LGVEC)
        IF(NDEPAR.NE.0) THEN
          NITER = NITER + 1
          IF (NITER.GT.50) THEN
            WRITE(LU,4000)
            CALL PLANTE(1)
            STOP
          ENDIF
          GOTO 10
        ENDIF
!
        WRITE(LU,4100) NITER
!
      ENDIF
!
!=======================================================================
!     BATHYMETRIC INTERPOLATION ON THE MESH
!=======================================================================
!
      IF(NBFOND.NE.0) THEN
        CALL PROJEC (X,Y,ZF,XR,YR,ZR,NBAT,NBOR,NPTFR,NFOND,NBFOND,
     &               FOND,DM,FONTRI,CORTRI,MAILLE,NGEO,KP1BOR)
      ENDIF
!
!=======================================================================
!     BUILDING THE GEOMETRY FILE IN SELAFIN FORM
!=======================================================================
!
      WRITE(LU,3003)
      NVARCL= 0
      DEBU  = .FALSE.
      SUIT  = .FALSE.
      ECRI  = .TRUE.
      LISTIN= .TRUE.
!
      NSOR = 26
!     IF THE DATE IS MISSING
      IF(IPARAM(10).EQ.0) THEN
        DATE(1) = 0
        DATE(2) = 0
        DATE(3) = 0
        TIME(1) = 0
        TIME(2) = 0
        TIME(3) = 0
      ENDIF
!
      CALL PRESEL(IKLE,TRAV1,NELEM,NELMAX,NDP,TEXTE,NBFOND,SORLEO,
     &            COLOR,NSFOND,NVARIN,NVAROU,MAILLE)
!
!     CAREFUL WHEN CALLING FM3SEL, THE TRUE IKLE IS IN TRAV1
!       AND IKLE IS USED AS A WORKING ARRAY
!
      CALL FM3SEL(X,Y,NPOIN,NBOR,NRES,STD,NVAR,TEXTE,TEXTE,
     &            VARCLA,NVARCL,TITRE,SORLEO,NSOR,W,TRAV1,IKLE,
     &            TRAV2,NELEM,NPTFR,NDP,MXPTVS,MXELVS,DATE,TIME,
     &            DEBU,SUIT,ECRI,LISTIN,IPARAM,IPOBO,X_ORIG,Y_ORIG)
!
!     INTERPOLATION OF INPUT VARIABLES
!
      IF(MAILLE.EQ.'SELAFIN'.AND..NOT.DIV4) THEN
        CALL INTERP(XINIT,YINIT,IKINIT,NPINIT,NEINIT,X,Y,NPOIN,
     &              NPMAX,SHP,ELT)
      ENDIF
!
      IF(ELISEC) THEN
!       WRITTING OUTPUT VARIABLES IN SELAFIN
        CALL ECRSEL (VAINIT,IKINIT,NPINIT,NEINIT,SHP,ELT,NPOIN,NPOIN1,
     &             NPMAX,W,X,ZF,NSFOND,NCOLOR,COLOR,VAR,NVARIN,NVAROU,
     &             0, 'STD', .FALSE., NRES, NGEO, 0, MAILLE, TEXTE)
      ELSE
!       WRITTING OUTPUT VARIABLES IN SELAFIN
        CALL ECRSEL(VAINIT,IKINIT,NPINIT,NEINIT,SHP,ELT,NPOIN,NPOIN1,
     &             NPMAX,W,X,ZF,NSFOND,NCOLOR,COLOR,VAR,NVARIN,NVAROU,
     &             NVAR2,STD,FUSION,NRES,NGEO,NFO1,MAILLE,TEXTE)
      ENDIF
!
!=======================================================================
!     BUILDING THE DYNAM FILE OF TELEMAC
!=======================================================================
!
      WRITE(LU,3005)
      IF(DIV4 .AND. NOMBND2(1:1).NE.' ') THEN
        CALL WRITESELLIM
     &(NRES,LIHBOR,LIUBOR,LIVBOR,HBOR,UBOR(:,1),VBOR(:,1),
     & CHBORD,NBOR,NPMAX,NPTFR)
      ELSE
        CALL DYNAMI (NPTFR,NBOR,LIHBOR,LIUBOR,LIVBOR,LITBOR,
     &              NCOLFR,MAILLE,NRES)
      ENDIF
!
 3900 FORMAT(//,'********************************************',/,
     &          'OVERSTRESSED ELEMENTS ARE CANCELLED ONLY IN',/,
     &          'THE CASE OF TRIANGLES                     ',/,
     &          '********************************************',/)
 3901 FORMAT(//,'********************************************',/,
     &          'ELEMENTS CAN BE CUT IN FOUR ONLY IN',/,
     &          'THE CASE OF TRIANGLES                     ',/,
     &          '********************************************',/)
 4000 FORMAT(//,'***********************************************',/,
     &          'FAILURE IN CANCELLING BACKWARD DEPENDENCIES    ',/,
     &          '         (NUMBER OF ATTEMPTS : 50)             ',/,
     &          'THERE MUST BE TOO FEW NODES IN THE MESH        ',/,
     &          '***********************************************')
 4100 FORMAT(1X,'BACKWARD DEPENDENCIES ARE CANCELLED AFTER ',I2,
     &          ' ATTEMPTS')
!
 4002 FORMAT(//,'***********************************************',/,
     &          'MESH DRY ELEMENT SUPPRESION NOT AVAILABLE FOR ',
     &          'NON TRIANGULAR MESH.',/,
     &          '***********************************************')
!
 3001 FORMAT(1X,'THE POINT NUMBER ',I6,' HAS TO BE REMOVED')
 3003 FORMAT(//,1X,'GENERATING GEOMETRY FILE',/,
     &         1X,'------------------------')
 3005 FORMAT(//,1X,'TREATMENT OF BOUNDARY CONDITIONS',/,
     &         1X,'--------------------------------')
 3007 FORMAT(//,1X,'MESH DRY ELEMENT SUPPRESSION',
     &        /,1X,'----------------------------',/)
 3009 FORMAT(/,1X,'NO CONNECTED ISLAND')
 3011 FORMAT(//,1X,'ELIMINATION OK BACKWARDS DEPENDENCIES',
     &        /,1X,'------------------------------------',/)
!
      DEALLOCATE(W)
      DEALLOCATE(WORK)
      DEALLOCATE(X)
      DEALLOCATE(Y)
      DEALLOCATE(ZF)
      DEALLOCATE(XR)
      DEALLOCATE(YR)
      DEALLOCATE(ZR)
      DEALLOCATE(XINIT)
      DEALLOCATE(YINIT)
      DEALLOCATE(VAINIT)
      DEALLOCATE(VAR)
      DEALLOCATE(SHP)
      DEALLOCATE(NOP5)
      DEALLOCATE(TRAV1)
      DEALLOCATE(TRAV2)
      DEALLOCATE(TRAV3)
      DEALLOCATE(NCOLOR)
      DEALLOCATE(IKLE)
      DEALLOCATE(IKINIT)
      DEALLOCATE(IFABOR)
      DEALLOCATE(ELT)
      DEALLOCATE(TFAST1)
      DEALLOCATE(TFAST2)
      DEALLOCATE(ISDRY)
      DEALLOCATE(NBOR)
      DEALLOCATE(OLD_NBOR)
      DEALLOCATE(KP1BOR)
      DEALLOCATE(LIUBOR)
      DEALLOCATE(LIVBOR)
      DEALLOCATE(LITBOR)
      DEALLOCATE(LIHBOR)
      DEALLOCATE(NCOLFR)

      DEALLOCATE(CHBORD)
      DEALLOCATE(HBOR)
      DEALLOCATE(UBOR)
      DEALLOCATE(VBOR)
      DEALLOCATE(IPOBO)
!
!-----------------------------------------------------------------------
!
      RETURN
      END
