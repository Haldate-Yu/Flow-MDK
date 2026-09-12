!                       ****************
                        SUBROUTINE RANBO
!                       ****************
!
     &(NBOR,KP1BOR,IFABOR,IKLE,NCOLOR,TRAV1,NPTFR,X,Y,NCOLFR,
     & NDP,NPOIN,NELEM,NELMAX,MESH)
!
!***********************************************************************
! STBTEL  V5P2
!***********************************************************************
!
!brief  Building the table of boundary segments
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| NBOR     |<--| Array of boundary node numbers
!| IFABOR   |-->| Array of neighbouring elements for each side
!| IKLE     |-->| Connectivity
!| NCOLOR   |-->| Array of node colours
!| NCOLFR   |<--| Array of boundary node colours
!| TRAV1    |<->| Working array
!| NPTFR    |<--| Number of boundary nodes
!| MESH     |-->| Elements types
!| NDP      |-->| Number of nodes per element
!| NPOIN    |-->| Total number of nodes
!| NELEM    |-->| Total number of elements
!| NELMAX   |-->| Actual size of arrays associated to elements
!|          |   | (nelmax = nelem + 0.2*nelem)
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER, INTENT(IN)    :: NDP,NELMAX,MESH,NELEM,NPOIN
      INTEGER, INTENT(INOUT) :: NPTFR
      INTEGER, INTENT(INOUT) :: NBOR(*),KP1BOR(*),NCOLFR(*)
      INTEGER, INTENT(INOUT) :: TRAV1(NPOIN,2)
      INTEGER, INTENT(IN)    :: IFABOR(NELMAX,*),IKLE(NELMAX,NDP)
      INTEGER, INTENT(IN)    :: NCOLOR(*)
      DOUBLE PRECISION, INTENT(IN) :: X(NPOIN),Y(NPOIN)
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER IILE,NILE,I,ISUIV,IELEM,IFACE,NOEUD1,NOEUD2
      INTEGER IERROR, I1, I2
!
      DOUBLE PRECISION SOM1,SOM2,Y2
!
      LOGICAL SWAP
!
      INTEGER :: SOMSUI(4) = (/ 2 , 3 , 4 , 0 /)
      DOUBLE PRECISION, PARAMETER :: EPSILO = 1.D-6
!
!=======================================================================
!     INITIALISATION
!=======================================================================
!
      SOMSUI(NDP) = 1
      IF (MESH.NE.2.AND.MESH.NE.3) THEN
        WRITE(LU,4000) MESH
4000    FORMAT(/,1X,'RANBO : MESH NOT ALLOWED , MESH = ',I4,/)
        CALL PLANTE(1)
        STOP
      ENDIF
!
!=======================================================================
!     LOOK FOR BOUNDARY SEGMENTS, NUMBERED FROM 1 TO NPTFR
!=======================================================================
!
      NPTFR = 0
      DO IELEM=1,NELEM
        DO IFACE=1,NDP
          IF(IFABOR(IELEM,IFACE).LE.0) THEN
            NPTFR = NPTFR + 1
            TRAV1(NPTFR,1) = IKLE(IELEM,       IFACE )
            TRAV1(NPTFR,2) = IKLE(IELEM,SOMSUI(IFACE))
          ENDIF
        ENDDO
      ENDDO
!
!=======================================================================
!     CHECKING THAT EACH NODE APPEARES ONLY TWICE
!     ( ONCE AS NODE 1 , ONCE AS NODE 2 )
!=======================================================================
!
      IERROR = 0
      DO I=1,NPTFR
        I1 = 1
        I2 = 1
        DO ISUIV=1,NPTFR
          IF (TRAV1(I,1).EQ.TRAV1(ISUIV,2)) I1 = I1 + 1
          IF (TRAV1(I,2).EQ.TRAV1(ISUIV,1)) I2 = I2 + 1
        ENDDO
        IF (I1.NE.2) THEN
          IERROR = IERROR + 1
          WRITE(LU,1020) X(TRAV1(I,1)),Y(TRAV1(I,1)),I1
        ENDIF
        IF (I2.NE.2) THEN
          IERROR = IERROR + 1
          WRITE(LU,1020) X(TRAV1(I,2)),Y(TRAV1(I,2)),I2
        ENDIF
      ENDDO
!
1020  FORMAT(1X,'ERROR ON BOUNDARY NODE :',/,
     &       1X,'X=',F13.3,'  Y=',F13.3,/,
     &       1X,'IT BELONGS TO',I2,' BOUNDARY SEGMENT(S)')
!
      IF (IERROR.GT.0) THEN
        CALL PLANTE(1)
        STOP
      ENDIF
!
!=======================================================================
!     SORTING BOUNDARY SEGMENTS BOUT A BOUT.
!     WE START ARBITRARILY BY THE NODE FARTHERS TO THE SOUTH-WEST
!     ( OR THE SOUTHERLY NODE IF CONFLICT ) TO ENSURE THE START IS ON
!     THE DOMAINE BOUNDARY AND NOT ON AN ISLAND
!=======================================================================
!
      SOM2 = X(1) + Y(1)
      Y2   = Y(1)
