MODULE M_PROFIL_UTILS
  USE M_PRECISION, ONLY: &
       DOUBLE, SIMPLE
  USE M_PARAMETRE_C, ONLY: &
       EPS1, EPS2, EPS6, EPS10, INFINI, &  ! precision
       W0, W09, W12, & ! fraction
       GPES, PI        ! physical constant
  USE M_CONSTANTES_CALCUL_C, ONLY: &
       NOYAU_SARAP, NOYAU_REZODT, NOYAU_MASCARET
  USE M_PROFIL_T, ONLY: &
       PROFIL_T
  USE M_PROFIL_PLAN_T, ONLY: &
       PROFIL_PLAN_T
  USE M_PROFIL_COURLIS_T, ONLY: &
       PROFIL_COURLIS_T
  !------------------------------
  IMPLICIT NONE
  !------------------------------
  ! FOR DIFFERENT TYPE OF EVOLUTION OF THE PROFILES BY BEDLOAD
  TYPE ARRAY_POINTER_T
     INTEGER :: DIM1, DIM2 ! dimensions
     INTEGER, POINTER :: I(:,:) => NULL() ! integer data
     REAL(DOUBLE), POINTER :: R(:,:) => NULL() ! real data
  END TYPE ARRAY_POINTER_T
  !------------------------
  REAL(DOUBLE), PARAMETER :: &
       ZERO = EPS10, & ! define zero
       CFPL = EPS1 ! W12     ! 0.5*PAS: thresold for planim
  INTEGER, PARAMETER :: & ! type of profil evolution
       PROF_EVOL_UNIF = 1, &  ! flat deposit - uniform erosion
       PROF_EVOL_SIMP = 2     ! uniform deposit and erosion
  INTEGER, PARAMETER :: &
       NC_MAX = 100, & ! number of channels
       LEFT_DRY  = 1, &
       LEFT_WET  = 2, &
       RIGHT_WET = 3, &
       RIGHT_DRY = 4
  !------------------------
  TYPE CHANNEL_T
     INTEGER :: NC ! number of channels
     INTEGER :: ID(4,NC_MAX) ! index of point
     ! 1-2 = left  dry-wet
     ! 3-4 = right wet-dry
  END type CHANNEL_T
  !------------------------
