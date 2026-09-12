!                       *****************
                        SUBROUTINE INIADC
!                       *****************
!
     &(NPOIN1,TYPELE,NSFOND,IHAUT,NGEO,TITRE)
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief
!+      Count the actual number of nodes in the ADCIRC file
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
!|          |   | (NPMAX = NPOIN + 0.1*NELEM)
!| NELMAX   |-->| Actual size of the element6based arrays
!|          |   | (NELMAX = NELEM + 0.2*NELEM)
!| NRES     |-->| Index refering to the serafin file
!| NGEO     |-->| Index refering to the mesh generator file
!| NLIM     |-->| Index refering to the dynam file
!| NFO1     |-->| Index refering to the triangle trigrid file
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELEM,MESH,NDP,NPOIN
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) :: NGEO
      INTEGER, INTENT(INOUT) :: NPOIN1 , NSFOND
      INTEGER, INTENT(INOUT) :: IHAUT
!
      CHARACTER(LEN=80), INTENT(INOUT) :: TITRE
      CHARACTER(LEN=11), INTENT(INOUT) :: TYPELE
!
!=======================================================================
!     INITIALISATIONS
!=======================================================================
!
      NSFOND = 2
      REWIND NGEO
!
!=======================================================================
!     LOAD THE FILE AND GO TO 5TH RECORD, SEQUENTIALLY
!=======================================================================
!
      TITRE=' '
      READ(NGEO,*) TITRE(1:24)
      READ(NGEO,*) NELEM,NPOIN
      IHAUT = 0
      NDP   = 3
      NPOIN1= NPOIN
      MESH = 3
      TYPELE = 'TRIANGLES  '
!
!-----------------------------------------------------------------------
!
      RETURN
      END
