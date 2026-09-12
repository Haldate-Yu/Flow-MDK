!                   ****************************
                    SUBROUTINE BEDLOAD_AVALANCHE
!                   ****************************
!
     & (QSC,RATIO_SAND,XMVS,DZFDX,DZFDY,CALFA,SALFA)
!
!***********************************************************************
! GAIA
!***********************************************************************
!
!>@brief Computes the avalanching effect after APSLEY AND STANSBY JHE
!! 2008
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in,out] QSC         Bed load transport rate [kg*(m-1*s-1)]
!>@param[in]     RATIO_SAND  Mass fraction of sand
!>@param[in]     XMVS        Sediment density (kg/m3)
!>@param[in,out] DZFDX       Bottom slope in the x-direction
!>@param[in,out] DZFDY       Bottom slope in the y-direction
!>@param[in,out] CALFA       Cosinus of the angle between transport rate
!!                           and x-axis
!>@param[in,out] SALFA       Sinus of the angle between transport rate
!!                           and x-axis
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE BIEF
      USE DECLARATIONS_GAIA, ONLY : DT,PHISED,NPOIN,MESH,MSK,MASKEL,
     & IELMT,ZF,UNSV2D,PI,S,XKV0,LT,NCSIZE,V2DPAR
      USE DECLARATIONS_SPECIAL
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      IMPLICIT NONE
      TYPE(BIEF_OBJ),   INTENT(INOUT) :: QSC
      DOUBLE PRECISION, INTENT (IN)   :: RATIO_SAND(NPOIN),XMVS
      TYPE(BIEF_OBJ),   INTENT(INOUT) :: DZFDX, DZFDY ! -- T1,T2
      TYPE(BIEF_OBJ),   INTENT(INOUT) :: CALFA, SALFA
!
!!-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER I
      DOUBLE PRECISION :: AVAL
      DOUBLE PRECISION :: TANBETA,COSBETA,LCELL2,POROS,TANPHI
      DOUBLE PRECISION :: QSCX,QSCY,QSCAX,QSCAY,SBETA,CBETA,HYP

!======================================================================!
!======================================================================!
!                               PROGRAM                                !
!======================================================================!
!======================================================================!

!     COMPUTES THE SLOPE  : D(ZF)/DX ET D(ZF)/DY (AT THE NODES)
!
      CALL VECTOR(DZFDX, '=', 'GRADF          X',IELMT,1.D0,ZF,S,S,
     &            S,S,S,MESH,MSK,MASKEL)
      CALL VECTOR(DZFDY, '=', 'GRADF          Y',IELMT,1.D0,ZF,S,S,
     &            S,S,S,MESH,MSK,MASKEL)
!
      IF(NCSIZE.GT.1) THEN
        CALL PARCOM(DZFDX,2,MESH)
        CALL PARCOM(DZFDY,2,MESH)
      ENDIF
!
      CALL OS('X=XY    ',X=DZFDX,Y=UNSV2D)
      CALL OS('X=XY    ',X=DZFDY,Y=UNSV2D)


!      BEGINNING AVALANCHING
! Q_AVALANCHE = (1-P) (0.5*L**2*(TAN(BETA)-TAN(PHISED))) / (COS(BETA) *
! DT)
! P : POROSITY
! L : MAX. HOR. DIMENSION OF THE CELL
! BETA : SLOPE ANGLE
! PHISED : ANGLE OF REPOSE
! DT : TIME STEP
! TANPHI =TAN(PHISED*PI/180.D0)
! QSCX/QSCY: BEDLOAD CONCERNING TRANSPORT FORMULA
! QSCAX/QSCAY:BEDLOAD CONCERNING AVALANCHING
! CBETA/SBETA: COS/SIN OF ANGLE IN DIRECTION OF HIGHEST SLOPE
!
      TANPHI = TAN(PHISED*PI/180.D0)
! POROSITY IS TAKEN FROM THE ACTIVE LAYER
      DO I=1,NPOIN
! LENGTH IS ASSUMED THE SQUARE ROOT OF THE ELEMENT AREA
        LCELL2 = V2DPAR%R(I)
!
        TANBETA = SQRT(DZFDX%R(I)**2+DZFDY%R(I)**2)
        COSBETA = 1.D0/SQRT(1.D0+DZFDX%R(I)**2+ DZFDY%R(I)**2)

        IF(TANBETA.GT.TANPHI) THEN
          AVAL = (1-XKV0(1))*0.5D0*LCELL2
     &     *(TANBETA-TANPHI)/DT /COSBETA
        ELSE
          AVAL = 0.D0
        ENDIF
        AVAL = AVAL*RATIO_SAND(I)

! x,y COMPONENTS OF THE BEDLOAD CONCERNING TRANSPORT FORMULA
        QSCX = QSC%R(I)*CALFA%R(I)
        QSCY = QSC%R(I)*SALFA%R(I)
! DIRECTION OF MAXIMUM SLOPE
        HYP = MAX(SQRT(DZFDX%R(I)**2+DZFDY%R(I)**2),1.D-10)
        IF(HYP.GT.1.D-12) THEN
          SBETA = -DZFDY%R(I)/HYP
          CBETA = -DZFDX%R(I)/HYP
        ELSE
          SBETA = 0.D0
          CBETA = 1.D0
        ENDIF
! AVALANCHING IN X/Y DIRECTION
        QSCAX = AVAL*XMVS*CBETA
        QSCAY = AVAL*XMVS*SBETA
!
! COMBINED BEDLOAD FROM TRANSPORT AND AVALANCHING
        QSC%R(I) = SQRT((QSCX+QSCAX)**2+(QSCY+QSCAY)**2)
!
! CALCULATION OF DIRECTION OF COMBINED BEDLOAD
        IF(QSC%R(I).GT.1.D-12) THEN
          SALFA%R(I)=(QSCY+QSCAY)/QSC%R(I)
          CALFA%R(I)=(QSCX+QSCAX)/QSC%R(I)
        ELSE
          SALFA%R(I)=0.D0
          CALFA%R(I)=1.D0
        ENDIF
      ENDDO
!
!-----------------------------------------------------------------------
!
      RETURN
      END SUBROUTINE
