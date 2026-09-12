!                   ******************
                    SUBROUTINE ICE_BUO
!                   ******************
!
     &(FC,FN,WCHU,MESH3D,DT,VOLU,NPOIN2,NPOIN3,NPLAN,T1)
!
!***********************************************************************
! TELEMAC3D   V8P4                                    2022
!***********************************************************************
!
!brief    Advection of frasil ice with buoyancy velocity
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| DT             |-->| TIME STEP
!| FC             |<->| VARIABLE AFTER CONVECTION
!| FN             |<->| VARIABLE F AFTER ADVECTION WITH VELOCITY BUT WC
!| MESH3D         |<->| 3D MESH
!| NPLAN          |-->| NUMBER OF PLANES IN THE 2D MESH
!| NPOIN2         |-->| NUMBER OF POINTS IN THE 2D MESH
!| NPOIN3         |-->| NUMBER OF POINTS IN THE 3D MESH
!| T1             |<->| WORK ARRAY IN BIEF_OBJ
!| VOLU           |-->| VOLUME AROUND POINTS AT TIME N+1
!| WCHU           |-->| VELOCITY (POSITIVE IF SEDIMENT SETTLING VELOCITY)
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE BIEF
      USE DECLARATIONS_TELEMAC
!
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER         , INTENT(IN)    :: NPOIN2,NPOIN3,NPLAN
      DOUBLE PRECISION, INTENT(IN)    :: DT
      TYPE(BIEF_OBJ)  , INTENT(IN)    :: FN,WCHU,VOLU
      TYPE(BIEF_OBJ)  , INTENT(INOUT) :: FC,T1
      TYPE(BIEF_MESH) , INTENT(INOUT) :: MESH3D
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER I2D,IPLAN,I3D,IINF,ISUP
      DOUBLE PRECISION ZDEP,ZARR,ZTOP,ZINF,ZSUP,ALFA
!
!-----------------------------------------------------------------------
!
!     INITIALISING FC (IF WILL BE THE FINAL MASS CARRIED BY POINTS)
!
      CALL OS('X=0     ',X=FC)
!
!     SEDIMENT ON TOP PLANE WILL NOT MOVE
!
      DO I2D=NPOIN3-NPOIN2+1,NPOIN3
        FC%R(I2D)=FC%R(I2D)+FN%R(I2D)*VOLU%R(I2D)
      ENDDO
!
!-----------------------------------------------------------------------
!
!     LOOP ON ALL THE VERTICALS, MASSES SHIFTED DOWN FOR EVERY POINT
!
      DO I2D=1,NPOIN2
!       TOP TREATED ABOVE, SO LOOP END AT NPLAN - 1
        DO IPLAN=1, NPLAN-1
!         3D POINT NUMBER
          I3D=I2D+(IPLAN-1)*NPOIN2
!         TOP
          ZTOP=MESH3D%Z%R(NPOIN3-NPOIN2+I2D)
!         DEPARTURE POINT
          ZDEP=MESH3D%Z%R(I3D)
!         ARRIVAL POINT (WCHU>0)
          ZARR=MIN(ZDEP+WCHU%R(I3D)*DT,ZTOP)
!         LOCATING THE ARRIVAL POINT
          IINF=IPLAN
          ISUP=IPLAN+1
1         CONTINUE
          ZINF=MESH3D%Z%R(I2D+(IINF-1)*NPOIN2)
          ZSUP=MESH3D%Z%R(I2D+(ISUP-1)*NPOIN2)
          IF(ZARR.GT.ZSUP) THEN
            IINF=IINF+1
            ISUP=ISUP+1
            GO TO 1
          ENDIF
!         PROJECTION OF THE ORIGINAL MASS ON THE TWO POINTS
          ALFA=(ZARR-ZINF)/MAX(ZSUP-ZINF,1.D-7)
!         MASS ON IINF
          FC%R(I2D+(IINF-1)*NPOIN2)
     &   =FC%R(I2D+(IINF-1)*NPOIN2)+(1.D0-ALFA)*FN%R(I3D)*VOLU%R(I3D)
!         MASS ON ISUP
          FC%R(I2D+(ISUP-1)*NPOIN2)
     &   =FC%R(I2D+(ISUP-1)*NPOIN2)+      ALFA *FN%R(I3D)*VOLU%R(I3D)
        ENDDO
      ENDDO
!
!     INVERSION OF THE MASS MATRIX (HERE LUMPED) TO GO BACK FROM MASSES
!     TO CONCENTRATIONS
!
      CALL OS('X=Y     ',X=T1,Y=VOLU)
!
!     ASSEMBLING IN PARALLEL
!
      IF(NCSIZE.GT.1) THEN
        CALL PARCOM(FC,2,MESH3D)
        CALL PARCOM(T1,2,MESH3D)
      ENDIF
!
!     INVERTING THE (LUMPED) MASS MATRIX (I.E. VOLU)
!
      DO I3D=1,NPOIN3
        FC%R(I3D)=FC%R(I3D)/MAX(T1%R(I3D),1.D-6)
      ENDDO
!
!-----------------------------------------------------------------------
!
      RETURN
      END

