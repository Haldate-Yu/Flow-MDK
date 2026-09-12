!== Copyright (C) 2000-2022 EDF-CEREMA ==
!
!   This file is part of MASCARET.
!
!   MASCARET is free software: you can redistribute it and/or modify
!   it under the terms of the GNU General Public License as published by
!   the Free Software Foundation, either version 3 of the License, or
!   (at your option) any later version.
!
!   MASCARET is distributed in the hope that it will be useful,
!   but WITHOUT ANY WARRANTY; without even the implied warranty of
!   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
!   GNU General Public License for more details.
!
!   You should have received a copy of the GNU General Public License
!   along with MASCARET.  If not, see <http://www.gnu.org/licenses/>
!
subroutine calcul_Q(Hu, Hd, Hb, e, n, b, Q, zeta_k, zeta0)
   implicit none
   REAL(KIND=8) :: Hu, Hd, Hb, e, n, b, DELTA_H, H1, H2
   REAL(KIND=8) :: state, tau_h, sigma_s, u0, zeta_k, zeta0, eps, m
   REAL(KIND=8) :: Q,RH,COEF,COEF1
   REAL(KIND=8) :: HAMONT,HAVAL
   REAL(KIND=8), PARAMETER :: G_CONSTANT = 2 * 9.81
! initialization
   Q = 0.D0
! check where's the "upstream"
   HAMONT = HU - Hb
   HAVAL = HD - Hb
   IF (HAVAL <= 0.D0) HAVAL=0.1D0
   IF ((HAMONT > 0.D0).AND.(HAMONT > HAVAL)) THEN
      state = e/HAMONT
      tau_h = HAVAL/HAMONT
      sigma_s = 2.31*tau_h*(1-tau_h)**0.4 
      u0 = 0.6-0.176*state 
      ! zeta_k = 0.7
      ! zeta0 = 0.45
      eps = 1-0.2*(zeta_k+(n-1)*zeta0)*HAMONT/(n*b) 
      IF ((2/HAMONT).LE.0.24) then
         m = 0.385+0.171*(2/HAMONT)**0.657
      else
         m = 0.414*(2/HAMONT)**(-0.0652)
      endif
      ! CHECK STATE
      if (state <= 0.65) then ! HOLE
         Q = sigma_s*u0*e*b*(G_CONSTANT*HAMONT)**0.5 !sigma_s
         !print*,'calcul_q Q_B =',Q
      else ! WEIR
         Q = sigma_s*m*eps*b*((G_CONSTANT)**0.5)*(HAMONT**1.5) !COEF
         ! ENDIF
         !print*,'calcul_q Q_S =',Q
      endif
   ! ELSE
      ! PRINT*,'**H_UPSTREAM <= 0**'
   ENDIF
end subroutine calcul_Q

subroutine Q_SUM(Hu, Hd, Hb, E_n, sum_Q)
   implicit none
   REAL(KIND=8) :: Hu, Hd, Hb, E_n(:), sum_Q
   REAL(KIND=8) :: Q_single
   integer :: i
   REAL(KIND=8) :: n = 0.0
   REAL(KIND=8), PARAMETER :: b = 9.0
   sum_Q = 0 !initialization
   do i = 1, size(E_n)
      if (E_n(i)>0) then
         n=n+1.d0
      endif
   enddo
   do i=1, size(E_n)
      call calcul_Q(Hu,Hd,Hb,E_n(i),n,b,Q_single,E_n(7),E_n(8))
      sum_Q = sum_Q + Q_single
   end do
end subroutine Q_SUM

! subroutine CALCUL_GATE_Q(HU, HD, HB, E, Q_GATE)
!    implicit none
!    REAL(KIND=8)   :: HU, HD, HB
!    REAL(KIND=8)   :: N_GATE=5.0
!    REAL(KIND=8)   :: B_GATE=9.0
!    REAL(KIND=8),dimension(5) :: E
!    REAL(KIND=8)   :: Q_GATE
!    INTERFACE
!       subroutine Q_SUM(Hu, Hd, Hb, E_n, n, b, sum_Q)
!          REAL(KIND=8) :: Hu, Hd, Hb, E_n(:), n, b, sum_Q
!          REAL(KIND=8) :: Q_single
!       end subroutine Q_SUM
!   END INTERFACE
!    CALL Q_SUM(HU,HD,HB,E,N_GATE,B_GATE,Q_GATE)
! !   Q_GATE = MAX(0.D0,Q_GATE)
! end subroutine CALCUL_GATE_Q

