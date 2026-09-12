!                       *****************
                        SUBROUTINE INITRI
!                       *****************
!
     &( NPOIN1,TYPELE,NGEO,NFO1)
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Count the actual number of nodes and elemnts of a
!+           TRIGRID file
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| NPOIN1   |<--| Actual number of nodes in the mesh
!|          |   | (npoin is the max node index because supertab
!|          |   |  keeps holes in its node numbering
!| TYPELE   |-->| Element types
!| MESH     |<--| Mesh
!| NDP      |-->| Number of nodes per element
!| NPOIN    |<--| Total number of nodes in the mesh
!| NELEM    |<--| Total number of element in the mesh
!| NPMAX    |-->| Actual size of the node-based x and y arrays
!|          |   | (npmax = npoin + 0.1*nelem)
!| NELMAX   |-->| Actual size of the element6based arrays
!|          |   | (nelmax = nelem + 0.2*nelem)
!| NRES     |-->| Index refering to the serafin file
!| NGEO     |-->| Index refering to the mesh generator file
!| NLIM     |-->| Index refering to the dynam file
!| NFO1     |-->| Index refering to the triangle trigrid file
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_STBTEL, ONLY: NELEM,MESH,NDP,NPOIN
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) :: NGEO, NFO1
      INTEGER, INTENT(INOUT) :: NPOIN1
      CHARACTER(LEN=*), INTENT(INOUT) :: TYPELE
!
      CHARACTER(LEN=1)   ZDUMMY
!
      REWIND (NGEO)
      REWIND (NFO1)
      READ (NGEO,*) NPOIN1
      NPOIN = NPOIN1
      NELEM = 0
 1    CONTINUE
        READ (NFO1, '(A1)', END=9000) ZDUMMY
        NELEM = NELEM + 1
      GOTO 1
!
 9000 CONTINUE
      TYPELE = 'TRIANGLES  '
      NDP = 3
      MESH = 3
!
      RETURN
      END
