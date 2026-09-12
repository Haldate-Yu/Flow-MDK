!                 ************************************
                  SUBROUTINE LECDON_SPLIT_OUTPUTPOINTS
!                 ************************************
!
     &(INT_LIST, POINT_ARRAY, FULLOUTPUT)
!
!***********************************************************************
! GAIA
!***********************************************************************
!
!>@brief Split a string containing a list of integers into an array
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in]     IN_LIST     String of integers
!>@param[in,out] POINT_ARRAY Array with the same integers
!>@param[in,out] FULLOUTPUT  True if FULLOUTPUT is found
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      CHARACTER(LEN=*), INTENT(INOUT) :: INT_LIST
      INTEGER, INTENT(INOUT) :: POINT_ARRAY(100)
      LOGICAL, INTENT(INOUT) :: FULLOUTPUT
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
! INTERNAL VARIABLES:
!
      CHARACTER C(2)
      CHARACTER(LEN=8) MOT(100)
      INTEGER I,J,LONG,I1,I2,NMOT
!
      INTRINSIC LEN
!
!-----------------------------------------------------------------------
!
!  RECOGNISED SEPARATORS IN 'INT_LIST'
!
      C(1) = ';'
      C(2) = '|'
      LONG = LEN(INT_LIST)
      IF(LONG.EQ.0) THEN
        WRITE(LU,*) 'LECDON_SPLIT STRING ERROR'
        CALL PLANTE(1)
        STOP
      ENDIF
!
      DO I=1,LONG
        DO J=1,2
          IF(INT_LIST(I:I).EQ.C(J)) INT_LIST(I:I) = ' '
        ENDDO
      ENDDO
!
! 'INT_LIST' NOW IS MADE UP OF WORDS SEPARATED BY WHITE SPACES
!
      I1 = 0
      NMOT=0
!
 10   CONTINUE
      IF(I1.GE.LONG) GOTO 30
      I1=I1+1
      IF(INT_LIST(I1:I1).EQ.' ') GOTO 10
!
      I2=0
!
 20   CONTINUE
      I2=I2+1
      IF(INT_LIST(I1+I2:I1+I2).NE.' ') GOTO 20
!
      NMOT=NMOT+1
      MOT(NMOT)=INT_LIST(I1:I1+I2)
      I1=I1+I2
      GOTO 10
!
30    CONTINUE
!
!     Builds the POINT_ARRAY
!
      FULLOUTPUT = .FALSE.
      DO J=1,100
        POINT_ARRAY(J) = -1
      ENDDO
      DO J=1,NMOT
        READ(MOT(J),* ) POINT_ARRAY(J)
        IF (POINT_ARRAY(J).EQ.0) FULLOUTPUT = .TRUE.
      ENDDO
!
!-----------------------------------------------------------------------
!
      RETURN
      END
