!                   *************************
                    SUBROUTINE PREDES_RESTART
!                   *************************
!
     &(LLT,AAT,YAGOUT,CODE)
!
!***********************************************************************
! GAIA
!***********************************************************************
!
!>@brief    Prepares the variables which will be written to
!!          the restart file.
!!          Creation from predes (for the result file)
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in] AAT       Current time (for building solutions)
!>@param[in] CODE      Name of calling programme (telemac2d or 3d)
!>@param[in] LLT       Local lt
!>@param[in] YAGOUT    If yes graphic output anyway (steered by t2d)
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE BIEF
      USE DECLARATIONS_GAIA
      IMPLICIT NONE
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER          , INTENT(IN) :: LLT
      DOUBLE PRECISION , INTENT(IN) :: AAT
      CHARACTER(LEN=24) , INTENT(IN) :: CODE
      LOGICAL          , INTENT(IN) :: YAGOUT
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER I,J,K
      LOGICAL LEO
!
!-----------------------------------------------------------------------
!
!     THE OUTPUT VARIABLES ARE BUILT ONLY IF NECESSARY, HENCE THE
!     FOLLOWING TESTS, WHICH MUST BE THE SAME AS IN DESIMP (BIEF LIBRARY)
!
      LEO=.FALSE.
!     IF CODE =TELEMAC2D OUTOUT IS MANAGED BY T2D
      IF(CODE(8:9).EQ.'2D'.OR.CODE(8:9).EQ.'3D') LEO=YAGOUT
!
!     NO PRINTOUTS REQUIRED: LEAVING
      IF (.NOT.LEO) GO TO 1000
!
!=======================================================================
!
!     VARIABLES WHICH ARE NOT INITIALISED AT THE FIRST CALL OF
!     PREDES_RESTART
!
      IF(LLT.EQ.0) THEN
!       JMH ON 27/11/2009
        IF(LEO.AND.SOREST(19)) THEN
          CALL OS('X=0     ',X=KS)
        ENDIF
      ENDIF
!
!=======================================================================
! UPDATE THE Values of the writing blocks
!=======================================================================
!
      ! For memory optimisation (from intel debug)
      ! For RATIOS
      IF (LEO.AND.SOREST(NVAR_RATIOS+1)) THEN
        DO K=1,NOMBLAY
          DO I=1,NSAND
            RATIOS%ADR(K+(I-1)*NOMBLAY)%P%R=RATIO_SAND(I,K,1:NPOIN)
          ENDDO
        ENDDO
      ENDIF
      ! For RATIOM
      IF(LEO.AND.SOREST(NVAR_RATIOM+1)) THEN
        DO K=1,NOMBLAY
          DO I=1,NMUD
            RATIOM%ADR(K+(I-1)*NOMBLAY)%P%R=RATIO_MUD(I,K,1:NPOIN)
          ENDDO
        ENDDO
      ENDIF
      ! For Layconc
      IF(LEO.AND.SOREST(NVAR_LAYCONC+1)) THEN
        DO K=1,NOMBLAY
          LAYCONC%ADR(K)%P%R=CONC_MUD(K,1:NPOIN)
        ENDDO
      ENDIF
      ! For mass_s
      IF(LEO.AND.SOREST(NVAR_MASS_S+1)) THEN
        DO K=1,NOMBLAY
          DO I=1,NSAND
            MASS_S%ADR(K+(I-1)*NOMBLAY)%P%R=MASS_SAND(I,K,1:NPOIN)
          ENDDO
        ENDDO
      ENDIF
      ! For mass_m
      IF(LEO.AND.SOREST(NVAR_MASS_M+1)) THEN
        DO K=1,NOMBLAY
          DO I=1,NMUD
            MASS_M%ADR(K+(I-1)*NOMBLAY)%P%R=MASS_MUD(I,K,1:NPOIN)
          ENDDO
        ENDDO
      ENDIF
      ! For mtransfer
      IF(LEO.AND.SOREST(NVAR_MTRANS+1)) THEN
        DO K=1,NOMBLAY
          MTRANSFER%ADR(K)%P%R=TRANS_MASS(K,1:NPOIN)
        ENDDO
      ENDIF
      ! For tocemud
      IF(LEO.AND.SOREST(NVAR_TOCEMUD+1)) THEN
        DO K=1,NOMBLAY
          TOCEMUD%ADR(K)%P%R=TOCE_MUD(K,1:NPOIN)
        ENDDO
      ENDIF
      ! For partheniades
      IF(LEO.AND.SOREST(NVAR_PARTHE+1)) THEN
        DO K=1,NOMBLAY
          PARTHE%ADR(K)%P%R=PARTHENIADES(K,1:NPOIN)
        ENDDO
      ENDIF
!
!=======================================================================
! UPDATE THE POINTERS TO THE DIFFERENTIATED VARIABLES
!=======================================================================
!
      J = NVAR_ADVAR
      DO I = 1,NADVAR
        IF(LEO.AND.SOREST(J)) THEN
          CALL AD_GET_GAIA(I,ADVAR%ADR(I)%P)
          J = J + 1
        ENDIF
      ENDDO
!
!=======================================================================
!
1000  CONTINUE
!
!=======================================================================
!
      RETURN
      END
