!                       *****************
                        SUBROUTINE LECSIM
!                       *****************
!
     &( X , Y , IKLE , NCOLOR , TITRE , NOP5 , NGEO )
!
!***********************************************************************
!   STBTEL V5P2
!***********************************************************************
!
!brief    Parsing geometry file created by the SIMAIL mesh generator
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| X,Y           |-->| Mesh coordinates
!| X1,Y1         |-->| Mesh coordinates read as single precision
!| IKLE          |<->| Connectivity
!| NCOLOR        |<--| Array of node colours
!| TITRE         |<->| Title of the study
!| NOP5          |-->| Working array for the parsing of sd
!| MESH          |<--| Mesh
!| NDP           |-->| Number of nodes per element
!| NPOIN         |<--| Total number of nodes in the mesh
!| NELEM         |<--| Total number of element in the mesh
!| NPMAX         |-->| Actual size of the node-based x and y arrays
!|               |   | (npmax = npoin + 0.1*nelem)
!| NELMAX        |-->| Actual size of the element6based arrays
!|               |   | (nelmax = nelem + 0.2*nelem)
!| NRES          |-->| Index refering to the serafin file
!| NGEO          |-->| Index refering to the mesh generator file
!| NLIM          |-->| Index refering to the dynam file
!| NFO1          |-->| Index refering to the triangle trigrid file
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELEM,MESH,NPOIN,NELMAX
      IMPLICIT NONE
!
      DOUBLE PRECISION, INTENT(INOUT) :: X(*) , Y(*)
      INTEGER, INTENT(INOUT) :: IKLE(NELMAX,4) , NCOLOR(*)
      CHARACTER(LEN=80), INTENT(INOUT) :: TITRE
      INTEGER, INTENT(INOUT) :: NOP5(*)
      INTEGER, INTENT(IN) :: NGEO
!
      INTEGER ERR
      INTEGER I,J,K
      INTEGER LONG, NTASD
      INTEGER NCGE, NMAE , NDSDE , NNO , NCOPNP ,NPO
      INTEGER INING, NBEGM , INDIC
!
      REAL, DIMENSION(:), ALLOCATABLE :: X1,Y1
!
!
      INTRINSIC DBLE
!
!-----------------------------------------------------------------------
!
      ALLOCATE(X1(NPOIN),STAT=ERR)
      ALLOCATE(Y1(NPOIN),STAT=ERR)
!
      IF(ERR.NE.0) THEN
        WRITE(LU,8000) ERR
8000    FORMAT(1X,'LECSIM: ERROR DURING ALLOCATION OF MEMORY: ',/,1X,
     &            'ERROR CODE: ',1I6)
      ENDIF
!
!=======================================================================
!     INITIALISATION
!=======================================================================
!
      REWIND NGEO
!
      DO I=1,NPOIN
        X(I) = 9999999.D0
        Y(I) = 9999999.D0
        NCOLOR(I) = 99999
      ENDDO
!
!=======================================================================
!     SEQUENTIAL FILE PARSING (1ST RECORD FOR SD)
!     FOR DUMMY RECORD, WE USE NOP5
!=======================================================================
!
      READ(NGEO,ERR=110,END=120) LONG,(NOP5(I),I=1,LONG)
!
!=======================================================================
!     SEQUENTIAL PARSING (NOP0 ARRAY). PARSING THE TITLE
!     FOR DUMMY RECORD, WE USE NOP5
!=======================================================================
!
      READ(NGEO,ERR=110,END=120) LONG,TITRE,(NOP5(I),I=1,11),NTASD
!
!=======================================================================
!     SEQUENTIAL PARSING (NOP1 ARRAY AND ASSOCIATED)
!     FOR DUMMY RECORD, WE USE NOP5
!=======================================================================
!
      IF (NTASD.GT.0) THEN
        READ(NGEO,ERR=110,END=120) LONG,(NOP5(I),I=1,LONG)
        DO I=1,NTASD
          READ(NGEO,ERR=110,END=120) LONG,(NOP5(J),J=1,LONG)
        ENDDO
      ENDIF