subroutine READ_E(nlines,E_FILE)
   implicit none
   integer :: nlines
   integer :: iline,J
   integer :: iostat_value
   REAL(kind=8),DIMENSION(1000,8) :: E_FILE
   character(len=256)  :: line
   !REAL(kind=8), ALLOCATABLE, DIMENSION(:,:) :: E_GATE
   !
   NLINES = 0
   ! READ E ARRAY FROM GATE.TXT
   OPEN(unit=180,file='./GATE.txt',status='old',action='read')
   ! CHECK HOW MANY LINES IN IT
   iostat_value = 1
   DO WHILE(.TRUE.)
      READ(180,'(A)',iostat=iostat_value) line
      IF (iostat_value /=0) EXIT
      NLINES=NLINES+1
      READ(LINE,*) (E_FILE(NLINES,J),J=1,8)
   END DO
   CLOSE(180)
END subroutine READ_E

subroutine FLUDEV( &
              FLULOC , &
              FLULOD , &
              FLULOG , &
              NSECD0 , &
                ITYP , &
                IPOS , &
                ZDEV , &
               DEBIT , &
     Epaisseur_Seuil , &
            Nb_Point , &
           Loi_Debit , &
            Loi_Cote , &
                  SD , &
                  ZD , &
                 PRD , &
                  SG , &
                  ZG , &
                  HG , &
                 PRG , &
                  QG , &
                  QD , &
                  DZ , &
               ALGEO , &
               COTR  , &
                 DT  , &
               COEF  , &
             NMLARG  , &
             ERREUR  )

