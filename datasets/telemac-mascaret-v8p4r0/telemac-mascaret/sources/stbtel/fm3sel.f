!                       *****************
                        SUBROUTINE FM3SEL
!                       *****************
!
     &(X,Y,NPOIN,NBOR,NFIC,STD,NVAR,TEXTE,TEXTLU,VARCLA,NVARCL,
     & TITRE,SORLEO,NSOR,W,IKLE,
     & IKLES,ITRAV,NELEM,NPTFR,NDP,MXPTVS,MXELVS,DATE,TIME,
     & DEBU,SUIT,ECRI,LISTIN,IPARAM,IPOBO,X_ORIG,Y_ORIG)
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    As for FMTSEL, but the size of SORLEO is parameterised
!+         + Read the GEO file (SELAFIN format)
!+         + Write the GEO file (SELAFIN format)
!+        This subroutine can be driven using the arguments
!+         DEBU, SUIT, ET ECRI
!
!warning
!+        1) if DEBU, SUIt and ECRIT are .FALSE.
!+        2) if DEBU, ITRAV must be the integer array IA
!+           and we must not use IKLE nor IKLES because the
!+           pointer subroutine has not been called yet
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| HBOR      |<->| Prescribed depth
!| X,Y       |<->| Coordinates
!| NPOIN     |<->| Number of nodes in the mesh
!| NBOR      |-->| Global numbering of boundary nodes
!| NFIC      |-->| File index of the file to be read or written
!| STAND     |-->| Not used
!| STD       |-->| File binary type (std, ibm, i3e)
!| NVAR      |<->| Number of variables in the file
!| TEXTE     |<->| Names and units of the variables
!| TEXTLU    |<->| Names and units of the variables to be read
!| VARCLA    |-->| Array of clandestine variables
!| NVARCL    |-->| Number of clandestine variables
!| TITRE     |<->| Title of the file
!| SORLEO    |-->| Variables that we wish to write to (26 bools)
!| NSOR      |-->| Size of solrleo
!| W         |-->| Working array as float, size npoin
!| IKLE      |<->| Connectivity (i.e. transfering from local
!|           |   | node numbering of un element to the global
!|           |   | numbering
!| IKLES     |-->| Working array used to modify ikle
!|           |   | of size nelem * ndp
!| ITRAV     |-->| Integer working array of size npoin
!| NELEM     |<->| Number of elements in the mesh
!| NPTFR     |<->| Number of boundary nodes in the domaine
!| NDP       |<->| Number of node per element
!| DEBU      |-->| The file is read first to count the number of
!|           |   | nodes with which we will allocate the pointers
!| SUIT      |-->| The header part of the geo file is read first
!|           |   | to place the file pointer to the first record
!| ECRI      |-->| We here write the header part of the geo file
!| LISTIN    |-->| Information written on the log file (or not)
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
!    HEADER OF THE SELAFIN FILE
!
!      1    : TITLE
!      2    : NUMBER OF VARIABLES AND CLANDESTINE VARIABLES
!      3    : NAMES AND UNITS OF THE VARIABLES
!      4    : 1,0,0,0,0,0,0,0,0,0
!      5    : NELEM,NPOIN,NDP,1
!      6    : IKLE
!      7    : IPOBO, ARRAY OF SIZE NPOIN, 0 = INT.NODE, NOT OTHERWISE
!      8    : X
!      9    : Y
!
!     WHAT IS NOT DONE IN FM3SEL.
!
!     10    : TIME
!     11    : ACTUAL VARIABLES IN THE ORDER DEFINED ABOVE
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY : TYP_BND_ELEM, TYP_ELEM,
     &                                NPTIR, OUT_FORMAT
      USE INTERFACE_STBTEL, EX_FM3SEL => FM3SEL
      USE INTERFACE_HERMES
      IMPLICIT NONE
!
      DOUBLE PRECISION, INTENT(IN) :: X(*),Y(*)
      REAL, INTENT(INOUT) :: W(*)
!                     IKLE(NELEM,NDP) IKLES(NDP,NELEM)
      INTEGER, INTENT(IN) :: NBOR(*)
      INTEGER, INTENT(INOUT) :: IKLE(*),IKLES(*),ITRAV(*)
      INTEGER, INTENT(INOUT) :: NPOIN,NVAR,MXPTVS,MXELVS,TIME(3),DATE(3)
      INTEGER, INTENT(IN) :: NFIC,NVARCL,NSOR
      INTEGER, INTENT(INOUT) :: NELEM,NPTFR,NDP
      INTEGER, INTENT(IN) :: IPARAM(10),IPOBO(*)
      LOGICAL, INTENT(IN) :: DEBU,SUIT,ECRI,LISTIN,SORLEO(*)
      CHARACTER(LEN=3), INTENT(IN) :: STD
      CHARACTER(LEN=72), INTENT(IN) :: TITRE
!                        NSOR      NSOR+NVARCL
      CHARACTER(LEN=32), INTENT(IN) :: TEXTE(*),VARCLA(NVARCL)
      CHARACTER(LEN=32), INTENT(INOUT) :: TEXTLU(*)
      INTEGER, INTENT(IN) :: X_ORIG, Y_ORIG
!
      INTEGER IELEM,I,IB(10)

      CHARACTER(LEN=32), ALLOCATABLE :: VAR_INFO(:)
      INTEGER DATETIME(6), IVAR, IERR
      CHARACTER(LEN=80) :: TITSEL
!
!-----------------------------------------------------------------------
!
      IF(ECRI) THEN
        ! COMPUTE NVAR
        NVAR=0
        DO I=1,NSOR
          IF(SORLEO(I)) NVAR = NVAR + 1
        ENDDO
        NVAR = NVAR + NVARCL

        ALLOCATE(VAR_INFO(NVAR))
        IVAR = 1
        DO I=1,NSOR
          IF(SORLEO(I)) THEN
            VAR_INFO(IVAR) = TEXTE(I)(1:32)
            IVAR = IVAR + 1
          ENDIF
        ENDDO
        IF(NVARCL.NE.0) THEN
          DO I=1,NVARCL
            VAR_INFO(IVAR) = VARCLA(I)(1:32)
            IVAR = IVAR + 1
          ENDDO
        ENDIF


        TITSEL = REPEAT(' ', 80)
        TITSEL(1:72) = TITRE

        CALL SET_HEADER(OUT_FORMAT,NFIC,TITSEL,NVAR,VAR_INFO,IERR)

        IF(NPTIR.EQ.0) THEN
          DO I=1,NPOIN
            ITRAV(I) = 0
          ENDDO
          DO I =1,NPTFR
            ITRAV(NBOR(I)) = I
          ENDDO
        ELSE
          ITRAV(1:NPTFR) = 0
        ENDIF

        CALL SET_MESH(OUT_FORMAT,NFIC,2,TYP_ELEM,NDP,NPTFR,NPTIR,
     &                NELEM,NPOIN,IKLE,ITRAV(1:NPOIN),ITRAV(1:NPOIN),
     &                X,Y,0,DATE,TIME,X_ORIG,Y_ORIG,IERR)

      ELSE IF (DEBU) THEN
        CALL GET_MESH_CONNECTIVITY(OUT_FORMAT,NFIC,TYP_ELEM,
     &          ITRAV(1+NPOIN:NELEM*NDP+NPOIN+1),NELEM,NDP,IERR)

        CALL GET_BND_IPOBO(OUT_FORMAT,NFIC,NPOIN,NPTFR,
     &                     TYP_BND_ELEM,ITRAV(1:NPOIN),IERR)
        NPTFR = 0
        IF(NPOIN.GE.1) THEN
          DO I = 1 , NPOIN
            IF(ITRAV(I).NE.0) NPTFR = NPTFR + 1
          ENDDO
        ENDIF
!       ITRAV(1) : IPOBO  ITRAV(1+NPOIN) : IKLES
!       ITRAV(1+NPOIN+NDP*NELEM) : TABLEAU DE TRAVAIL.
        CALL MXPTEL(MXPTVS,MXELVS,ITRAV(1+NPOIN),
     &              ITRAV(1+NPOIN+NDP*NELEM),
     &              NPOIN,NELEM,NDP,ITRAV,LISTIN)
!       IPOBO EST MODIFIE PAR MXPTEL

      ELSE
        ! LIT ACTION
        CALL GET_MESH_DATE(OUT_FORMAT,NFIC,DATETIME,IERR)
        CALL CHECK_CALL(IERR, 'FM3SEL:GET_MESH_DATA')
        DATE = DATETIME(1:3)
        TIME = DATETIME(4:6)

        CALL GET_MESH_NELEM(OUT_FORMAT,NFIC,TYP_ELEM,NELEM,IERR)
        CALL CHECK_CALL(IERR, 'GET_MESH_NELEM:TRIA')

        CALL GET_MESH_NPOIN(OUT_FORMAT,NFIC,TYP_ELEM,NPOIN,IERR)
        CALL CHECK_CALL(IERR, 'GET_MESH_NPOIN:TRIA')

        CALL GET_MESH_CONNECTIVITY(OUT_FORMAT,NFIC,TYP_ELEM,IKLES,
     &                             NELEM,NDP,IERR)
        CALL CHECK_CALL(IERR, 'GET_MESH_CONNECTIVITY:TRIA')

        CALL GET_MESH_NPOIN_PER_ELEMENT(OUT_FORMAT,NFIC,TYP_ELEM,
     &                                  IB(3),IERR)

        DO I      = 1,NDP
          DO IELEM  = 1,NELEM
            IKLE((I-1)*NELEM+IELEM) = IKLES((IELEM-1)*NDP+I)
          ENDDO
        ENDDO
      ENDIF
!
      IF(DEBU.AND.LISTIN) THEN
        WRITE(LU,301) TITRE
        WRITE(LU,501) NPTFR,NELEM,NPOIN
        IF(NPOIN.LT.3.OR.NPTFR.LT.3.OR.NPTFR.GE.NPOIN) THEN
          WRITE(LU,24) NPOIN,NPTFR
          CALL PLANTE(1)
          STOP
        ENDIF
      ENDIF
!
!-----------------------------------------------------------------------
!
!  LISTING FORMAT :
!
24    FORMAT(1X,'FM3SEL : NUMBER OF POINTS IN THE MESH: ',1I9,/,1X,
     &          '         NUMBER OF BOUNDARY POINTS: ',1I9,/,1X,
     &          '         WRONG DATA, PROGRAMME STOPPED')
301   FORMAT(1X,//,1X,'TITLE: ',A72,/)
501   FORMAT(1X,'NUMBER OF BOUNDARY POINTS: ',1I9,/,1X,
     &'NUMBER OF ELEMENTS:',1I9,/,1X,'NUMBER OF POINTS:',1I9)
!
!-----------------------------------------------------------------------
!
      RETURN
      END
