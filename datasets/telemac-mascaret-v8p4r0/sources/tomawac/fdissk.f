!                       *****************
                        SUBROUTINE FDISSK
!                       *****************
     &  (FDK,  NPOIN2, NDIRE,FS,ZTEL,NZ,HSMJT,FZNORM,NF)
! WAVE-ENHANCED MIXING
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| FS             |-->| VARIANCE DENSITY DIRECTIONAL SPECTRUM
!| FDK            |<--|
!| FZNORM               WORK ARRAY
!| HSMJT                WORK ARRAY
!| NF             |-->| NUMBER OF FREQUENCIES
!| NDIRE          |-->| NUMBER OF DIRECTIONS
!| NPOIN2         |-->| NUMBER OF POINTS IN 2D MESH
!| NZ             |-->| NUMBER OF PLAN IN TELEMAC3D
!| XK             |-->| DISCRETIZED WAVE NUMBER
!| ZTEL           |-->| ELEVATION
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      USE BIEF
      USE DECLARATIONS_TOMAWAC, ONLY : DEUPI,GRAVIT,DFREQ,DEPTH,BETABR,
     &                                 TRA41, STRA42
      USE INTERFACE_TOMAWAC, EX_FDISSK => FDISSK

      IMPLICIT NONE

!.....VARIABLES IN ARGUMENT
!     """"""""""""""""""""
      INTEGER, INTENT(IN)  :: NZ
      INTEGER, INTENT(IN) :: NPOIN2, NDIRE, NF
      DOUBLE PRECISION, INTENT(IN) :: FS(NPOIN2,NDIRE,NF)
      DOUBLE PRECISION, INTENT(IN) :: HSMJT(NPOIN2)
      DOUBLE PRECISION, INTENT(INOUT) :: FDK(NPOIN2,NZ)
      DOUBLE PRECISION, INTENT(IN) :: ZTEL(NPOIN2,NZ)
      DOUBLE PRECISION, INTENT(INOUT) :: FZNORM(NPOIN2)
!     """""""""""""""""
!.....LOCAL VARIABLES
!     """""""""""""""""
      INTEGER  JP    , JF    , IP,  INZ
      DOUBLE PRECISION DTETAR, AUX1,AUXZ
      DOUBLE PRECISION, POINTER:: TMPARR1(:,:), TMPARR2(:)

      DOUBLE PRECISION :: TMP

      TMPARR1(1:NPOIN2,1:NZ)=>STRA42%R(1:NPOIN2*NZ)
      TMPARR2=>TRA41
!
      IF (NDIRE.EQ.0) THEN
        WRITE(LU,*) 'FDISSK : NDIRE DIR eq 0 '
        CALL PLANTE(1)
      ENDIF
      DTETAR=DEUPI/DBLE(NDIRE)

      DO IP=1,NPOIN2
        FZNORM(IP) = 0.D0
        TMPARR2(IP) = 0.D0
      ENDDO
      DO INZ=1,NZ
        DO IP=1,NPOIN2
          FDK(IP,INZ) = 0.D0
        ENDDO
      ENDDO

      DO INZ=1,NZ
        DO IP=1,NPOIN2
!TYPE II
          IF (HSMJT(IP) .NE.0) THEN
            TMPARR1(IP,INZ) = (1.D0-TANH(SQRT(2.D0) /
     &        (1.2D0*HSMJT(IP))*((DEPTH(IP))-ZTEL(IP,INZ)))**2)
            FZNORM(IP)=FZNORM(IP)+ TMPARR1(IP,INZ) *
     &        (ZTEL(IP,NZ)-ZTEL(IP,1))
          ENDIF
!TYPE I
!           FZNORM(IP,NZ)=FZNORM(IP,NZ)+(COSH(SQRT(2.D0)
!      & /(1.2D0*HSMJT(IP))*(ZTEL(IP,INZ)-ZFJ(IP))))*AUXZ

        ENDDO
      ENDDO
!
      DO JF=1,NF
        AUX1 = DFREQ(JF)*DTETAR*GRAVIT**(1.D0/3.D0)
        DO JP=1,NDIRE
          DO IP=1,NPOIN2
            TMPARR2(IP) = TMPARR2(IP) + AUX1 *
     &        (FS(IP,JP,JF)*ABS(BETABR(IP)))**(1.D0/3.D0)
          ENDDO
        ENDDO
      ENDDO

      DO INZ=1,NZ
        DO IP=1,NPOIN2
          IF (FZNORM(IP).NE.0) THEN
!   type II shape
            FDK(IP,INZ) = FDK(IP,INZ)+(0.03D0 * 
     &        TMPARR1(IP,INZ)/FZNORM(IP) *
     &        DEPTH(IP)*HSMJT(IP)/SQRT(2.D0)*TMPARR2(IP))
          ENDIF
        ENDDO
      ENDDO


! !
! ! type I shape

!
!             FDK(IP,INZ)=FDK(IP,INZ)+(0.03D0
!      & *(COSH(SQRT(2.D0)/(1.2D0*HSMJT(IP))
!      & *(ZTEL(IP,INZ)-ZFJ(IP))))/(FZNORM(IP,NZ))*DEPTH1(IP)
!      & *HSMJT(IP)/SQRT(2.D0)*(FS(IP,JP,JF)*ABS(BETA(IP))
!      & *GRAVIT)**(1./3.))*AUX1

      RETURN
      END
