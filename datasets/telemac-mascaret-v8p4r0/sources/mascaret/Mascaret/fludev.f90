!======================================================================
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
!======================================================================

subroutine calcul_Q(Hu, Hd, Hb, e, n, b, Q, zeta_k, zeta0)
   implicit none
   REAL(KIND=8) :: Hu, Hd, Hb, e, n, b, DELTA_H, H1, H2
   REAL(KIND=8) :: state, tau_h, sigma_s, u0, zeta_k, zeta0, eps, m
   REAL(KIND=8) :: Q,RH,COEF,COEF1
   REAL(KIND=8) :: HAMONT,HAVAL
   REAL(KIND=8), PARAMETER :: G_CONSTANT = 2 * 9.81
   
   ! initialization
   Q = 0.D0
   
   if ((e <= 0.D0) .or. (n <= 0.D0) .or. (b <= 0.D0)) return

   ! check where's the "upstream"
   HAMONT = HU - Hb
   HAVAL = HD - Hb
   IF (HAVAL <= 0.D0) HAVAL=0.1D0
   
   IF ((HAMONT > 0.D0).AND.(HAMONT > HAVAL)) THEN
      state = e/HAMONT
      tau_h = HAVAL/HAMONT
      sigma_s = 2.31*tau_h*(1-tau_h)**0.4 
      u0 = 0.6-0.176*state
      eps = 1.D0 - 0.2D0*(zeta_k + (n - 1.D0)*zeta0)*HAMONT/(n*b)
      IF ((2/HAMONT).LE.0.24) then
         m = 0.385+0.171*(2/HAMONT)**0.657
      else
         m = 0.414*(2/HAMONT)**(-0.0652)
      endif
      
      ! CHECK STATE
      if (state <= 0.65) then 
         ! HOLE
         Q = sigma_s*u0*e*b*(G_CONSTANT*HAMONT)**0.5
      else 
         ! WEIR
         Q = sigma_s*m*eps*b*((G_CONSTANT)**0.5)*(HAMONT**1.5) 
      endif
   ENDIF
end subroutine calcul_Q

subroutine Q_SUM(Hu, Hd, Hb, E_n, sum_Q)
   implicit none
   REAL(KIND=8) :: Hu, Hd, Hb, E_n(:), sum_Q
   REAL(KIND=8) :: Q_single, n, zeta_k, zeta0
   integer :: i, gate_count
   REAL(KIND=8), PARAMETER :: b = 9.D0
   sum_Q = 0 !initialization

   gate_count = MIN(size(E_n), 5)
   if (gate_count <= 0) return

   n = 0.D0
   do i = 1, gate_count
      if (E_n(i)>0) then
         n=n+1.d0
      endif
   enddo

   if (n <= 0.D0) return

   zeta_k = 0.7D0
   zeta0 = 0.45D0
   if (size(E_n) >= 6) zeta_k = E_n(6)
   if (size(E_n) >= 7) zeta0  = E_n(7)

   do i=1, gate_count
      call calcul_Q(Hu,Hd,Hb,E_n(i),n,b,Q_single,zeta_k,zeta0)
      sum_Q = sum_Q + Q_single
   end do
end subroutine Q_SUM

