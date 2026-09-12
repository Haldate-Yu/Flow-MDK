! ASUMPPTIONS:
! Wave current interaction is not yet taken into account
! Note that we calculate the "kinematic surface roller energy" (so energy divided by RHO). Unit is m3/s2
      MODULE SURFACE_ROLLER

      USE BIEF
      USE DECLARATIONS_SPECIAL

      IMPLICIT NONE
      TYPE(BIEF_OBJ), TARGET :: FROL, FROL_OLD,CROLY,CROLX, DISSIP_ROL
      DOUBLE PRECISION, TARGET, ALLOCATABLE, DIMENSION(:) :: CROL,
     & SIN_DIR,COS_DIR, FREQ_ROL, DIR_ROL


      ! FOR PROPAGATION
      TYPE(BIEF_OBJ) ::      SHPROL
      INTEGER, ALLOCATABLE, DIMENSION(:) :: ELTROL, ETAROL
      INTEGER, ALLOCATABLE, DIMENSION(:,:) :: ITR_ROL
      INTEGER, ALLOCATABLE, DIMENSION(:) :: ISUBROL


      !EMPTY DATA STRUCTURE
      TYPE(BIEF_OBJ) :: BID

      DOUBLE PRECISION :: DTROL


      LOGICAL :: DEBUG_SR = .FALSE.

      PRIVATE

      PUBLIC :: INIT_SURF_ROL,END_SURF_ROL, CALC_SURF_ROL,
     &   RAD_STRESS_SURF_ROL, FROL, POSTPROC_SURF_ROL, DISSIP_ROL

      SAVE

      CONTAINS


!***********************************************************************

!                   *****************************
                    SUBROUTINE INIT_SURF_ROL()
!                   *****************************
!

!
!***********************************************************************
! TOMAWAC
!***********************************************************************
!
!>@brief INTIALIZE SURFACE ROLLER MODULE
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_TOMAWAC
      IMPLICIT NONE
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
!
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER :: IERR
!
!-----------------------------------------------------------------------


      !COMPATIBILTY CHECKS

      DEBUG_SR = (DEBUG.GT.0)
      IF (DEBUG_SR) THEN
        WRITE (LU,*) 'START INIT_SURF_ROL'
      ENDIF


      IF (SBREK.EQ.10) THEN
        WRITE (LU,*) 'SURFACE ROLLERS DO NOT WORK YET WITH: '
        WRITE (LU,*) 'DEPTH-INDUCED BREAKING DISSIPATION = 10'
        CALL PLANTE(1)
      ENDIF

      DTROL = DT/DBLE(SUBSTEP_SURFROL)

      CALL BIEF_ALLVEC(1,FROL ,'FROL  ',IELM2 , 1 , 2 ,MESH)
      CALL BIEF_ALLVEC(1,DISSIP_ROL ,'DISROL  ',IELM2 , 1 , 2 ,MESH)
      CALL BIEF_ALLVEC(1,FROL_OLD ,'FROLOL',IELM2 , 1 , 2 ,MESH)
      CALL BIEF_ALLVEC(1,CROLX ,'CROLX ',IELM2 , 1 , 2 ,MESH)
      CALL BIEF_ALLVEC(1,CROLY ,'CROLY ',IELM2 , 1 , 2 ,MESH)
      CALL BIEF_ALLVEC(1,SHPROL ,'SHPROL',IELM2 , 3 , 2 ,MESH)
      CALL BIEF_ALLVEC(1,BID,'BID   ',0,1,1,MESH)

      !MEMORY FOR CHARACTERISTICS
      ALLOCATE(ELTROL(NPOIN2),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'INIT_SURF_ROL:ELTROL')
      ALLOCATE(ETAROL(NPOIN2),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'INIT_SURF_ROL:ETAROL')
      ALLOCATE(ITR_ROL(NPOIN2,3),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'INIT_SURF_ROL:ITR01')
      ALLOCATE(ISUBROL(NPOIN2),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'INIT_SURF_ROL:ISUBROL')



      ! MEMORY ALLOCATION
      ALLOCATE(FREQ_ROL(NPOIN2),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'INIT_SURF_ROL:FREQ_ROL')
      ALLOCATE(DIR_ROL(NPOIN2),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'INIT_SURF_ROL:DIR_ROL')

      ALLOCATE(CROL(NPOIN2),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'INIT_SURF_ROL:CROL')
      ALLOCATE(COS_DIR(NPOIN2),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'INIT_SURF_ROL:COS_DIR')
      ALLOCATE(SIN_DIR(NPOIN2),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'INIT_SURF_ROL:SIN_DIR')

      !INITIAL CONDITIONS
      CALL OS('X=0     ',X=FROL)
      CALL OS('X=0     ',X=FROL_OLD)
      CALL OS('X=0     ',X=DISSIP_ROL)

      IF (DEBUG_SR) THEN
        WRITE (LU,*) 'END INIT_SURF_ROL'
      ENDIF