!
!=======================================================================
!     SEQUENTIAL PARSING (NOP2 ARRAY)
!     FOR DUMMY RECORD, WE USE NOP5
!=======================================================================
!
      READ(NGEO,ERR=110,END=120) LONG,(NOP5(I),I=1,LONG)
      NCOPNP = NOP5(4)
      NBEGM  = NOP5(25)
!
!=======================================================================
!     SEQUENTIAL PARSING (NOP3 ARRAY)
!     FOR DUMMY RECORD, WE USE NOP5
!=======================================================================
!
      IF (NBEGM.NE.0) THEN
        READ(NGEO,ERR=110,END=120) LONG,(NOP5(I),I=1,LONG)
      ENDIF
!
!=======================================================================
!     SEQUENTIAL PARSING OF THE NODE COORDINATES(NOP4 ARRAY)
!=======================================================================
!
      READ(NGEO,ERR=110,END=120) LONG,(X1(I),Y1(I),I=1,NPOIN)
      DO I=1,NPOIN
        X(I) = DBLE(X1(I))
        Y(I) = DBLE(Y1(I))
      ENDDO
!
!=======================================================================
!     SEQUENTIAL PARSING OF IKLE (NOP5 ARRAY)
!     FOR DUMMY RECORD, WE USE NOP5 AND LONG
!=======================================================================
!
      INDIC = 0
      READ(NGEO,ERR=110,END=120) LONG,(NOP5(I),I=1,LONG)
      DO I=1,NELEM
        INDIC = INDIC +1
        NCGE  = NOP5(INDIC)
        INDIC = INDIC +1
        NMAE  = NOP5(INDIC)
        INDIC = INDIC +1
        NDSDE = NOP5(INDIC)
        INDIC = INDIC +1
        NNO   = NOP5(INDIC)
! NNO : NUMBER OF NODES PER ELEMENT
        IF ( (NNO.EQ.4.AND.MESH.NE.2) .OR. (NNO.EQ.3.AND.MESH.NE.3) )
     &  THEN
          WRITE(LU,4000)
          CALL PLANTE(1)
          STOP
        ENDIF
        DO K=1,NNO
          INDIC = INDIC +1
          IKLE(I,K) = NOP5(INDIC)
        ENDDO
        IF (NCOPNP.NE.1) THEN
          INDIC = INDIC +1
          NPO = NOP5(INDIC)
          DO K=1,NPO
            INDIC = INDIC +1
          ENDDO
        ENDIF
!  NMAE :
        IF (NMAE.NE.0) THEN
          INDIC = INDIC +1
          INING = NOP5(INDIC)
          DO K=2,NMAE
            IF (INING.EQ.3) THEN
              INDIC = INDIC +1
              NCOLOR(IKLE(I,K-1)) = NOP5(INDIC)
            ELSE IF(INING.EQ.2) THEN
              INDIC = INDIC +1
              IF (K.GT.NNO+1) NCOLOR(IKLE(I,K-(NNO+1))) = NOP5(INDIC)
            ELSE IF(INING.EQ.1) THEN
              INDIC = INDIC +1
              IF (K.GT.2*NNO+1)
     &        NCOLOR(IKLE(I,K-(2*NNO+1))) = NOP5(INDIC)
            ENDIF
          ENDDO
        ENDIF
      ENDDO !I
!
      GOTO 80
!
 110  CONTINUE
      WRITE(LU,4100)
 120  CONTINUE
      WRITE(LU,4200)
!
 80   CONTINUE
!
!=======================================================================
!
      DEALLOCATE (X1)
      DEALLOCATE (Y1)
!
!=======================================================================
!
4000  FORMAT(//,'*********************************************',/,
     &          'LECSIM : THERE IS NO LINK BETWEEN THE NUMBER  ',/,
     &          'OF POINTS BY ELEMENT AND THE TYPE OF ELEMENTS ',/,
     &          '**********************************************',//)
4100  FORMAT(//,'**********************************************',/,
     &          'LECSIM : ERROR IN READING FILE SIMAIL         ',/,
     &          '**********************************************',//)
4200  FORMAT(//,'*************************************************',/,
     &          'LECSIM : ATTEMPT TO READ AFTER END OF FILE SIMAIL ',/,
     &          '*************************************************',//)
!
      RETURN
      END
