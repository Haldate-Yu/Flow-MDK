!                   *************************************
                    MODULE INTERFACE_GAIA_SUSPENSION !
!                   *************************************
!
!
!***********************************************************************
! GAIA
!***********************************************************************
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      INTERFACE
      ! ======================================= !
      !  INTERFACE FOR THE GAIA SUBROUTINE      !
      !        FOR THE SUSPENDED TRANSPORT      !
      ! ======================================= !
      !----------------------------------------------------------------!
      SUBROUTINE BED1_SUSPENSION_DEPOSIT
      !----------------------------------------------------------------!
     &(CODE)
      USE BIEF
      USE DECLARATIONS_GAIA
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
      CHARACTER(LEN=24), INTENT(IN)   :: CODE
      END SUBROUTINE BED1_SUSPENSION_DEPOSIT
      !================================================================!

      !----------------------------------------------------------------!
      SUBROUTINE SUSPENSION_COMPUTE_CAE
      !----------------------------------------------------------------!
     &(TAUP,HN,DCLA,NPOIN,CHARR,XMVE,XMVS,VCE,GRAV,
     & ZERO,ZREF,AC,CSTAEQ,QSC,ICQ,U2D,V2D,CSRATIO,DEBUG,RATIO_TOCE)
      USE BIEF
      IMPLICIT NONE
      TYPE (BIEF_OBJ),  INTENT(IN)    :: TAUP,HN,ZREF,QSC
      TYPE (BIEF_OBJ),  INTENT(IN)    :: U2D,V2D,CSRATIO
      INTEGER,          INTENT(IN)    :: NPOIN,DEBUG,ICQ
      LOGICAL,          INTENT(IN)    :: CHARR
      DOUBLE PRECISION, INTENT(IN)    :: XMVE,XMVS,GRAV,VCE
      DOUBLE PRECISION, INTENT(IN)    :: ZERO,DCLA
      DOUBLE PRECISION, INTENT(IN)    :: AC
      TYPE (BIEF_OBJ),  INTENT(INOUT) :: CSTAEQ,RATIO_TOCE
      !----------------------------------------------------------------!
      END SUBROUTINE SUSPENSION_COMPUTE_CAE
      !================================================================!
      !----------------------------------------------------------------!
      SUBROUTINE SUSPENSION_FREDSOE
      !----------------------------------------------------------------!
     &  (DCLA, TAUP, NPOIN, GRAV, XMVE, XMVS, AC,  CSTAEQ, RATIO_TOCE)
      USE BIEF
      IMPLICIT NONE
      TYPE(BIEF_OBJ),   INTENT(IN)    :: TAUP
      INTEGER,          INTENT(IN)    :: NPOIN
      DOUBLE PRECISION, INTENT(IN)    :: GRAV, XMVE, XMVS
      DOUBLE PRECISION, INTENT(IN)    :: DCLA
      DOUBLE PRECISION, INTENT(IN)    :: AC
      TYPE(BIEF_OBJ),   INTENT(INOUT) :: CSTAEQ
      TYPE(BIEF_OBJ),   INTENT(IN)    :: RATIO_TOCE
      !----------------------------------------------------------------!
      END SUBROUTINE SUSPENSION_FREDSOE
      !================================================================!
      !----------------------------------------------------------------!
        SUBROUTINE SUSPENSION_BIJKER
      !----------------------------------------------------------------!

     &  (TAUP, NPOIN, CHARR, QSC, ZREF, ZERO, CSTAEQ, XMVE,RATIO_TOCE)
      USE BIEF
      IMPLICIT NONE
      TYPE(BIEF_OBJ),   INTENT(IN)    :: TAUP, QSC
      TYPE (BIEF_OBJ),  INTENT(IN)    :: ZREF
      INTEGER,          INTENT(IN)    :: NPOIN
      LOGICAL,          INTENT(IN)    :: CHARR
      DOUBLE PRECISION, INTENT(IN)    :: ZERO
      DOUBLE PRECISION, INTENT(IN)    :: XMVE
      TYPE(BIEF_OBJ),   INTENT(INOUT) :: CSTAEQ
      TYPE(BIEF_OBJ),   INTENT(IN)    :: RATIO_TOCE
      !----------------------------------------------------------------!
      END SUBROUTINE SUSPENSION_BIJKER
      !================================================================!
      !----------------------------------------------------------------!
      SUBROUTINE SUSPENSION_VANRIJN ! (_IMP_)
      !----------------------------------------------------------------!

     &  (DCLA, TAUP, NPOIN, GRAV,
     &   XMVE, XMVS,VCE, ZERO, AC, CSTAEQ,ZREF,RATIO_TOCE)

      USE BIEF
      IMPLICIT NONE
      TYPE(BIEF_OBJ),   INTENT(IN)    :: TAUP,ZREF
      INTEGER,          INTENT(IN)    :: NPOIN
      DOUBLE PRECISION, INTENT(IN)    ::  GRAV,  XMVE, XMVS,VCE
      DOUBLE PRECISION, INTENT(IN)    :: ZERO,AC,DCLA
      TYPE(BIEF_OBJ),   INTENT(INOUT) :: CSTAEQ
      TYPE(BIEF_OBJ),   INTENT(IN)    :: RATIO_TOCE

      END SUBROUTINE SUSPENSION_VANRIJN
      !================================================================!
      !----------------------------------------------------------------!
      SUBROUTINE SUSPENSION_SANDFLOW
      !----------------------------------------------------------------!
