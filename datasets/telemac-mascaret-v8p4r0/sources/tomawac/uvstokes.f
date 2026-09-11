!#######################################################################
                        SUBROUTINE UVSTOKES
     &  (UST, VST, WST, FS, NPOIN2, XK, ZFJ, NDIRE, ZTEL, NZ, NF)
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!  calculation of the three components of the stokes drift
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| FS             |-->| VARIANCE DENSITY DIRECTIONAL SPECTRUM
!| NF             |-->| NUMBER OF FREQUENCIES
!| NDIRE          |-->| NUMBER OF DIRECTIONS
!| NPOIN2         |-->| NUMBER OF POINTS IN 2D MESH
!| NZ             |-->| NUMBER OF PLAN IN TELEMAC3D
!| XK             |-->| DISCRETIZED WAVE NUMBER
!| UST            |<--| STOKES COMPONENT ALONG X
!| VST            |<--| STOKES COMPONENT ALONG Y
!| WST            |<--| STOKES COMPONENT ALONG Z
!| ZFJ            |-->| BOTTOM ELEVATION
!| ZTEL           |-->| ELEVATION IN TELEMAC3D
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      USE BIEF
      USE DECLARATIONS_TOMAWAC, ONLY : FREQ,COSTET,DFREQ,DZX,DZY,SINTET,
     &                                 DEPTH, DEUPI,STRA42
      USE INTERFACE_TOMAWAC, EX_UVSTOKES => UVSTOKES
      
!NDIRE - number of direction discretization      
      IMPLICIT NONE
      
!.....VARIABLES IN ARGUMENT
!     """"""""""""""""""""
      INTEGER, INTENT(IN)  :: NZ,NF
      INTEGER, INTENT(IN) :: NPOIN2, NDIRE
      DOUBLE PRECISION, INTENT(IN) :: FS(NPOIN2,NDIRE,NF)
      DOUBLE PRECISION, INTENT(IN) :: ZFJ(NPOIN2)
      DOUBLE PRECISION, INTENT(IN) :: XK(NPOIN2,NF)
      DOUBLE PRECISION, INTENT(INOUT) :: UST(NPOIN2,NZ)
      DOUBLE PRECISION, INTENT(INOUT) :: VST(NPOIN2,NZ)
      DOUBLE PRECISION, INTENT(INOUT) :: WST(NPOIN2)
      DOUBLE PRECISION, INTENT(IN) :: ZTEL(NPOIN2,NZ)
!.....LOCAL VARIABLES
!     """""""""""""""""
      INTEGER  JP    , JF    , IP, INZ
      DOUBLE PRECISION SIGMA, DTETAR, AUX1, TMP

      DOUBLE PRECISION, POINTER :: TMP_ARR1(:,:),
     &   TMP_ARR2(:,:,:)

!----------------------------------------------------------------------
      TMP_ARR1(1:NPOIN2,1:NF)=>STRA42%R(1:NPOIN2*NF)
      TMP_ARR2(1:NPOIN2,1:NZ,1:NF)=>
     &          STRA42%R(NPOIN2*NF+1:NPOIN2*(NZ+1)*NF)
!
      DTETAR=DEUPI/DBLE(NDIRE)

!begin mjt- initialize variables
      DO INZ=1,NZ
        DO IP=1,NPOIN2
          UST(IP,INZ) = 0.D0
          VST(IP,INZ) = 0.D0
        ENDDO
      ENDDO

!store local profile (in principle only needed every coupling step)
      DO JF=1,NF
        SIGMA=DEUPI*FREQ(JF)
        AUX1=DFREQ(JF)*DTETAR
        DO IP=1,NPOIN2
          TMP_ARR1(IP,JF) = AUX1*SIGMA*XK(IP,JF)
     &       /SINH(XK(IP,JF)*DEPTH(IP))**2
        ENDDO
      ENDDO

!store profile  (in principle only needed every coupling step)
      DO JF=1,NF
        DO INZ=1,NZ
          DO IP=1,NPOIN2
            TMP_ARR2(IP,INZ,JF) =
     &         COSH(2.D0*XK(IP,JF)*(ZTEL(IP,INZ)-ZFJ(IP)))
          ENDDO
        ENDDO
      ENDDO

!apply
      DO JF=1,NF
        DO JP=1,NDIRE
          DO INZ=1, NZ
            DO IP=1,NPOIN2
                TMP = TMP_ARR2(IP,INZ,JF)*
     &              TMP_ARR1(IP,JF)*FS(IP,JP,JF)
                UST(IP,INZ)=UST(IP,INZ)+SINTET(JP)*TMP
                VST(IP,INZ)=VST(IP,INZ)+COSTET(JP)*TMP
            ENDDO
          ENDDO
        ENDDO
      ENDDO

      DO IP=1,NPOIN2
        WST(IP)=-UST(IP,1)*DZX(IP)-VST(IP,1)*DZY(IP)
      ENDDO
      
      RETURN
      END
