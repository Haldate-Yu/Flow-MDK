!                       *****************
                        SUBROUTINE DEPARR
!                       *****************
!
     &(IKLE,NDEPAR,LGVEC)
!
!***********************************************************************
! STBTEL    V5P2
!***********************************************************************
!
!brief    detection of backward dependencies
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| IKLE      |<--| Global numbering of all nodes by element
!| NDEPAR    |<--| Number of backward dependencies
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELEM, NELMAX
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) :: LGVEC
      INTEGER, INTENT(INOUT) :: NDEPAR
      INTEGER, INTENT(IN) :: IKLE(NELMAX,4)
!
      INTEGER IELEM , K
      INTEGER I1 , I2 , I3 , J1 , J2 , J3 , IEL1
!
!=======================================================================
!
      NDEPAR = 0
      DO IELEM = 1,NELEM
        I1 = IKLE(IELEM,1)
        I2 = IKLE(IELEM,2)
        I3 = IKLE(IELEM,3)
        DO K = 2,LGVEC
          IEL1 = MOD(NELEM+IELEM-K,NELEM) + 1
          J1 = IKLE(IEL1,1)
          J2 = IKLE(IEL1,2)
          J3 = IKLE(IEL1,3)
          IF (I1.EQ.J1.OR.I1.EQ.J2.OR.I1.EQ.J3.OR.
     &        I2.EQ.J1.OR.I2.EQ.J2.OR.I2.EQ.J3.OR.
     &        I3.EQ.J1.OR.I3.EQ.J2.OR.I3.EQ.J3) NDEPAR = NDEPAR + 1
        ENDDO
      ENDDO
!
!=======================================================================
!
      RETURN
      END