!***********************************************************************
! PROGICIEL : MASCARET        N. GOUTAL
!
! VERSION : V8P4R0+              EDF-CEREMA
! MODIFICATION BY MAURICE FOR GATE CODE SIMULATION           
!***********************************************************************
!   FONCTION :  CALCUL DES FLUX DU AU DEVERSEMENT
!                    AU DESSUS D'UN BARRAGE
!
!-----------------------------------------------------------------------
!                             ARGUMENTS
! .___________.____.____.______________________________________________.
! !    NOM    !TYPE!MODE!                   ROLE                       !
! !___________!____!____!______________________________________________!
! !  FLULOC   ! TR !  A ! FLUX LOCAL  CALCULE PAR ROE                  !
! !  FLULOD   ! TR !  D ! FLUX SORTANT A DROITE DU BARRAGE             !
! !  FLULOG   ! TR !  D ! FLUX RENTRANT A GAUCHE DU BARRAGE            !
! !  NSECD0   ! TR !  D ! SECTION LIMITE DROITE                        !
! !  ITYP     !  I !  D ! TYPE DOUVRAGE                                !
! !  IPOS     !  I !  D ! POSITION DU BARRAGE                          !
! !  ZDEV     !  R !  D ! COTE DE DEVERSEMENT                          !
! !  SD       !  R !  M ! ETAT A DROITE DU BARRAGE                     !
! !  ZD       !  R !    !                                              !
! !  PRD      !  R !  M !         "                                    !
! !  SG       !  R !  M ! ETAT A GAUCHE DU BARRAGE                     !
! !  ZG       !  R !    !                                              !
! !  HG       !  R !  M !         "                                    !
! !  PRG      !  R !  M !         "                                    !
! !  QG       !  R !  M !         "                                    !
! !  QD       !  R !  M !                                              !
! !  DZ       ! TR !    !                                              !
! !  ALGEO    ! TR !  M ! LARGEUR         PLANIMETREE                  !
! !  COTR     ! TR !  M ! COTE DU FOND                                 !
! !  DT       ! TR !  M ! PAS DE TEMPS                                 !
! !  COEF     ! TR !  D ! COEFFICICIENT DE DEBIT                       !
! !  NMLARG   !  I !  D !                                              !
! !___________!____!____!______________________________________________!
!
!     TYPE : I (ENTIER), R (REEL), A (ALPHANUMERIQUE), T (TABLEAU)
!            L (LOGIQUE)   .. ET TYPES COMPOSES (EX : TR TABLEAU REEL)
!     MODE : D (DONNEE NON MODIFIEE), R (RESULTAT), M (DONNEE MODIFIEE)
!            A (AUXILIAIRE MODIFIE)
!
!***********************************************************************
!   ALGEO fait partie d'une structure de donnees

   !============================= Declarations ===========================

   !.. Modules importes ..
   !----------------------
   use M_PRECISION
   use M_INTERPOLATION_S  ! Interpolation
   use M_PARAMETRE_C ! EPS3
   use M_ERREUR_T    ! Type ERREUR_T
   use M_QSING_I     ! Interface de la fonction    QSING
   use M_ERODEV_I    ! Interface du sous-programme ERODEV

   !.. Declarations explicites ..
   !-----------------------------
   implicit none

   !.. Arguments ..
   !---------------
   ! 1ere dimension IM, 2nde dimension 2
   real(DOUBLE), dimension(:,:)  , intent(  out) :: FLULOC
   ! 1ere dimension IM
   real(DOUBLE), dimension(:)    , intent(  out) :: FLULOD,FLULOG
   integer     ,                   intent(inout) :: NSECD0
   integer     ,                   intent(inout) :: ITYP
   integer     ,                   intent(in)    :: IPOS
   integer     ,                   intent(in)    :: Epaisseur_Seuil
   real(DOUBLE),                   intent(inout) :: ZDEV
   real(DOUBLE),                   intent(inout) :: DEBIT
   real(DOUBLE),                   intent(in)    :: SD,ZD
   real(DOUBLE),                   intent(in)    :: PRD
   real(DOUBLE),                   intent(in)    :: SG,ZG,HG
   real(DOUBLE),                   intent(in)    :: PRG
   real(DOUBLE),                   intent(in)    :: QG,QD
   ! 1ere dimension IM
   real(DOUBLE), dimension(:)    , intent(in)    :: DZ
   ! 1ere dimension IM, 2nde dimension NMLARG
   real(DOUBLE), dimension(:,:)  , intent(in)    :: ALGEO
   ! 1ere dimension IM
   real(DOUBLE), dimension(:)    , intent(in)    :: COTR
    ! Dimension Nb_Point
   real(DOUBLE),dimension(:)     , intent(in)    :: Loi_Debit,Loi_Cote
   real(DOUBLE),                   intent(in)    :: DT,COEF
   integer     ,                   intent(in)    :: NMLARG,Nb_Point
   Type (ERREUR_T)               , intent(inout) :: ERREUR

   !.. Variables locales ..
   !-----------------------
   real(DOUBLE)   :: HDEV,QDEV,ZINT,VG,AT,H_GD
   integer :: ntimestep=0
   INTEGER :: NLINES,ILINE
   REAL(DOUBLE), ALLOCATABLE, DIMENSION(:,:) :: E_GATE
   REAL(DOUBLE),DIMENSION(1000,8) :: E_FILE
   REAL(DOUBLE),DIMENSION(5) :: E
   LOGICAL :: end_of_file,exist_of_file
   INTEGER :: iostat_value,j
   character(len=256)  :: line
   character(len=256)  :: file_name
   character(len=256)  :: pathNode
   CHARACTER(LEN=256)  :: TITLE
   save ntimestep,E_FILE,NLINES
   !
   !character(132) :: !arbredappel_old ! arbre d'appel precedent
   !
   INTERFACE
   !   subroutine CALCUL_GATE_Q(HU, HD, HB, E, Q_GATE)
   !    REAL(KIND=8) :: HU
   !    REAL(KIND=8) :: HD
   !    REAL(KIND=8) :: HB
   !    REAL(KIND=8),DIMENSION(5) :: E
   !    REAL(KIND=8) :: Q_GATE
   !   end subroutine CALCUL_GATE_Q
     !
     subroutine Q_SUM(Hu, Hd, Hb, E_n, sum_Q)
      implicit none
      REAL(KIND=8) :: Hu, Hd, Hb, E_n(:), sum_Q
     end subroutine Q_SUM
     subroutine READ_E(NLINES,E_FILE)
      !REAL(kind=8), ALLOCATABLE, DIMENSION(:,:) :: E_GATE
      integer :: NLINES
      REAL(kind=8),DIMENSION(1000,8) :: E_FILE
     end subroutine READ_E
   END INTERFACE
   !============================= Instructions ===========================

   ! INITIALISATION
   !===============
   Erreur%Numero = 0
   !arbredappel_old    = trim(!Erreur%arbredappel)
   !Erreur%arbredappel = trim(!Erreur%arbredappel)//'=>FLUDEV'