!
!-----------------------------------------------------------------------
!
      RETURN
      END
!***********************************************************************

!                   *****************************
                    SUBROUTINE CALC_SURF_ROL()
!                   *****************************
!

!
!***********************************************************************
! TOMAWAC
!***********************************************************************
!
!>@brief CALCULATION OF SURFACE ROLLERS
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_TOMAWAC
      IMPLICIT NONE
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
!
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER :: I
!
!-----------------------------------------------------------------------


          IF (DEBUG_SR) THEN
            WRITE (LU,*) 'START CALC_SURF_ROL'
          ENDIF

          !Do substeps for calculation of surface rollers
          CALL PREPO_SURF_ROL()
          DO I = 1, SUBSTEP_SURFROL
            CALL PROPA_SURF_ROL
            CALL SOURCE_SURF_ROL
            CALL OS('X=Y     ',X=FROL_OLD,Y=FROL)
          ENDDO

          IF (DEBUG_SR) THEN
            WRITE (LU,*) 'END CALC_SURF_ROL'
          ENDIF


!
!-----------------------------------------------------------------------
!
      RETURN
      END




!***********************************************************************

!                   *****************************
                    SUBROUTINE PREPO_SURF_ROL()
!                   *****************************
!

!
!***********************************************************************
! TOMAWAC
!***********************************************************************
!
!>@brief PREPARATION OF ADVECTION OF SURFACE ROLLERS
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_TOMAWAC
      IMPLICIT NONE
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
!
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER :: IPOIN2
      DOUBLE PRECISION :: K,TMP
      DOUBLE PRECISION, PARAMETER :: ALPHA_HEDGES = 0.5D0


!
!-----------------------------------------------------------------------


      IF (DEBUG_SR) THEN
        WRITE (LU,*) 'START PREPO_SURF_ROL'
      ENDIF


      !calculate wave directions and frequency from spectrum
      !note that no transfer to absoulte frequency is done.
      !So wave-current interaction may not be taken into account correctly

      CALL FREMOY(FREQ_ROL, F,NF, NDIRE, NPOIN2)
      CALL TETMOY(DIR_ROL, F, NDIRE,NF,NPOIN2)

      !To substitute H, the dependency of the shallow water wave
      !propagation speed on the wave height (amplitude dispersion) is
      !exploited using an empirical predictor similar to the one proposed
      !by Hedges (1976) for the nonlinear shallow water phase speed
      !assumed that relation works on Hrms.

      CALL TOTNRJ(VARIAN, F, NF, NDIRE, NPOIN2)

      !calculate wave velocities (c=omega/k)
      DO IPOIN2=1,NPOIN2
        TMP = 2.0D0*ALPHA_HEDGES*
     &    SQRT(2.0D0*MAX(VARIAN(IPOIN2),0.0D0))
        CALL WNSCOU(K  , FREQ_ROL(IPOIN2)  , DEPTH(IPOIN2)+TMP)
        CROL(IPOIN2) =  DEUPI*FREQ_ROL(IPOIN2)/K
      ENDDO

      !apply wave directions
      DO IPOIN2=1,NPOIN2
        COS_DIR(IPOIN2) = COS(DIR_ROL(IPOIN2))
      ENDDO
      DO IPOIN2=1,NPOIN2
        SIN_DIR(IPOIN2) = SIN(DIR_ROL(IPOIN2))
      ENDDO

      !note that the sin and cos, are chosen such that there is an 
      !implicit convertion from the nautical directions in TOMAWAC 
      ! to cartesian ones for the surface rolles
      DO IPOIN2=1,NPOIN2
        CROLX%R(IPOIN2) = CROL(IPOIN2)*SIN_DIR(IPOIN2)
      ENDDO
      DO IPOIN2=1,NPOIN2
        CROLY%R(IPOIN2) = CROL(IPOIN2)*COS_DIR(IPOIN2)
      ENDDO

      !wetting drying
      DO IPOIN2=1,NPOIN2
        IF(DEPTH(IPOIN2).LT.PROMIN) THEN
          CROLX%R(IPOIN2)=0.0D0
          CROLY%R(IPOIN2)=0.0D0
        ENDIF
      ENDDO

      IF (DEBUG_SR) THEN
        WRITE (LU,*) 'END PREPO_SURF_ROL'
      ENDIF
!
!-----------------------------------------------------------------------
!
      RETURN
      END