!
      DO I=1,NPTFR
!
        SOM1 = X(TRAV1(I,1)) + Y(TRAV1(I,1))
        IF (ABS(SOM1-SOM2).LE.ABS(EPSILO*SOM1)) THEN
          IF (Y(TRAV1(I,1)).LE.Y2) THEN
            Y2    = Y(TRAV1(I,1))
            SOM2  = SOM1
            ISUIV = I
          ENDIF
        ELSEIF (SOM1.LE.SOM2) THEN
          Y2    = Y(TRAV1(I,1))
          SOM2  = SOM1
          ISUIV = I
        ENDIF
!
      ENDDO
!
      NOEUD1 = TRAV1(ISUIV,1)
      NOEUD2 = TRAV1(ISUIV,2)
      TRAV1(ISUIV,1) = TRAV1(1,1)
      TRAV1(ISUIV,2) = TRAV1(1,2)
      TRAV1(1,1) = NOEUD1
      TRAV1(1,2) = NOEUD2
!
      IILE = 0
      NILE = 1
!
      DO I=2,NPTFR
        SWAP = .FALSE.
!
!=======================================================================
!     LOOKING OFR THE BOUDNARY SEGMENT HAVING ITS FIRST NODE IDENTICAL
!     TO THE SECOND NODE OF THE PREVIOUS BOUNDARY SEGMENT
!=======================================================================
!
        DO ISUIV=I,NPTFR
!
          IF (TRAV1(ISUIV,1).EQ.TRAV1(I-1,2)) THEN
!
!=======================================================================
!     SWAPPING SEGMENTS BETWEEN NUMBERS I+1 AND ISUIV
!=======================================================================
!
            NOEUD1 = TRAV1(ISUIV,1)
            NOEUD2 = TRAV1(ISUIV,2)
            TRAV1(ISUIV,1) = TRAV1(I,1)
            TRAV1(ISUIV,2) = TRAV1(I,2)
            TRAV1(I,1) = NOEUD1
            TRAV1(I,2) = NOEUD2
            KP1BOR(I+NPTFR) = I-1
            KP1BOR(I-1) = I
            SWAP = .TRUE.
            EXIT
!
          ENDIF
!
        ENDDO
        IF(SWAP) CYCLE
!
!=======================================================================
!       IF THE FOLLOWING NODE INDEX IS NOT FOUND WE CHECK THAT THE LAST
!       FOUND NODE IS IDENTICAL TO THE FIRST, THERFORE CLOSING THE
!       POLYGON AND CARRYING ON WITH THE NEXT POLYGON
!=======================================================================
!
        IF (TRAV1(NILE,1).NE.TRAV1(I-1,2)) THEN
!
!=======================================================================
!       OTHERWISE THERE IS AN ERROR
!=======================================================================
!
          WRITE(LU,4500) TRAV1(I-1,2)
4500      FORMAT(1X,'ERROR IN STORING THE EDGE SEGMENTS',/,
     &           1X,'FOR THE NODE ',I5)
          CALL PLANTE(1)
          STOP
        ENDIF
!
        KP1BOR(NILE+NPTFR) = I-1
        KP1BOR(I-1) = NILE
        IILE = IILE+1
        NILE = I
!
      ENDDO! ISUIV
!
!=======================================================================
!     CHECKING TAHT THE LAST RECORD LINE IS CLOSED
!=======================================================================
!
      IF (TRAV1(NILE,1).NE.TRAV1(NPTFR,2)) THEN
        WRITE(LU,5000) TRAV1(NILE,1),TRAV1(NPTFR,2)
5000    FORMAT(1X,'ERROR, THE BOUNDARY IS NOT CLOSED :',/,
     &         1X,'FIRST POINT :',I5,2X,'LAST POINT : ',I5)
        CALL PLANTE(1)
        STOP
      ENDIF
!
      KP1BOR(NILE+NPTFR) = NPTFR
      KP1BOR(NPTFR) = NILE
!
      WRITE(LU,5500) NPTFR
      WRITE(LU,5600) IILE
 5500 FORMAT(1X,'NUMBER OF BOUNDARY POINTS      : ',I5)
 5600 FORMAT(1X,'NUMBER OF ISLANDS              : ',I5)
!
!=======================================================================
!     SETTING THE ARRAY NBOR AND
!     SAVING COLOURS FOR BOUDARY NODES IN NCOLFR
!=======================================================================
!
      DO I=1,NPTFR
        NBOR(I      ) = TRAV1(I,1)
        NBOR(I+NPTFR) = TRAV1(I,2)
        NCOLFR(I) = NCOLOR(TRAV1(I,1))
      ENDDO
!
      RETURN
      END
