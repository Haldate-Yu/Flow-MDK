!                   *********************************
                    SUBROUTINE USER_HINDERING_FORMULA
!                   *********************************
!
     &(WCHU,C,CINI,CGEL,NPOIN3)
!
!***********************************************************************
! TELEMAC3D   V8P5
!***********************************************************************
!
!brief    USER SUBROUTINE TO CUSTOMIZE THE HINDERING FORMULATIONS
!+
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| C              |<->| CONCENTRATION OF SED AT NODES
!|                |   | (ACTUALLY TRAV1 BIEF OBJECT WORK ARRAY)
!| CGEL           |-->| SEDIMENT CONCENTRATION AT WHICH SEDIMENT FORMS
!|                |   | A WEAK SOIL (KG/M3)
!| CINI           |-->| THRESHOLD CONCENTRATION FOR HINDERING TO START
!| NPOIN3         |-->| NUMBER OF 3D NODES
!| WCHU           |<->| SEDIMENT SETTLING VELOCITY
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE BIEF
!
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      TYPE(BIEF_OBJ), INTENT(INOUT) :: C
      INTEGER, INTENT(IN)           :: NPOIN3
      DOUBLE PRECISION, INTENT(INOUT) :: WCHU(NPOIN3)
      DOUBLE PRECISION, INTENT(IN)  :: CINI, CGEL
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
!
!-----------------------------------------------------------------------
!
!      ADD HINDERING FORMULA HERE
!
!
!-----------------------------------------------------------------------
!
      RETURN
      END