CONTAINS
  !------------------------------------
  SUBROUTINE GET_FREE_UNIT(UI)
    INTEGER, INTENT(OUT) :: UI
    LOGICAL :: PRESENT
    DO UI = 10, 99 ! find a free lecture unit
       INQUIRE(UNIT = UI, OPENED = PRESENT)
       IF(.NOT.PRESENT) RETURN
    END DO
  END SUBROUTINE GET_FREE_UNIT
  !------------------------------------
  FUNCTION STRING_ARGUMENT_COUNT(STR) RESULT(N_ARGS)
    CHARACTER(LEN=*), INTENT(IN) :: STR
    CHARACTER(LEN=1) :: CH
    INTEGER :: N, N_ARGS
    LOGICAL :: IS_NEW_ARG
    ! The character which is used to separate the arguments in STR
    CHARACTER(LEN=1), PARAMETER :: CH_SPACE = ' ', CH_TAB = ACHAR(9)
    N_ARGS = 0; IS_NEW_ARG = .TRUE. ! init
    DO N = 1, LEN_TRIM(STR)
       CH = STR(N:N) ! current character
       IF(CH == CH_SPACE .OR. CH == CH_TAB) THEN
          IS_NEW_ARG = .TRUE.
       ELSEIF(IS_NEW_ARG) THEN
          N_ARGS = N_ARGS + 1
          IS_NEW_ARG = .FALSE.
       END IF
    END DO
  END FUNCTION STRING_ARGUMENT_COUNT
  !------------------------------------
  SUBROUTINE ALLOC_ARRAY_POINTER(AP, &
       DIM1, DIM2, IDATA, RDATA)
    TYPE(ARRAY_POINTER_T), INTENT(INOUT) :: AP
    INTEGER, INTENT(IN) :: DIM1
    INTEGER, INTENT(IN), OPTIONAL :: DIM2
    LOGICAL, INTENT(IN), OPTIONAL :: IDATA, RDATA
    AP%DIM1 = DIM1
    IF(PRESENT(DIM2)) THEN
       AP%DIM2 = DIM2
    ELSE ! defaut DIM2
       AP%DIM2 = 1
    END IF
    IF(PRESENT(IDATA)) THEN
       IF(IDATA) ALLOCATE(AP%I(AP%DIM1, AP%DIM2))
    END IF
    IF(PRESENT(RDATA)) THEN
       IF(RDATA) ALLOCATE(AP%R(AP%DIM1, AP%DIM2))
    END IF
  END SUBROUTINE ALLOC_ARRAY_POINTER
  !------------------------------------
  SUBROUTINE FREE_ARRAY_POINTER(AP)
    TYPE(ARRAY_POINTER_T), INTENT(INOUT) :: AP
    IF(ASSOCIATED(AP%I)) DEALLOCATE(AP%I)
    IF(ASSOCIATED(AP%R)) DEALLOCATE(AP%R)
  END SUBROUTINE FREE_ARRAY_POINTER
  !------------------------------------
  SUBROUTINE COMPT_CHANNELS(CH, Z0, DYP, LIMIT)
    TYPE(CHANNEL_T), INTENT(OUT) :: CH
    REAL(DOUBLE), INTENT(IN) :: Z0, DYP(:) ! x-coord
    INTEGER, INTENT(IN), OPTIONAL :: LIMIT(2)
    INTEGER :: POINT(2), IPOIN, IC, NC, ID(4, NC_MAX)
    !
    IF (PRESENT(LIMIT)) THEN
       POINT = LIMIT
       IF(POINT(1) < 1 .OR. POINT(2) > SIZE(DYP)) &
            STOP "ERROR IN COMPT_CHANNELS: GIVEN LIMIT OUT OF RANK"
    ELSE
       POINT(1) = 1
       POINT(2) = SIZE(DYP)
    END IF
    ! init
    NC      = 0
    ID(:,:) = 0
    IPOIN   = POINT(1)
    ! find left/right-wet banks
    LOOP_LEFT_WET: DO WHILE (IPOIN < POINT(2) .AND. NC < NC_MAX)
       ! left
       IF(DYP(IPOIN) < Z0) THEN
          NC = NC + 1
          ID(LEFT_WET, NC) = IPOIN
          ! right
          LOOP_RIGHT_WET: DO
             IF(DYP(IPOIN + 1) > Z0) THEN
                ID(RIGHT_WET, NC) = IPOIN
                EXIT LOOP_RIGHT_WET
             ELSE IF(IPOIN + 1 == POINT(2)) THEN ! right bank reached !
                ID(RIGHT_WET, NC) = POINT(2)
                EXIT LOOP_RIGHT_WET
             END IF
             IPOIN = IPOIN + 1
          END DO LOOP_RIGHT_WET
          ! check
          IF( ID(LEFT_WET,NC) == ID(RIGHT_WET,NC)) THEN
             !STOP "ERROR: ONLY 1 POINT FOUND ON THE CHANNEL"
             !PRINT *, "WARNING : ONLY 1 POINT FOUND ON THE CHANNEL"
             ID(LEFT_WET, NC) = 0
             ID(RIGHT_WET, NC) = 0
             NC = NC - 1 ! ignore this channel
          END IF
       END IF
       IPOIN = IPOIN + 1
    END DO LOOP_LEFT_WET
    ! find left/right-dry banks
    DO IC=1, NC
       ! left
       IPOIN = ID(LEFT_WET, IC)
       LOOP_LEFT_DRY: DO WHILE(IPOIN > POINT(1))
          IF(DYP(IPOIN) > DYP(IPOIN - 1)) &
               EXIT LOOP_LEFT_DRY
          IPOIN = IPOIN - 1
       END DO LOOP_LEFT_DRY
       ID(LEFT_DRY, IC) = IPOIN ! init
       ! right
       IPOIN = ID(RIGHT_WET, IC)
       LOOP_RIGHT_DRY: DO WHILE(IPOIN < POINT(2))
          IF(DYP(IPOIN) > DYP(IPOIN + 1)) &
               EXIT LOOP_RIGHT_DRY
          IPOIN = IPOIN + 1
       END DO LOOP_RIGHT_DRY
       ID(RIGHT_DRY, IC) = IPOIN
       !WRITE(*, *) "CHANNEL: ", IC, Z0, &
       !     DYP(ID(LEFT_WET, IC)-1), DYP(ID(LEFT_WET, IC)), &
       !     DYP(ID(RIGHT_WET, IC)), DYP(ID(RIGHT_WET, IC)+1)
    END DO
    ! result
    CH%NC = NC
    CH%ID = ID
  END SUBROUTINE COMPT_CHANNELS
  !------------------------------------
  SUBROUTINE CSUR_PROFIL(NPAS, DZ, S1, P1, B1, H, S, P, B)
    INTEGER, INTENT(IN) :: NPAS ! nombre de pas de planimetrage
    REAL(DOUBLE), INTENT(IN) :: DZ ! pas de planimetrage
    REAL(DOUBLE), INTENT(IN) :: S1(:), P1(:), B1(:) ! tabeaux de planimetrage
    REAL(DOUBLE), INTENT(IN) :: H ! tirant d'eau
    REAL(DOUBLE), INTENT(OUT) :: S, P, B ! fonction interpolée
    INTEGER :: JG, JD
    REAL(DOUBLE) :: DY, DYDZ, SG, PG, BG, SD, PD, BD
    ! RECHERCHE DE L'INTERVALLE CONTENANT LE TIRANT D'EAUY
    !PRINT *, "H = ", H, "DZ = ", DZ
    JG = INT(H / DZ) + 1
    JD = JG + 1
    IF (JG < 1) THEN
       STOP "ERROR CSUR_PROFIL: JG < 1"
    ELSE IF (JD > NPAS) THEN ! prolongation
       JG = NPAS
       SG = S1(JG)
       PG = P1(JG)
       BG = B1(JG)
       DY = H - REAL(JG - 1, DOUBLE)*DZ
       !
       S  = SG + BG*DY
       P  = PG + 2.D0*DY
       B  = BG
    ELSE ! 1 <= JG < JD <= NPAS
       SG = S1(JG)
       PG = P1(JG)
       BG = B1(JG)
       DY = H - REAL( JG - 1, DOUBLE)*DZ
       SD = S1(JD)
       PD = P1(JD)
       BD = B1(JD)
       !
       DYDZ = DY / DZ
       S  = SG + (SD - SG)*DYDZ
       P  = PG + (PD - PG)*DYDZ
       B  = BG + (BD - BG)*DYDZ
    END IF
  END SUBROUTINE CSUR_PROFIL
  !------------------------------------
  SUBROUTINE READ_VAR_LIDO(NVAR, KEY, LIDO, VAR)
    INTEGER, INTENT(IN) :: NVAR
    CHARACTER(LEN=*), INTENT(IN) :: KEY, LIDO
    REAL(DOUBLE), INTENT(OUT) :: VAR(:)
    CHARACTER(LEN=132) :: CHAINE
    INTEGER :: MSG, UI, I
    LOGICAL :: KEY_FOUND
    !
    CALL GET_FREE_UNIT(UI)
    OPEN(UNIT = UI, FILE = LIDO, ACCESS = 'SEQUENTIAL', ACTION = 'READ', &
         FORM = 'FORMATTED', STATUS = 'OLD', POSITION = 'REWIND',  IOSTAT = MSG)
    IF(MSG /= 0) STOP "ERROR: CAN NOT OPEN "
    KEY_FOUND = .FALSE.
    !PRINT *, "NVAR = ", NVAR
    LOOP_READ: DO WHILE (MSG == 0)
       READ(UI, '(A)', IOSTAT = MSG) CHAINE
       !PRINT *, CHAINE
       IF(INDEX(CHAINE, KEY) /= 0) THEN ! key found
          KEY_FOUND = .TRUE.
          READ(UI, *, IOSTAT = MSG) (VAR(I), I=1, NVAR)
          IF(MSG /= 0) STOP "ERROR: CAN NOT READ THE VALUE"
          EXIT LOOP_READ
       END IF
    END DO LOOP_READ
    !PRINT *, VAR
    IF(.NOT. KEY_FOUND) STOP "ERROR: CAN NOT FOUND THE KEY "
    CLOSE(UI)
  END SUBROUTINE READ_VAR_LIDO
  !------------------------------------
END MODULE M_PROFIL_UTILS
