!                       *****************
                        SUBROUTINE LECSTB
!                       *****************
!
     &( X , Y ,IKLE , NCOLOR , TITRE , NPOIN1 ,
     &  NGEO , NSEC2,NSEC3,NSEC11,NSEC12)
!
!***********************************************************************
!   STBTEL V5P2
!***********************************************************************
!
!brief    Parsing geometry file created by the SUPERTAB mesh generator
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| X,Y       |-->| Mesh coordinates
!| IKLE      |<->| Connectivity
!| NCOLOR    |<--| Array of node colours
!| TITRE     |<->| Title of the study
!| TRAV1,2   |<->| Working arrays
!| MESH      |<--| Mesh
!| NDP       |-->| Number of nodes per element
!| NPOIN     |<--| Total number of nodes in the mesh
!| NELEM     |<--| Total number of element in the mesh
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
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELEM,MESH,NPOIN,NELMAX
      IMPLICIT NONE
!
      DOUBLE PRECISION, INTENT(INOUT) :: X(*) , Y(*)
      INTEGER, INTENT(INOUT) :: IKLE(NELMAX,4) , NCOLOR(*)
      CHARACTER(LEN=80), INTENT(INOUT) :: TITRE
      INTEGER, INTENT(IN) :: NPOIN1
      INTEGER, INTENT(IN) :: NGEO
      INTEGER, INTENT(IN) :: NSEC11 , NSEC12 , NSEC2 , NSEC3
!
      INTEGER INDIC3 , NSEC , N1 , N2 ,NCOLOI
      INTEGER INDIC1 , INDIC2 , I
!
      DOUBLE PRECISION X2 , Y2
      REAL X1 , Y1
!
      CHARACTER(LEN=2)  MOINS1
      CHARACTER(LEN=4)  BLANC
!
      INTRINSIC DBLE
!
!=======================================================================
!     INITIALISATION
!=======================================================================
!
      INDIC1 = 0
      INDIC2 = 0
      INDIC3 = 0
      REWIND NGEO
!
      DO I=1,NPOIN
        X(I) = 9999999.D0
        Y(I) = 9999999.D0
        NCOLOR(I) = 99999
      ENDDO
!
!=======================================================================
!     SEQUENTIAL PARSING IN PARTICULAR INDICES NSEC1, NSEC2 AND NSEC3
!=======================================================================
!
 10   READ(NGEO,1000,ERR=110,END=120) BLANC,MOINS1
      IF (MOINS1.NE.'-1'.OR.BLANC.NE.'    ') GOTO 10
 1000 FORMAT(A4,A2)
!
 20   READ(NGEO,2000,ERR=110,END=120) NSEC
      IF (NSEC.EQ.-1) THEN
        GOTO 20
!
!=======================================================================
!     PARSING OF THE TITLE
!=======================================================================
!
      ELSE IF (NSEC.EQ.NSEC3) THEN
        INDIC3 = 1
        READ(NGEO,25,ERR=110,END=120) TITRE
 25     FORMAT(A80)
!
!=======================================================================
!     PARSING OF THE COORDINATES AND OF NODE COLOURS
!=======================================================================
!
!     PARSING IN SINGLE PRECISION
!
      ELSE IF (NSEC.EQ.NSEC11) THEN
        INDIC1 = 1
!
        DO I=1,NPOIN1
          READ(NGEO,35,ERR=110,END=120) NSEC,N1,N2,NCOLOI,X1,Y1
!
!     PARSING IN DOUBLE PRECISION
!
          X(NSEC) = DBLE(X1)
          Y(NSEC) = DBLE(Y1)
          NCOLOR(NSEC) = NCOLOI
        ENDDO
!
 35     FORMAT(4I10,2E13.5)
!
        GOTO 50
!
!     PARSING DOUBLE PRECISION
!
      ELSE IF (NSEC.EQ.NSEC12) THEN
        INDIC1 = 1
!
        DO I=1,NPOIN1
          READ(NGEO,36,ERR=110,END=120) NSEC,N1,N2,NCOLOI
          READ(NGEO,37,ERR=110,END=120) X2,Y2
          X(NSEC) = X2
          Y(NSEC) = Y2
          NCOLOR(NSEC) = NCOLOI
        ENDDO
!
 36     FORMAT(4I10)
 37     FORMAT(2D25.16)
!
        GOTO 50
!
!=======================================================================
!       PARSING OF THE IKLE
!=======================================================================
!
      ELSE IF (NSEC.EQ.NSEC2) THEN
        INDIC2 = 1
        DO I=1,NELEM
          IF (MESH.EQ.2) THEN
            READ(NGEO,2000,ERR=110,END=120) NSEC
            READ(NGEO,4000,ERR=110,END=120) IKLE(I,1),IKLE(I,2),
     &                                       IKLE(I,3),IKLE(I,4)
          ELSE IF (MESH.EQ.3) THEN
            READ(NGEO,2000,ERR=110,END=120) NSEC
            READ(NGEO,4000,ERR=110,END=120) IKLE(I,1),IKLE(I,2),
     &                                       IKLE(I,3)
          ELSE
            WRITE(LU,4400) MESH
 4400       FORMAT(2X,'TYPE OF MESH NOT AVAILABLE : MESH = ',I3)
            CALL PLANTE(1)
            STOP
          ENDIF
        ENDDO
        GOTO 50
!
      ENDIF
!
 50   IF (INDIC1.EQ.1.AND.INDIC2.EQ.1.AND.INDIC3.EQ.1) THEN
        GOTO 60
      ELSE
        GOTO 10
      ENDIF
!
 110  CONTINUE
      WRITE(LU,4100)
      CALL PLANTE(1)
      STOP
 120  CONTINUE
      WRITE(LU,4200)
      CALL PLANTE(1)
      STOP
!
 60   CONTINUE
!
 2000 FORMAT(I10)
 4000 FORMAT(4I10)
 4100 FORMAT(/,'****************************************',/,
     &         'ERROR IN READING UNIVERSAL FILE (LECSTB)',/,
     &         '****************************************')
 4200 FORMAT(/,'******************************************',/,
     &         'END OF THE UNIVERSAL FILE : ERROR (LECSTB)',/,
     &         '******************************************')
!
      RETURN
      END