subroutine READ_E(nlines,E_FILE)
   implicit none
   integer :: nlines
   integer :: iline,J
   integer :: iostat_value
   REAL(kind=8),DIMENSION(2000, 8) :: E_FILE
   character(len=256)  :: line
   
   NLINES = 0
   OPEN(unit=180,file='./GATE.txt',status='old',action='read')
   
   iostat_value = 0
   DO WHILE(.TRUE.)
      READ(180,'(A)',iostat=iostat_value) line
      IF (iostat_value /=0) EXIT 
      
      IF (LEN_TRIM(line) == 0) CYCLE
      
      IF (NLINES >= 2000) EXIT
      
      NLINES=NLINES+1
      READ(LINE, *, iostat=iostat_value) (E_FILE(NLINES,J), J=1,8)
      
      IF (iostat_value /= 0) THEN
         NLINES = NLINES - 1
         CYCLE
      END IF
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

   use M_PRECISION
   use M_INTERPOLATION_S  
   use M_PARAMETRE_C 
   use M_ERREUR_T    
   use M_QSING_I     
   use M_ERODEV_I    

   implicit none

   real(DOUBLE), dimension(:,:)  , intent(  out) :: FLULOC
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
   real(DOUBLE), dimension(:)    , intent(in)    :: DZ
   real(DOUBLE), dimension(:,:)  , intent(in)    :: ALGEO
   real(DOUBLE), dimension(:)    , intent(in)    :: COTR
   real(DOUBLE),dimension(:)     , intent(in)    :: Loi_Debit,Loi_Cote
   real(DOUBLE),                   intent(in)    :: DT,COEF
   integer     ,                   intent(in)    :: NMLARG,Nb_Point
   Type (ERREUR_T)               , intent(inout) :: ERREUR

   real(DOUBLE)   :: HDEV,QDEV,ZINT,VG,AT,H_GD
   integer :: ntimestep=0
   INTEGER :: NLINES,ILINE,output_period
   REAL(DOUBLE),DIMENSION(2000,8) :: E_FILE
   REAL(DOUBLE),DIMENSION(7) :: E
   INTEGER :: iostat_value,j
   character(len=256)  :: line
   character(len=256)  :: file_name
   character(len=256)  :: pathNode
   CHARACTER(LEN=256)  :: TITLE
   save ntimestep,E_FILE,NLINES
   
   INTERFACE
     subroutine Q_SUM(Hu, Hd, Hb, E_n, sum_Q)
      implicit none
      REAL(KIND=8) :: Hu, Hd, Hb, E_n(:), sum_Q
     end subroutine Q_SUM
     subroutine READ_E(NLINES,E_FILE)
      integer :: NLINES
      REAL(kind=8),DIMENSION(2000,8) :: E_FILE
     end subroutine READ_E
   END INTERFACE

   Erreur%Numero = 0

   if( ITYP == 3 ) then
      HDEV = ZG - ZDEV
      if( ( HDEV >= EPS3 ) .or. ( debit > 0.d0 ) ) then

         if( ITYP == 3 ) then
            call ERODEV( ZDEV, ZG, HG, QD, IPOS, ALGEO, DZ, DT, NMLARG, ERREUR )
            if (Erreur%Numero /= 0) then
               return
            endif
            if( ZDEV <= COTR(IPOS) ) then
               ZDEV = COTR(IPOS)
               ITYP = 1
               return
            endif
         endif
         
         if (HDEV >= EPS3) then
            VG   = QG / SG
            QDEV = QSING( COEF, ZG, HG, ZD, VG, ZDEV, DZ, ALGEO, IPOS, Epaisseur_Seuil, NMLARG, ERREUR )
         else
            QDEV = 0.D0
         endif

         QDEV = QDEV + DEBIT
         FLULOC(IPOS,1) = QDEV
         FLULOD(IPOS)   = (QDEV**2) / SG + PRG

         if( SD >= .1_DOUBLE ) then
            FLULOG(IPOS) = (QDEV**2) / SD + PRD
         else
            FLULOG(IPOS) = PRD
         endif
      else
         FLULOD(IPOS)   = -( QG**2 ) / SG + PRG
         FLULOG(IPOS)   = PRD
         FLULOC(IPOS,1) = 0._DOUBLE
      endif

   ELSEIF (ITYP == 4) THEN
      
      HDEV = ZG - ZDEV
      H_GD = ZG - ZD
      E = 0.D0
      
      IF(ntimestep == 0) THEN
         NLINES = 0
         CALL READ_E(NLINES,E_FILE)
         OPEN(unit=181,file='fort.181',status='replace',action='write')
      END IF
      
      ntimestep = ntimestep +1
      AT = DT*DBLE(ntimestep)

      IF (NLINES >= 1) E = E_FILE(1,2:8)
      
      DO ILINE=1, NLINES-1
         IF ((AT>=E_FILE(ILINE,1)).AND.(AT<E_FILE(ILINE+1,1))) THEN
            E = E_FILE(ILINE,2:8)
            EXIT
         END IF
      END DO

      IF ((NLINES >= 1) .AND. (AT >= E_FILE(NLINES,1))) THEN
         E = E_FILE(NLINES,2:8)
      END IF

      IF ((HDEV >= EPS3).OR.(DEBIT > 0.D0)) THEN
         if (HDEV >= EPS3) then
            CALL Q_SUM(ZG,ZD,ZDEV,E,QDEV)
         else
            QDEV = 0.D0
         endif
         
         QDEV = QDEV + DEBIT

         QDEV = MAX(QDEV, 0.D0)
         IF (QG >= 0.D0) THEN
            QDEV = MIN(QDEV, QG)
         END IF

         FLULOC(IPOS,1) = QDEV
         FLULOD(IPOS) = (QDEV**2) / SG + PRG
         
         if( SD >= .1_DOUBLE ) then
            FLULOG(IPOS) = (QDEV**2) / SD + PRD
         else
            FLULOG(IPOS) = PRD
         endif

      ELSE
         QDEV = 0.D0
         FLULOD(IPOS)   = -( QG**2 ) / SG + PRG
         FLULOG(IPOS)   = PRD
         FLULOC(IPOS,1) = 0._DOUBLE
         FLULOC(IPOS,2) = 0._DOUBLE
      ENDIF

      output_period = 1
      IF (DT > 0.D0) output_period = MAX(1, NINT(3600.D0 / DT))
      IF (MOD(ntimestep, output_period) == 0) THEN
         WRITE(181,*) AT,FLULOC(IPOS,1)
      ENDIF
      
   ELSE
      If( ITYP == 6 ) ZINT = ZG
      if( ITYP == 7 ) ZINT = ZD
      call INTERPOLATION_S ( QDEV, ZINT, 1, Loi_Cote, Loi_Debit, nb_point, Erreur )
      
      QDEV           = QDEV + DEBIT
      FLULOC(IPOS,1) = QDEV
      FLULOD(IPOS)   = (QDEV**2) / SG + PRG
      
      if( SD >= .1_DOUBLE ) then
         FLULOG(IPOS) = (QDEV**2) / SD + PRD
      else
         FLULOG(IPOS) = PRD
      endif

   endif
   300 FORMAT(6F8.2)

  return

end subroutine FLUDEV
