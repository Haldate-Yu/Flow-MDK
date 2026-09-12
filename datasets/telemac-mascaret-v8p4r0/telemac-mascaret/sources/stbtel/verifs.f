!                       *****************
                        SUBROUTINE VERIFS
!                       *****************
!
     &(IFABOR,IKLE,TRAV1,NPTFR,NUMPB,NBPB)
!
!***********************************************************************
! STBTEL  V5P2
!***********************************************************************
!
!brief    Removing gaps in the node numbering and re-ordering elements
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| X,Y       |<--| Node coordinates
!| IKLE      |<->| Connectivity
!| TRAV1     |<->| Working array
!| NBOR      |-->| Boundary node number
!| NPTFR     |-->| Array of boundary nodes
!| NCOLOR    |<--| Array of node colours
!| IFABOR    |<->| Array of neighbouring elements for each side
!| NUMPB     |<--| Node numbers that cause trouble
!| NBPB      |<--| Number of nodes that cause trouble
!| MESH      |-->| Mesh
!| NDP       |-->| Number of nodes per element
!| NPOIN     |-->| Total number of nodes in the mesh
!| NELEM     |-->| Total number of elements in the mesh
!| NPMAX     |-->| Actual size of the node-based x and y arrays
!|           |   | (npmax = npoin + 0.1*nelem)
!| NELMAX    |-->| Actual size of the element6based arrays
!|           |   | (nelmax = nelem + 0.2*nelem)
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) :: IFABOR(NELMAX,*) , IKLE(NELMAX,4)
      INTEGER, INTENT(INOUT) :: TRAV1(NPOIN,2)
      INTEGER, INTENT(INOUT) :: NPTFR
      INTEGER, INTENT(INOUT) :: NUMPB(100), NBPB
!
      INTEGER I, J
      INTEGER ISUIV , IELEM , IFACE
      INTEGER I1 , I2
      LOGICAL EXIST
!
!      DATA SOMSUI / 2 , 3 , 4 , 0 /
      INTEGER :: SOMSUI(4) = (/ 2 , 3 , 4 , 0 /)
!
!=======================================================================
!     INITIALISATION
!=======================================================================
!
      WRITE(LU,1020)
      NBPB = 0
      SOMSUI(NDP) = 1
      IF (MESH.NE.2.AND.MESH.NE.3) THEN
        WRITE(LU,4000) MESH
4000    FORMAT(/,1X,'RANBO : MESH NOT ALLOWED , MESH = ',I4,/)
        CALL PLANTE(1)
        STOP
      ENDIF
!
!=======================================================================
!     FIND BOUNDARY SEGMENTS NUMBERED FROM 1 TO NPTFR
!=======================================================================
!
      NPTFR = 0
      DO IELEM=1,NELEM
        DO IFACE=1,NDP
          IF (IFABOR(IELEM,IFACE).LE.0) THEN
            NPTFR = NPTFR + 1
            TRAV1(NPTFR,1) = IKLE(IELEM,       IFACE )
            TRAV1(NPTFR,2) = IKLE(IELEM,SOMSUI(IFACE))
          ENDIF
        ENDDO
      ENDDO
!
!=======================================================================
!     CHECKING THAT NODE ARE LISTED ONLY TWICE
!     ( ONCE AS NODE 1 , ONCE AS NODE 2 )
!=======================================================================
!
      DO I=1,NPTFR
        I1 = 1
        I2 = 1
        DO ISUIV=1,NPTFR
          IF (TRAV1(I,1).EQ.TRAV1(ISUIV,2)) I1 = I1 + 1
          IF (TRAV1(I,2).EQ.TRAV1(ISUIV,1)) I2 = I2 + 1
        ENDDO
        IF (I1.NE.2) THEN
          IF (NBPB.EQ.0) THEN
            NBPB = 1
            NUMPB(NBPB) = TRAV1(I,1)
          ELSE
            EXIST = .FALSE.
            DO J=1,NBPB
              IF (NUMPB(J).EQ.TRAV1(I,1)) EXIST = .TRUE.
            ENDDO
            IF (.NOT.EXIST) THEN
              NBPB = NBPB + 1
              IF (NBPB.GT.100) THEN
                WRITE(LU,9001)
                CALL PLANTE(1)
                STOP
              ENDIF
              NUMPB(NBPB) = TRAV1(I,1)
            ENDIF
          ENDIF
        ENDIF
        IF (I2.NE.2) THEN
          IF (NBPB.EQ.0) THEN
            NBPB = 1
            NUMPB(NBPB) = TRAV1(I,2)
          ELSE
            EXIST = .FALSE.
            DO J=1,NBPB
              IF (NUMPB(J).EQ.TRAV1(I,2)) EXIST = .TRUE.
            ENDDO
            IF (.NOT.EXIST) THEN
              NBPB = NBPB + 1
              IF (NBPB.GT.100) THEN
                WRITE(LU,9001)
                CALL PLANTE(1)
                STOP
              ENDIF
              NUMPB(NBPB) = TRAV1(I,2)
            ENDIF
          ENDIF
        ENDIF
      ENDDO
!
      RETURN
!
! -------------------------FORMATS------------------------------------------
 1020 FORMAT (//,1X,'SEARCHING ABOUT CONNECTED ISLANDS',/,
     &          1X,'---------------------------------')
 9001 FORMAT (1X,'*****************************************',/,
     &        1X,'ERROR - ROUTINE VERIFS',/,
     &        1X,'NB OF CONNECTION POINTS GREATHER THAN 100',/,
     &        1X,'*****************************************')
!
      END