!   if( ( ITYP == 3 ) .or. ( ITYP == 4 ) ) then
   IF(AT == 0.D0) THEN
      open(unit=181,file='Q_GATE_OUT.txt',status='REPLACE')
      TITLE = 'TIME Q_GATE'
      WRITE(181,*) TRIM(TITLE)
   ENDIF
   if( ITYP == 3 ) then
      !
      !      CALCUL DE LA HAUTEUR ET DU DEBIT  DEVERSES AU DESSUS D'SEUIL MINCE OU EPAIS
      !
      !ntimestep = ntimestep + 1
      !print*,'test here fludev',ntimestep
      HDEV = ZG - ZDEV
      !print*,'HDEV, ZG=',HDEV,ZG
      if( ( HDEV >= EPS3 ) .or. ( debit > 0.d0 ) ) then

         if( ITYP == 3 ) then
            ! BARRAGE ERODABLE
            call ERODEV( &
             ZDEV   , &
             ZG     , &
             HG     , &
             QD     , &
             IPOS   , &
             ALGEO  , &
             DZ     , &
             DT     , &
             NMLARG , &
             ERREUR   &
             )

            if (Erreur%Numero /= 0) then
               return
            endif

            if( ZDEV <= COTR(IPOS) ) then
               ZDEV = COTR(IPOS)
               ITYP = 1
               !Erreur%arbredappel = !arbredappel_old
               return
            endif
         endif
         if (HDEV >= EPS3) then
            !      IL Y A DEVERSEMENT
            VG   = QG / SG
            QDEV = QSING( COEF , ZG , HG , ZD , VG , &
                          ZDEV , DZ , ALGEO , IPOS , Epaisseur_Seuil , &
                          NMLARG , ERREUR )
         else
            QDEV = 0.D0
         endif

         QDEV = QDEV + DEBIT
         FLULOC(IPOS,1) = QDEV
         FLULOD(IPOS)   = (QDEV**2) / SG + PRG

         !         CALCUL DU FLUX A L'AVAL DU BARRAGE
         if( SD >= .1_DOUBLE ) then
            !              FLUVIAL A l'AVAL
            FLULOG(IPOS) = (QDEV**2) / SD + PRD
         else
            FLULOG(IPOS) = PRD
         endif
      else
         FLULOD(IPOS)   = -( QG**2 ) / SG + PRG
         FLULOG(IPOS)   = PRD
         FLULOC(IPOS,1) = 0._DOUBLE
         FLULOC(IPOS,2) = 0._DOUBLE
      endif

   ELSEIF (ITYP == 4) THEN
      QDEV = 0.D0
      HDEV = ZG - ZDEV
      H_GD = ZG - ZD
      E = [0.D0,0.D0,0.D0,0.D0,0.D0]
      !end_of_file = .FALSE.
      IF(ntimestep == 0) THEN
         NLINES = 0
         CALL READ_E(NLINES,E_FILE)
         print*,'NLINES= ',NLINES
      END IF
      ntimestep = ntimestep +1
      AT = DT*ntimestep
      DO ILINE=1, NLINES-1
         IF ((AT>=E_FILE(ILINE,1)).AND.(AT<E_FILE(ILINE+1,1))) THEN
            E = E_FILE(ILINE,2:6)
         END IF
      END DO
      ! CALCULATE Q_GATE AND GIVE IT TO DEBIT
      IF ((HDEV >= EPS3).OR.(DEBIT > 0.D0)) THEN
      !IF (.TRUE.) THEN
         CALL Q_SUM(ZG,ZD,ZDEV,E,QDEV)
         ! PRINT*,'TEST AT === ',AT
         !IF (mod(ntimestep,100) == 0) PRINT*,'TYPE=4, QDEV=',QDEV
         QDEV = QDEV + DEBIT
         IF (mod(AT,3600.D0) == 0.D0) THEN
            PRINT*,'=====*****===== '
            PRINT*,'TEST AT === ',AT
            PRINT*,'TEST Q,QG=',QDEV,QG
            PRINT*,'TEST ZG,ZD=',ZG,ZD
            PRINT*,'SG,SD,PRG,PRD=',SG,SD,PRG,PRD
         ENDIF