!
     &  (DCLA, NPOIN, GRAV, XMVE, XMVS, ZERO, CSTAEQ, HN,
     &   U2D, V2D, CSRATIO,RATIO_TOCE)
!
      USE BIEF
      IMPLICIT NONE
      TYPE(BIEF_OBJ),   INTENT(IN)       :: HN,U2D,V2D,CSRATIO
      INTEGER,          INTENT(IN)       :: NPOIN
      DOUBLE PRECISION, INTENT(IN)       :: GRAV, XMVE, XMVS
      DOUBLE PRECISION, INTENT(IN)       :: ZERO,DCLA
      TYPE(BIEF_OBJ),   INTENT(INOUT)    :: CSTAEQ
      TYPE(BIEF_OBJ),   INTENT(IN)    :: RATIO_TOCE
!
      END SUBROUTINE SUSPENSION_SANDFLOW
      !================================================================!
      !----------------------------------------------------------------!
      SUBROUTINE EQCAE_BC
      !----------------------------------------------------------------!
!
     &(LITBOR,TBOR,TN,J,KENT)
!
      USE BIEF
      USE DECLARATIONS_GAIA
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
      INTEGER, INTENT(IN) :: LITBOR(NPTFR),J,KENT
      DOUBLE PRECISION, INTENT(INOUT) :: TBOR(NPTFR),TN(NPOIN)
!
      END SUBROUTINE EQCAE_BC
      !================================================================!
      !----------------------------------------------------------------!
      SUBROUTINE PREP_ADVECTION_GAIA
      !----------------------------------------------------------------!
!
     &(UCONV_TEL,VCONV_TEL,ICONVF,SOLSYS,J,LITBOR,TBOR,TN,KENT,FLBOR_W,
     & HN_TEL,MASSOU)
!
      USE BIEF
      USE INTERFACE_PARALLEL
      USE DECLARATIONS_GAIA
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
      TYPE(BIEF_OBJ), INTENT(IN) :: UCONV_TEL,VCONV_TEL,FLBOR_W
      TYPE(BIEF_OBJ), INTENT(IN), TARGET :: HN_TEL
      INTEGER, INTENT(IN) :: ICONVF,SOLSYS,J,LITBOR(NPTFR),KENT
      DOUBLE PRECISION, INTENT(INOUT) :: TBOR(NPTFR),TN(NPOIN)
      DOUBLE PRECISION, INTENT(INOUT) :: MASSOU
!
      END SUBROUTINE PREP_ADVECTION_GAIA
      !================================================================!
      !----------------------------------------------------------------!
      SUBROUTINE SUSPENSION_MILES
      !----------------------------------------------------------------!

     &(HN,NPOIN,HMIN,FDM,FD90,XWC,CSRATIO)

      USE BIEF
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
      TYPE(BIEF_OBJ),   INTENT(IN)    :: HN
      INTEGER,          INTENT(IN)    :: NPOIN
      DOUBLE PRECISION, INTENT(IN)    :: FDM,FD90,XWC,HMIN
      TYPE(BIEF_OBJ),   INTENT(INOUT) :: CSRATIO
      END SUBROUTINE SUSPENSION_MILES
      !================================================================!
      !----------------------------------------------------------------!
      SUBROUTINE SUSPENSION_ROUSE
      !----------------------------------------------------------------!

     &(USTAR,HN,NPOIN,KARMAN,ZERO,XWC,ZREF,CSRATIO)

      USE BIEF
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
      TYPE(BIEF_OBJ),   INTENT(IN)    :: USTAR,HN,ZREF
      INTEGER,          INTENT(IN)    :: NPOIN
      DOUBLE PRECISION, INTENT(IN)    :: KARMAN,XWC,ZERO
      TYPE(BIEF_OBJ),   INTENT(INOUT) :: CSRATIO

      END SUBROUTINE SUSPENSION_ROUSE
      !================================================================!
!
!======================================================================!
!======================================================================!
      END INTERFACE
      END MODULE INTERFACE_GAIA_SUSPENSION
!
!#######################################################################
!