!***********************************************************************

!                   *****************************
                    SUBROUTINE PROPA_SURF_ROL()
!                   *****************************
!

!
!***********************************************************************
! TOMAWAC
!***********************************************************************
!
!>@brief ADVECTION OF SURFACE ROLLERS USING CHARACTERISTIC METHOD
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_TOMAWAC
      IMPLICIT NONE
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
!
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!

      !EMPTY DATA TYPES
      TYPE(SLVCFG) :: SLVBID

!
!-----------------------------------------------------------------------

      IF (DEBUG_SR) THEN
        WRITE (LU,*) 'START PROPA_SURF_ROL'
      ENDIF

      CALL CHARAC(
     &            FROL_OLD,FROL,1,
                  !advection velocity
     &            CROLX,CROLY,
                  !not used
     &            BID,BID,BID,BID,
     &            DTROL,MESH%IFABOR,IELM2,
     &            NPOIN2,1,1,1,.FALSE.,SHPROL,
                  ! not used
     &            BID,BID,TB,
     &            ELTROL,
                  !not used
     &            ETAROL,ETAROL,
                  !integer work array
     &            ITR_ROL(1:NPOIN2,1),
                  !arrival sub-domain(was already 2d)
     &            ISUBROL,
     &            ITR_ROL(1:NPOIN2,2),MESH,NELEM2,NELEM2,
     &            MESH%IKLE,
     &            MESH%SURDET,
                  !for weak char; not used
     &            BID,BID,SLVBID,0.D0,.FALSE.,3,BID,1,
!                 a posteriori interpolation
     &            .FALSE.,
!                 and periodicity
     &            .FALSE.)

      IF (DEBUG_SR) THEN
        WRITE (LU,*) 'END PROPA_SURF_ROL'
      ENDIF

!
!-----------------------------------------------------------------------
!
      RETURN
      END



!***********************************************************************

!                   *****************************
                    SUBROUTINE SOURCE_SURF_ROL()
!                   *****************************
!

!
!***********************************************************************
! TOMAWAC
!***********************************************************************
!
!>@brief SOURCE AND SINK TERMS FOR SURFACE ROLLERS
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_TOMAWAC
      IMPLICIT NONE
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
!
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER :: IPOIN2
      DOUBLE PRECISION :: COEF, COEFDT
      DOUBLE PRECISION, PARAMETER :: VERY_SMALL = 1.0D-8
!
!-----------------------------------------------------------------------



      IF (DEBUG_SR) THEN
        WRITE (LU,*) 'START SOURCE_SURF_ROL'
      ENDIF

      COEF = 2.0D0*GRAVIT*BETA_S_SURFROL/BETA_2_SURFROL
      COEFDT = COEF*DTROL

      !update surface roller energy
      !SCHEME: E(N+1)-E(N) = DT*(SOURCE(N)-SINK(N+1))
      !explicit source
      !implicit sink

      ! Note that dissip_break is negative.
      ! Therefore a minus sign is needed.
      ! Also note that (due to roundoff error?), the maxz is needed
      !  to prevent very small negative values (1e-19)
      DO IPOIN2=1,NPOIN2
        FROL%R(IPOIN2) =  MAX((FROL%R(IPOIN2) - 
     &    DTROL*GRAVIT*DISSIP_BREAK%R(IPOIN2))/
     &    (1.0D0+COEFDT/MAX(CROL(IPOIN2),VERY_SMALL)),0.0D0)
        DISSIP_ROL%R(IPOIN2) = COEF*FROL%R(IPOIN2)/
     &     MAX(CROL(IPOIN2),VERY_SMALL)
      ENDDO


      IF (DEBUG_SR) THEN
        WRITE (LU,*) 'END SOURCE_SURF_ROL'
      ENDIF

!
!-----------------------------------------------------------------------
!
      RETURN
      END

!***********************************************************************

!                   *****************************
                    SUBROUTINE RAD_STRESS_SURF_ROL
!                   *****************************

     &                  (SXX,SXY,SYY,NPOIN2)
!

!
!***********************************************************************
! TOMAWAC
!***********************************************************************
!
!>@brief RADIATION STRESS DUE TO SURFACE ROLLERS
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in,out] SXX    xx-component of radiation stress
!>@param[in,out] SXY    xy-component of radiation stress
!>@param[in,out] SYY    yy-component of radiation stress
!>@param[in]  NPOIN2    Number of points in the mesh
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      IMPLICIT NONE
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER, INTENT(IN) :: NPOIN2
      DOUBLE PRECISION, DIMENSION(NPOIN2), INTENT(INOUT) :: SXX,SXY,SYY
