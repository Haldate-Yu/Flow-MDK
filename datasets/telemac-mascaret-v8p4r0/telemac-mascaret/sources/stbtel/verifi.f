!                       *****************
                        SUBROUTINE VERIFI
!                       *****************
!
     &(X,Y,IKLE,NCOLOR,TRAV1,EPSI,MESH,NDP,NPOIN,NELEM,NELMAX)
!
!***********************************************************************
! STBTEL  V5P2
!***********************************************************************
!
!brief    Removing gaps in the node numbering and re-ordering elements
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| X,Y      |-->| Mesh coordinates
!| IKLE     |<->| Connectivity
!| TRAV1,2  |<->| Working arrays
!| EPSI     |-->| Minimum distance between 2 nodes
!| NCOLOR   |<--| Array of node colours
!| COLOR    |<->| Whether node colours are stored within the geo
!| MESH     |-->| Elements types
!| NDP      |-->| Number of nodes per element
!| NPOIN    |<--| Total number of nodes in the mesh
!| NELEM    |<--| Total number of element in the mesh
!| NPMAX    |-->| Actual size of the node-based x and y arrays
!|          |   | (npmax = npoin + 0.2*nelem)
!| NELMAX   |-->| Actual size of arrays associated to elements
!|          |   | (nelmax = nelem + 0.2*nelem)
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE INTERFACE_STBTEL, EX_VERIFI => VERIFI
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) ::  MESH , NDP , NELMAX
      INTEGER, INTENT(INOUT) :: NPOIN, NELEM
      INTEGER, INTENT(INOUT) :: IKLE(NELMAX,4) , NCOLOR(*)
      INTEGER, INTENT(INOUT) :: TRAV1(*)
!
      DOUBLE PRECISION, INTENT(INOUT) :: X(*) , Y(*)
      DOUBLE PRECISION, INTENT(INOUT) :: EPSI
!
      INTEGER ITEST , ITEST1 , IELEM
!
!=======================================================================
!     CHECKING THAT ALL NODES ARE DISTINCT FROM ONE ANOTHER
!=======================================================================
!
      CALL REMAIL (IKLE,NCOLOR,TRAV1,X,Y,EPSI,
     &             NDP,NPOIN,NELEM,NELMAX)
!
!=======================================================================
!     CHECKING THAT ALL ELEMENTS ARE CORRECTLY ORIENTED
!=======================================================================
!
      ITEST = 0
!
!     QUADRANGLES
!
      IF (MESH.EQ.2) THEN
!
        DO IELEM=1,NELEM
!
          ITEST1 = 0
          CALL CIRCUL (IKLE,ITEST1,IELEM,1,2,3,X,Y,NELMAX)
          CALL CIRCUL (IKLE,ITEST1,IELEM,2,3,4,X,Y,NELMAX)
          CALL CIRCUL (IKLE,ITEST1,IELEM,3,4,1,X,Y,NELMAX)
          CALL CIRCUL (IKLE,ITEST1,IELEM,4,1,2,X,Y,NELMAX)
          IF (ITEST1.GT.0) ITEST = ITEST + 1
!
        ENDDO
!
!       TRIANGLES
!
      ELSE IF (MESH.EQ.3) THEN
!
        DO IELEM=1,NELEM
!
          ITEST1 = 0
          CALL CIRCUL (IKLE,ITEST1,IELEM,1,2,3,X,Y,NELMAX)
          IF (ITEST1.GT.0) ITEST = ITEST + 1
!
        ENDDO
!
      ELSE
        WRITE(LU,3090) MESH
 3090   FORMAT(/,' LECSTB TYPE OF MESH NOT AVAILABLE , MESH = ',I4)
      ENDIF
!
      WRITE(LU,3100) ITEST
 3100 FORMAT(1X,'NUMBER OF ELEMENTS BADLY ORIENTED : ',I5)
!
      RETURN
      END
