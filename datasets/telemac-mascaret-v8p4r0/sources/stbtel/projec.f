!                       *****************
                        SUBROUTINE PROJEC
!                       *****************
!
     &(X , Y , ZF , XRELV , YRELV , ZRELV , NBAT ,
     & NBOR , NPTFR , NFOND , NBFOND , FOND , DM ,
     & FONTRI , CORTRI , MAILLE,NGEO,KP1BOR)
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Interpolation of bathymetric values onto the mesh
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| X,Y         |-->| Mesh coordinates
!| ZF          |<--| Bottom values
!| XRELV,YRELV |-->| Bathymetric coordinates
!| ZRELV       |-->| Bathymetric values
!| NBAT        |-->| Number of bathymetric values
!| NBOR        |-->| Numbering of the boundary nodes
!| NPTFR       |-->| Number of boundary nodes
!| NFOND       |-->| Logical units of bathymetric files
!| NBFOND      |-->| Number of bathymetric files (5 maxi)
!| FOND        |-->| Names of the bathymetric files
!| DM          |-->| Minimum distance to the doamin border for
!|             |   | The bathymetric interpolation
!| FONTRI      |-->| Whether bathymetric values are in trigrid
!| CORTRI      |-->| Correction of bathymetric value for trigrid
!| MESH        |-->| Mesh
!| NDP         |-->| Number of node per element
!| NPOIN       |-->| Total number of nodes in the mesh
!| NELEM       |-->| Total number of elements in the mesh
!| NPMAX       |-->| Actual siwe of the x and y arrays
!|             |   | (npmax = npoin + 0.1*nelem)
!| NELMAX      |-->| Actual size of the arrays to do with elements
!|             |   | (nelmax = nelem + 0.2*nelem)
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NPOIN
      USE INTERFACE_STBTEL, EX_PROJEC => PROJEC
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) :: NPTFR, NBAT, NBFOND
      INTEGER, INTENT(IN) :: NFOND(*) , NBOR(NPTFR,2)
      INTEGER, INTENT(IN) :: NGEO, KP1BOR(NPTFR)
      DOUBLE PRECISION, INTENT(INOUT) :: XRELV(*) , YRELV(*) , ZRELV(*)
      DOUBLE PRECISION, INTENT(IN) :: X(*) , Y(*) , DM
      DOUBLE PRECISION, INTENT(IN) :: CORTRI
      DOUBLE PRECISION, INTENT(INOUT) :: ZF(*)
      CHARACTER(LEN=72), INTENT(IN) :: FOND(NBFOND)
      CHARACTER(LEN=9), INTENT(IN) ::  MAILLE
      LOGICAL, INTENT(IN) :: FONTRI
!
      INTEGER I , NPT , IVOIS
      INTEGER NP(5)
      DOUBLE PRECISION DIST , DIST2
!
!=======================================================================
!     PARSING BATHYMETRIC FILES
!=======================================================================
!
      CALL LECFON (XRELV,YRELV,ZRELV,NBAT,NFOND,NBFOND,NP,NPT,
     &             FONTRI,CORTRI,MAILLE,NGEO)
!
      IF (.NOT.FONTRI) THEN
        IF (NBFOND.NE.0) WRITE(LU,4000)
!
        DO I = 1,NBFOND
          WRITE(LU,4100) I,FOND(I),I,NP(I)
        ENDDO
      ENDIF
!
!=======================================================================
!     INTERPOLATING BATHYMETRY AT NODE I FROM SROUNDING BATHYMETRIC
!     VALUES from WITHIN THE DOMAINE
!=======================================================================
!
      CALL FASP (X,Y,ZF,NPOIN,XRELV,YRELV,ZRELV,NPT,NBOR,KP1BOR,
     &           NPTFR,DM)
!
!=======================================================================
!     SOME NODES MIGHT NOT HAVE BEEN PROCESSED THROUGH FASP (BECAUSE OF
!     LACK OF BATHYMETRIC DATA). THESE WOULD HAVE BEEN SET TO -1.E6.
!     THE NEAREST VALUE IS THEREFORE SET AT THOSE NODES.
!=======================================================================
!
      DO I=1,NPOIN
        IF(ZF(I).LT.-0.9D6) THEN
          DIST = 1.D12
          DO IVOIS = 1 , NPOIN
            DIST2 = ( X(I)-X(IVOIS) )**2 + ( Y(I)-Y(IVOIS) )**2
            IF(DIST2.LT.DIST.AND.ZF(IVOIS).GT.-0.9D6) THEN
              DIST = DIST2
              ZF(I) = ZF(IVOIS)
            ENDIF
          ENDDO
          WRITE(LU,4200) I,X(I),Y(I),ZF(I)
        ENDIF
      ENDDO
!
!-----------------------------------------------------------------------
!
 4000 FORMAT(//,1X,'INTERPOLATION OF BOTTOM TOPOGRAPHY FROM :',/,
     &          1X,'-----------------------------------------',/)
 4100 FORMAT(1X,'BOTTOM ',I1,' : ',A72,/,
     &       1X,'NUMBER OF POINTS READ IN THE BOTTOM TOPOGRAPHY FILE ',
     &       I1,' : ',I6,/)
 4200 FORMAT('POINT : ',I5,' X = ',F10.1,' Y = ',F10.1,
     &       '  NO DATA , ZF : ',F8.2)
!
      RETURN
      END