!
         ! IF (QDEV > 0.D0) THEN
         IF ((QDEV<=QG).AND.(QG.GT.50.18)) THEN
            QDEV = MIN(QDEV+50.18,QG)
            FLULOC(IPOS,1) = QDEV
            FLULOD(IPOS) = (QDEV**2) / SG + PRG
            if( SD >= .1_DOUBLE ) then
               !              FLUVIAL A l'AVAL
               FLULOG(IPOS) = (QDEV**2) / SD + PRD
            else
               FLULOG(IPOS) = PRD
            endif
         ! ENDIF
         ELSE
            FLULOC(IPOS,1) = QG
            FLULOD(IPOS) = (QG**2) / SG + PRG
            if( SD >= .1_DOUBLE ) then
               !              FLUVIAL A l'AVAL
               FLULOG(IPOS) = (QG**2) / SD + PRD
            else
               FLULOG(IPOS) = PRD
            endif
         ENDIF
      ELSE
         FLULOD(IPOS)   = -( QG**2 ) / SG + PRG
         FLULOG(IPOS)   = PRD
         FLULOC(IPOS,1) = 0._DOUBLE
         FLULOC(IPOS,2) = 0._DOUBLE
      ENDIF
      IF (mod(AT,3600.D0) == 0.D0) THEN
         PRINT*,'=====^^^^^===== '
         PRINT*,'TEST Q,QG=',QDEV,QG
         PRINT*,'=====^^^^^===== '
         WRITE(181,*) AT,FLULOC(IPOS,1)
      ENDIF
   ELSE
      !
      !  Lois Q= F(Zam) ou Q=F(Zav)
      !
      If( ITYP == 6 ) ZINT = ZG
      if( ITYP == 7 ) ZINT = ZD
      !
      !  Interpolation pour obtenir le debit
      !
      call INTERPOLATION_S              ( &
         QDEV                         , &
         ZINT                         , &
         1                            , &
         Loi_Cote                     , &
         Loi_Debit                    , &
         nb_point                     , &
         Erreur                         &
                                        )
      !
      !  Interpolation pour obtenir le debit 
      !
      QDEV           = QDEV + DEBIT
      FLULOC(IPOS,1) = QDEV
      FLULOD(IPOS)   = (QDEV**2) / SG + PRG
      !         CALCUL DU FLUX A L'AVAL DU BARRAGE
      if( SD >= .1_DOUBLE ) then
         !              FLUVIAL A l'AVAL
         FLULOG(IPOS) = (QDEV**2) / SD + PRD
      else
         FLULOG(IPOS) = PRD
      endif

   endif
   300 FORMAT(6F8.2)

  !------------------
  ! Fin du traitement
  !------------------

  !Erreur%arbredappel = !arbredappel_old

  return

end subroutine FLUDEV


