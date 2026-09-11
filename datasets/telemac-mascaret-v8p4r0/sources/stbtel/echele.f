!                       *****************
                        SUBROUTINE ECHELE
!                       *****************
!
     &(IKLE, IEL1 , IEL2 )
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Swap numbers for two elements
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| IKLE          |<->| Global numbering of all nodes by element
!| IEL1, IEL2    |-->| Node numbers to be swapped
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) :: IEL1 , IEL2
      INTEGER, INTENT(INOUT) :: IKLE(NELMAX,4)
!
      INTEGER STO(4), I
!
!
!=======================================================================
!
      DO I = 1 , NDP
        STO(I) = IKLE(IEL1,I)
        IKLE(IEL1,I) = IKLE(IEL2,I)
        IKLE(IEL2,I) = STO(I)
      ENDDO
!
!=======================================================================
!
      RETURN
      END