!
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER :: IPOIN2
      DOUBLE PRECISION, PARAMETER :: VERY_SMALL = 1.0D-8
!
!-----------------------------------------------------------------------


      IF (DEBUG_SR) THEN
        WRITE (LU,*) 'START RAD_STRESS_SURF_ROL'
      ENDIF

      DO IPOIN2 = 1,NPOIN2
        SXX(IPOIN2) =  SXX(IPOIN2) + FROL%R(IPOIN2)*COS_DIR(IPOIN2)**2
        SXY(IPOIN2) =  SXY(IPOIN2) + FROL%R(IPOIN2)*COS_DIR(IPOIN2)*
     &                                               SIN_DIR(IPOIN2)
        SYY(IPOIN2) =  SYY(IPOIN2) + FROL%R(IPOIN2)*SIN_DIR(IPOIN2)**2
      ENDDO

      IF (DEBUG_SR) THEN
        WRITE (LU,*) 'END RAD_STRESS_SURF_ROL'
      ENDIF


!
!-----------------------------------------------------------------------
!
      RETURN
      END
!***********************************************************************

!                   *****************************
                    SUBROUTINE POSTPROC_SURF_ROL
!                   *****************************
!

!
!***********************************************************************
! TOMAWAC
!***********************************************************************
!
!>@brief POSTPROCESSING SURFACE ROLLERS
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_TOMAWAC
      IMPLICIT NONE
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
!
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER :: IPOIN2
      DOUBLE PRECISION, PARAMETER :: VERY_SMALL = 1.0D-8
!
!-----------------------------------------------------------------------


      IF (DEBUG_SR) THEN
        WRITE (LU,*) 'START POSTPROC_SURF_ROL'
      ENDIF

      DO IPOIN2 = 1,NPOIN2
        CPL_WAC_DATA%SURFROL_TEL%R(IPOIN2)=FROL%R(IPOIN2)
      ENDDO
      DO IPOIN2 = 1,NPOIN2
        CPL_WAC_DATA%SURFDIS_TEL%R(IPOIN2)=DISSIP_ROL%R(IPOIN2)
      ENDDO


      IF (DEBUG_SR) THEN
        WRITE (LU,*) 'END POSTPROC_SURF_ROL'
      ENDIF

!
!-----------------------------------------------------------------------
!
      RETURN
      END


!***********************************************************************


!                   *****************************
                    SUBROUTINE END_SURF_ROL()
!                   *****************************
!

!
!***********************************************************************
! TOMAWAC
!***********************************************************************
!
!>@brief DEALLOCATE VARIABLES FOR SURFACE ROLLERS
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_TOMAWAC
      IMPLICIT NONE
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
!
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER :: IERR
!
!-----------------------------------------------------------------------

      CALL  BIEF_DEALLVEC(BID)
      CALL  BIEF_DEALLVEC(FROL)
      CALL  BIEF_DEALLVEC(FROL_OLD)
      CALL  BIEF_DEALLVEC(CROLX)
      CALL  BIEF_DEALLVEC(CROLY)
      CALL  BIEF_DEALLVEC(SHPROL)
      CALL  BIEF_DEALLVEC(DISSIP_ROL)

      DEALLOCATE(ELTROL, STAT=IERR)
      CALL CHECK_CALL(IERR,'DEALLOCATE ELTROL')
      DEALLOCATE(ETAROL, STAT=IERR)
      CALL CHECK_CALL(IERR,'DEALLOCATE ETAROL')
      DEALLOCATE(ITR_ROL, STAT=IERR)
      CALL CHECK_CALL(IERR,'DEALLOCATE ITR_ROL')
      DEALLOCATE(ISUBROL, STAT=IERR)
      CALL CHECK_CALL(IERR,'DEALLOCATE ISUBROL')

      DEALLOCATE(FREQ_ROL, STAT=IERR)
      CALL CHECK_CALL(IERR,'DEALLOCATE FREQ_ROL')
      DEALLOCATE(DIR_ROL, STAT=IERR)
      CALL CHECK_CALL(IERR,'DEALLOCATE DIR_ROL')
      DEALLOCATE(CROL, STAT=IERR)
      CALL CHECK_CALL(IERR,'DEALLOCATE CROL')
      DEALLOCATE(COS_DIR, STAT=IERR)
      CALL CHECK_CALL(IERR,'DEALLOCATE COS_DIR')
      DEALLOCATE(SIN_DIR, STAT=IERR)
      CALL CHECK_CALL(IERR,'DEALLOCATE SIN_DIR')


!
!-----------------------------------------------------------------------
!
      RETURN
      END

!***********************************************************************

      END MODULE
