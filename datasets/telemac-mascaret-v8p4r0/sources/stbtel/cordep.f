!                       *****************
                        SUBROUTINE CORDEP
!                       *****************
!
     &(IKLE,LGVEC)
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Backward dependency corrections
!
!
!-----------------------------------------------------------------------
!| IKLE           |-->| Connectivity table
!| LGVEC          |-->| Lenght of vector
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELEM,NELMAX
      USE INTERFACE_STBTEL, EX_CORDEP => CORDEP
      IMPLICIT NONE
!
      INTEGER, INTENT(INOUT) :: IKLE(NELMAX,4)
      INTEGER, INTENT(IN) :: LGVEC
!
      INTEGER IELEM , IEL1 , IEL2
      INTEGER I1 , I2 , I3 , J1 , J2 , J3
      INTEGER K
!
      LOGICAL DEP
!
!
!=======================================================================
!
      DO IELEM = 1,NELEM
        IEL2 = IELEM
25      CONTINUE
        DEP = .FALSE.
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
     &        I3.EQ.J1.OR.I3.EQ.J2.OR.I3.EQ.J3) DEP=.TRUE.
        ENDDO
        IF (DEP) THEN
          IEL2 = MOD(IEL2,NELEM) + 1
          IF (IEL2.EQ.IELEM) GOTO 40
          CALL ECHELE(IKLE,IELEM,IEL2)
          GOTO 25
        ENDIF
      ENDDO ! IELEM
!
!=======================================================================
!
40    CONTINUE
!
      RETURN
      END
