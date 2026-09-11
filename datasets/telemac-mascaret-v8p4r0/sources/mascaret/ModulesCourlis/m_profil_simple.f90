MODULE M_PROFIL_SIMPLE
  USE M_PROFIL_UTILS
  !------------------------------
  IMPLICIT NONE
  !------------------------------
  TYPE PROFIL_SIMPLE_T
     CHARACTER(255) :: FILE_LIMIT ! limit of erosion
     REAL(DOUBLE) :: LIMIT
     REAL(DOUBLE), POINTER :: CV(:) ! volume of erosion/depot
     REAL(DOUBLE), POINTER :: DZ(:) ! thickness
     REAL(DOUBLE), POINTER :: Z0(:) ! cote
     REAL(DOUBLE), POINTER :: H0(:) ! height
     REAL(DOUBLE), POINTER :: B0(:) ! width
     REAL(DOUBLE), POINTER :: S0(:) ! area
     REAL(DOUBLE), POINTER :: P0(:) ! perimeter
     TYPE(CHANNEL_T), POINTER :: CH(:) ! channels on the profile
  END TYPE PROFIL_SIMPLE_T
  !-----------------------
CONTAINS
  !------------------------------------
  SUBROUTINE INIT_PROFIL_SIMPLE(NPROF, NPAS, PROF_SIMP, &
       PROF_PAS, PROF_COORD, PROF_INIT)
    !---------------------
    INTEGER, INTENT(IN) :: NPROF, NPAS
    TYPE(PROFIL_SIMPLE_T), INTENT(OUT) :: PROF_SIMP
    REAL(DOUBLE), INTENT(IN)           :: PROF_PAS(:)
    TYPE(ARRAY_POINTER_T), INTENT(IN)  :: PROF_COORD(:)
    TYPE(PROFIL_PLAN_T), INTENT(IN)    :: PROF_INIT
    INTEGER :: MSG, IPROF, NPOIN
    REAL(DOUBLE) :: PAS, H0, Z0, B0, S0, P0, ZREF
    REAL(DOUBLE), POINTER :: DYP(:), S1(:), P1(:), B1(:) ! alias
    !---------------------
    !PRINT *, "! read H0"
    ALLOCATE( &
         PROF_SIMP%H0(NPROF), &
         PROF_SIMP%Z0(NPROF), &
         STAT = MSG)
    IF(MSG /= 0) STOP "ERROR: CAN NOT ALLOCATE H0, Z0"
    ! read H0
    IF(PROF_SIMP%FILE_LIMIT == ' ') THEN ! an uniform height of erosion is imposed
       H0 = PROF_SIMP%LIMIT
       DO IPROF=1, NPROF
          ZREF = MINVAL(PROF_COORD(IPROF)%R(:, 2))
          PROF_SIMP%H0(IPROF) = H0
          PROF_SIMP%Z0(IPROF) = H0 + ZREF
       END DO
    ELSE ! the height of erosion is given from a LIDO file => read this file
       CALL READ_VAR_LIDO(NPROF, 'Z', PROF_SIMP%FILE_LIMIT, PROF_SIMP%Z0)
       DO IPROF=1, NPROF
          ZREF = MINVAL(PROF_COORD(IPROF)%R(:, 2))
          PROF_SIMP%H0(IPROF) = PROF_SIMP%Z0(IPROF) - ZREF
          IF(PROF_SIMP%H0(IPROF) < EPS6) &
               STOP "ERREUR: LA COTE D'EROSION CORRESPOND A UN FOND SEC"
       END DO
    END IF
    !
    ! allocate the planimetred functions
    ALLOCATE( &
         PROF_SIMP%CV(NPROF), &
         PROF_SIMP%DZ(NPROF), &
         PROF_SIMP%B0(NPROF), &
         PROF_SIMP%S0(NPROF), &
         PROF_SIMP%P0(NPROF), &
         PROF_SIMP%CH(NPROF), &
         STAT = MSG)
    IF(MSG /= 0) STOP "ERROR: CAN NOT ALLOCATE CV, DZ, B0, S0, P0, NC, CH"
    !
    DO IPROF=1, NPROF
       ! dimension
       NPOIN = PROF_COORD(IPROF)%DIM1
       DYP   => PROF_COORD(IPROF)%R(:, 2)
       Z0    = PROF_SIMP%Z0(IPROF)
       H0    = PROF_SIMP%H0(IPROF)
       !PRINT *, "! compt. channels", IPROF
       CALL COMPT_CHANNELS(PROF_SIMP%CH(IPROF), Z0, DYP)
       ! init
       PROF_SIMP%CV(IPROF) = W0
       PROF_SIMP%DZ(IPROF) = W0
       ! planim
       PAS = PROF_PAS(IPROF)
       S1 => PROF_INIT%S1(IPROF,:)
       P1 => PROF_INIT%P1(IPROF,:)
       B1 => PROF_INIT%B1(IPROF,:)
       CALL CSUR_PROFIL(NPAS, PAS, S1, P1, B1, H0, S0, P0, B0)
       IF (S0 < EPS6) STOP "ERROR: S0 < EPS6"
       IF (P0 < EPS6) STOP "ERROR: P0 < EPS6"
       IF (B0 < EPS6) STOP "ERROR: B0 < EPS6"
       PROF_SIMP%S0(IPROF) = S0
       PROF_SIMP%P0(IPROF) = P0
       PROF_SIMP%B0(IPROF) = B0
    END DO
  END SUBROUTINE INIT_PROFIL_SIMPLE
  !------------------------------------
  SUBROUTINE FREE_PROFIL_SIMPLE(PROF_SIMP)
    TYPE(PROFIL_SIMPLE_T), INTENT(INOUT) :: PROF_SIMP
    DEALLOCATE( &
         PROF_SIMP%CV, &
         PROF_SIMP%DZ, &
         PROF_SIMP%H0, &
         PROF_SIMP%Z0, &
         PROF_SIMP%B0, &
         PROF_SIMP%S0, &
         PROF_SIMP%CH)
  END SUBROUTINE FREE_PROFIL_SIMPLE
  !------------------------------------
  SUBROUTINE UPDATE_PROFIL_SIMPLE (NPROF, NPAS, PROF_SIMP, &
       PROF_PAS, PROF_COORD, PROF_INIT, PROF_COURLIS, VSED)
    INTEGER, INTENT(IN) :: NPROF, NPAS
    TYPE(PROFIL_SIMPLE_T), INTENT(INOUT) :: PROF_SIMP
    REAL(DOUBLE), INTENT(IN)             :: PROF_PAS(:)
    TYPE(ARRAY_POINTER_T), INTENT(IN)    :: PROF_COORD(:)
    TYPE(PROFIL_PLAN_T), INTENT(IN)      :: PROF_INIT
    TYPE(PROFIL_COURLIS_T), INTENT(INOUT):: PROF_COURLIS(:)
    REAL(DOUBLE), INTENT(IN)             :: VSED(:)
    INTEGER :: IPROF, NPOIN, IPOIN, IPAS, NC, IC, I1, I2
    REAL(DOUBLE) :: PAS, H0, B0, S0, CV, DZ, ZREF, &
         S1Z0, Z0, S1Z1, Z1, S1Z2, Z2, Z0Z1
    TYPE(CHANNEL_T), POINTER :: CH ! alias
    ! loop on the profil
    LOOP_PROFIL: DO IPROF = 1, NPROF
       ! cummulate volume of sediment
       CV  = PROF_SIMP%CV(IPROF) + VSED(IPROF)
       DZ  = W0 ! init
       IF (ABS(VSED(IPROF)) < EPS10) CYCLE LOOP_PROFIL ! evolution can be neglected
       ! planim
       PAS = PROF_PAS(IPROF)
       H0  = PROF_SIMP%H0(IPROF)
       B0  = PROF_SIMP%B0(IPROF)
       S0  = PROF_SIMP%S0(IPROF)
       ! channels
       CH => PROF_SIMP%CH(IPROF)
       NC =  CH%NC
       ! profil courlis
       NPOIN = PROF_COURLIS(IPROF)%NBPOINT
       ! reset to initial profile
       DO IPOIN = 1, NPOIN
          PROF_COURLIS(IPROF)%Z(1, IPOIN) = PROF_COORD(IPROF)%R(IPOIN,2)
       END DO
       !
       IF (CV < W0) THEN ! erosion
          ! erosion thickness
          DZ = - CV / B0
          ! erosion inside the channels
          DO IC = 1, NC ! channels
             I1 = CH%ID(LEFT_WET , IC)
             I2 = CH%ID(RIGHT_WET, IC)
             DO IPOIN = I1, I2
                PROF_COURLIS(IPROF)%Z(1, IPOIN) = PROF_COORD(IPROF)%R(IPOIN,2) - DZ
             END DO
          END DO
       ELSE ! deposition
          ! solve the deposition thickness
          ! we find Z0 such that S1(Z0) = S0 + CV
          S1Z0 = S0 + CV
          ! first, we compute IPAS such that Z0 locate between IPAS and IPAS +1
          ! we notice that S1(H0) = S0 < S0 + D, so H0 < Z0
          ! and we can initialize IPAS with:
          IPAS = INT( H0/PAS ) + 1
          DO WHILE (PROF_INIT%S1(IPROF, IPAS+1) < S1Z0)
             IPAS = IPAS + 1
             IF (IPAS >= NPAS) STOP "ERROR PLANIM: IPAS >= NPAS"
          END DO
          Z1   = (IPAS - 1)*PAS
          S1Z1 = PROF_INIT%S1(IPROF, IPAS)
          Z2   = Z1 + PAS
          S1Z2 = PROF_INIT%S1(IPROF, IPAS+1)
          ! next, we calculate Z0 by interpolation:
          ! S1(Z0) =  S1(Z1) + (S1(Z2) - S1(Z1))*(Z0-Z1)/PAS
          ! we denote Z0Z1 = (Z0-Z1)/PAS
          Z0Z1 = (S1Z0 - S1Z1)/(S1Z2 - S1Z1)
          ! so we deduce Z0
          Z0 = Z0Z1*PAS + Z1
          ! by definition Z0 = H0 + DZ
          DZ = Z0 - H0
          IF(DZ < W0) STOP "ERROR PLANIM: DZ < 0"
          ! update the profile
          ZREF = MINVAL(PROF_COORD(IPROF)%R(:,2)) ! ZREF of the init profile
          DO IC = 1, NC ! channels
             ! uniform deposition inside each channel
             I1 = CH%ID(LEFT_WET,  IC)
             I2 = CH%ID(RIGHT_WET, IC)
             DO IPOIN = I1, I2
                PROF_COURLIS(IPROF)%Z(1, IPOIN) = PROF_COORD(IPROF)%R(IPOIN,2) + DZ
             END DO
             ! flat deposition at the left bank
             I1 = CH%ID(LEFT_DRY, IC)
             I2 = CH%ID(LEFT_WET, IC) -1
             DO IPOIN = I1, I2
                PROF_COURLIS(IPROF)%Z(1, IPOIN) = MAX(Z0 + ZREF, PROF_COORD(IPROF)%R(IPOIN,2))
             END DO
             ! flat deposition at the right bank
             I1 = CH%ID(RIGHT_WET, IC) +1
             I2 = CH%ID(RIGHT_DRY, IC)
             DO IPOIN = I1, I2
                PROF_COURLIS(IPROF)%Z(1, IPOIN) = MAX(Z0 + ZREF, PROF_COORD(IPROF)%R(IPOIN,2))
             END DO
          END DO
       END IF
       ! update ZREF of PROF_COURLIS
       ZREF = MINVAL(PROF_COURLIS(IPROF)%Z(1, :))
       PROF_COURLIS(IPROF)%ZREF(1) = ZREF
       ! update CV and DZ of PROF_SIMP
       PROF_SIMP%CV(IPROF) = CV
       PROF_SIMP%DZ(IPROF) = DZ
    END DO LOOP_PROFIL
  END SUBROUTINE UPDATE_PROFIL_SIMPLE
  !------------------------------------
  SUBROUTINE PLANIM_PROFIL_SIMPLE (IPROF, NPAS, PROF_SIMP, &
       PROF_PAS, PROF_INIT, PROF_PLAN)
    INTEGER, INTENT(IN) :: IPROF, NPAS
    TYPE(PROFIL_SIMPLE_T), INTENT(INOUT) :: PROF_SIMP
    REAL(DOUBLE), INTENT(IN)             :: PROF_PAS(:)
    TYPE(PROFIL_PLAN_T), INTENT(IN)      :: PROF_INIT
    TYPE(PROFIL_PLAN_T), INTENT(INOUT)   :: PROF_PLAN
    INTEGER :: IPAS, NC
    REAL(DOUBLE) :: PAS, DZ, CV, H0, B0, P0, S0, &
         Z, S, P, B, S00, P00, B00
    REAL(DOUBLE), POINTER :: S1(:), P1(:), B1(:) ! alias
    TYPE(CHANNEL_T), POINTER :: CH ! alias

    ! update the PROF_PLAN
    PAS  = PROF_PAS(IPROF)
    S1  => PROF_INIT%S1(IPROF,:)
    P1  => PROF_INIT%P1(IPROF,:)
    B1  => PROF_INIT%B1(IPROF,:)
    !
    CV   = PROF_SIMP%CV(IPROF)
    DZ   = PROF_SIMP%DZ(IPROF)
    H0   = PROF_SIMP%H0(IPROF)
    S0   = PROF_SIMP%S0(IPROF)
    B0   = PROF_SIMP%B0(IPROF)
    P0   = PROF_SIMP%P0(IPROF)
    CH  => PROF_SIMP%CH(IPROF)
    NC   = CH%NC

    ! modify the planimetrage for the MINOR BED (LIT MINEUR)
    IF (CV < W0) THEN ! erosion
       DO IPAS = 1, NPAS
          Z = (IPAS - 1) * PAS
          IF (Z < H0) THEN
             CALL CSUR_PROFIL(NPAS, PAS, S1, P1, B1, Z, S, P, B)
             PROF_PLAN%S1(IPROF, IPAS) = S
             PROF_PLAN%P1(IPROF, IPAS) = P
             PROF_PLAN%B1(IPROF, IPAS) = B
          ELSEIF (Z < H0 + DZ) THEN
             PROF_PLAN%B1(IPROF, IPAS) = B0
             PROF_PLAN%P1(IPROF, IPAS) = P0 + (Z - H0)*2.D0*NC
             PROF_PLAN%S1(IPROF, IPAS) = S0 + (Z - H0)*B0
          ELSE ! H0 + DZ < Z
             CALL CSUR_PROFIL(NPAS, PAS, S1, P1, B1, Z - DZ, S, P, B)
             PROF_PLAN%S1(IPROF, IPAS) = S + B0*DZ
             PROF_PLAN%P1(IPROF, IPAS) = P + DZ*2.D0*NC
             PROF_PLAN%B1(IPROF, IPAS) = B
          END IF
       END DO
    ELSE ! deposition
       CALL CSUR_PROFIL(NPAS, PAS, S1, P1, B1, H0 + DZ, S00, P00, B00)
       DO IPAS = 1, NPAS
          Z = (IPAS - 1) * PAS
          IF (Z < H0) THEN
             CALL CSUR_PROFIL(NPAS, PAS, S1, P1, B1, Z, S, P, B)
             PROF_PLAN%S1(IPROF, IPAS) = S
             PROF_PLAN%P1(IPROF, IPAS) = P
             PROF_PLAN%B1(IPROF, IPAS) = B
          ELSE ! H0 < Z
             CALL CSUR_PROFIL(NPAS, PAS, S1, P1, B1, Z + DZ, S, P, B)
             PROF_PLAN%S1(IPROF, IPAS) = S - CV
             PROF_PLAN%P1(IPROF, IPAS) = P + B00 - B0 - P00 + P0
             PROF_PLAN%B1(IPROF, IPAS) = B
          END IF
       END DO
    END IF

  END SUBROUTINE PLANIM_PROFIL_SIMPLE
  !------------------------------------
END MODULE M_PROFIL_SIMPLE
