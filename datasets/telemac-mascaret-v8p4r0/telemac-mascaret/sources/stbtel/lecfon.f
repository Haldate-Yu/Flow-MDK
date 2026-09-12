!                       *****************
                        SUBROUTINE LECFON
!                       *****************
!
     &( XRELV , YRELV , ZRELV , NBAT , NFOND , NBFOND ,  NP ,
     &  NPT , FONTRI , CORTRI , MAILLE, NGEO )
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Parsing bathymetric files
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!|  XRELV,YRELV | -->| bathymetric coordinates
!|  ZRELV       | -->| Bathymetric values
!|  NBAT        | -->| Number of bathymetric values
!|  NFOND       | -->| Logical units of the bathymetric files
!|  NBFOND      | -->| Number of bathymetric files (5 maxi)
!|  FOND        | -->| Names of the bathymetric files
!|  NP          | -->| Number of bathymetric values read by lecfon
!|  NPT         | -->| Total number of bathymetric values
!|  FONTRI      | -->| File pointer to the trigrid bathyemtric values
!|  CORTRI      | -->| Corrective values for trigrid bathymetric values
!|  MAILLE      | -->| Name of the mesh generator
!|  NRES        | -->| Index for the geometrie file
!|  NGEO        | -->| Index for the universal file
!|  NLIM        | -->| Index for the dynam file
!|  NFO1        | -->| Index for the trigrid triangl file
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
!
      DOUBLE PRECISION, INTENT(INOUT) :: XRELV(*) , YRELV(*) , ZRELV(*)
      INTEGER, INTENT(IN) :: NFOND(*) , NBAT , NBFOND
      INTEGER, INTENT(INOUT) :: NP(5), NPT
      LOGICAL, INTENT(IN) :: FONTRI
      DOUBLE PRECISION, INTENT(IN) :: CORTRI
      CHARACTER(LEN=9), INTENT(IN) ::  MAILLE
      INTEGER, INTENT(IN) :: NGEO
!
      INTEGER I
      INTEGER IDUMMY , ITRI
!
!     SIMGLE PRECISION (USE TO LOAD SINUSX FILE DATA)
!
      REAL   XSP , YSP , ZSP
!
      CHARACTER(LEN=1)  C
!
      CHARACTER(LEN=80) LIGNE
!
!
      INTRINSIC DBLE
!
!=======================================================================
!     INITIALISATION
!=======================================================================
!
      DO I=1,NBAT
        XRELV(I)=0.D0
        YRELV(I)=0.D0
        ZRELV(I)=0.D0
      ENDDO
!
!=======================================================================
!     PARSING BATHYMETRIC FILES
!=======================================================================
!
      NP(1) = 0
      NP(2) = 0
      NP(3) = 0
      NP(4) = 0
      NP(5) = 0
      NPT   = 0
!
!     IN CASE OF TRIGRID, IF FONTRI=TRUE BATHY IS READ DIRECTLY FROM
!     THE UNIVERSAL FILE, OTHERWISE COMMON PROCESSING APPLIES.
!
      IF (FONTRI) THEN
        IF (MAILLE.EQ.'TRIGRID') THEN
          WRITE (LU,4040)
          REWIND (NGEO)
          READ (NGEO,'(//)')
1         CONTINUE
            READ (NGEO,*,END=9000,ERR=9000) IDUMMY,XSP,YSP,ITRI,ZSP
            NPT = NPT + 1
            XRELV(NPT) = DBLE(XSP)
            YRELV(NPT) = DBLE(YSP)
            ZRELV(NPT) = DBLE(-ZSP) + CORTRI
            GOTO 1
9000      CONTINUE
          NP(1) = NPT
          WRITE (LU,4050) NPT
        ELSEIF (MAILLE.EQ.'FASTTABS') THEN
!
          WRITE (LU,4070)
          REWIND (NGEO)
2         CONTINUE
            READ (NGEO,'(A)',END=9010,ERR=8000) LIGNE
            IF (LIGNE(1:3).EQ.'GNN') THEN
              READ(LIGNE(4:80),*,ERR=8000,END=8000) IDUMMY,XSP,YSP,ZSP
              NPT = NPT + 1
              XRELV(NPT) = DBLE(XSP)
              YRELV(NPT) = DBLE(YSP)
              ZRELV(NPT) = DBLE(ZSP)
            ENDIF
            GOTO 2
9010      CONTINUE
        ENDIF
!
      ELSE
!
        DO I = 1,NBFOND
!
          REWIND NFOND(I)
30        READ(NFOND(I),1000,END=40) C
          IF (C(1:1).NE.'C'.AND.C(1:1).NE.'B') THEN
            BACKSPACE ( UNIT = NFOND(I) )
            NP(I)=NP(I)+1
            NPT  =NPT +1
            IF (NPT.GT.NBAT) THEN
              WRITE(LU,4020) NBAT
              CALL PLANTE(1)
              STOP
            ENDIF
!
!     PARSING THE SINUSX SINGLE PRECISION THEN -> DOUBLE PRECISION
!
            READ (NFOND(I),*) XSP,YSP,ZSP
            XRELV(NPT) = DBLE(XSP)
            YRELV(NPT) = DBLE(YSP)
            ZRELV(NPT) = DBLE(ZSP)
!
          ENDIF
          GOTO 30
40        CONTINUE
          IF (NP(I).EQ.0) THEN
            WRITE(LU,4030) I
            CALL PLANTE(1)
            STOP
          ENDIF
!
        ENDDO! I
      ENDIF
!
!
      RETURN
 8000 CONTINUE
      WRITE (LU,4001)
 4001 FORMAT (//,1X,'****************************'
     &        ,/,1X,'SUBROUTINE LECFON:'
     &        ,/,1X,'ERROR READING FASTTABS FILE.'
     &        ,/,1X,'****************************')
      CALL PLANTE(1)
      STOP
!
!-----------------------------------------------------------------------
!
1000  FORMAT(A1)
4020  FORMAT(/,'****************************************************',/,
     &         'THE NUMBER OF BATHYMETRIC POINTS IS     ',/,
     &         'GREATER THAN:',                                  1I6,/,
     &         'CHANGE THE FOLLOWING PARAMETER ',/,
     &         'IN THE STEERING FILE: ',/,
     &         'MAXIMUM NUMBER OF BATHYMETRIC POINTS '             ,/,
     &         '****************************************************')
4030  FORMAT(/,'******************************************',/,
     &         'THE BOTTOM TOPOGRAPHY FILE ',I1,' IS EMPTY|',/,
     &         '******************************************',/)
4040  FORMAT(/,'****************************************',/,
     &         'SUBROUTINE LECFON',/,
     &         'READING BATHYMETRY IN TRIGRID MESH FILE',/
     &         '****************************************',/)
4050  FORMAT(/,'****************************************',/,
     &         'SUBROUTINE LECFON',/,
     &         'NUMBER OF BATHYMETRIC POINTS IN TRIGRID FILE : ',
     &         I5,/
     &         '****************************************',/)
4070  FORMAT(/,'****************************************',/,
     &         'SUBROUTINE LECFON',/,
     &         'NUMBER OF BATHYMETRIC POINTS IN FASTTABS FILE: ',
     &         I5,/
     &         '****************************************',/)
!
      END SUBROUTINE
