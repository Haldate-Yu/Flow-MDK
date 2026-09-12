!               *********************************
                SUBROUTINE SUSPENSION_COMPUTE_CAE
!               *********************************
!
     &(TAUP,HN,DCLA,NPOIN,CHARR,XMVE,XMVS,VCE,GRAV,
     & ZERO,ZREF,AC,CSTAEQ,QSC,ICQ,U2D,V2D,CSRATIO,DEBUG,RATIO_TOCE)
!
!***********************************************************************
! GAIA
!***********************************************************************
!
!>@brief Computes equilibrium concentration
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in]     AC         Critical shields parameter
!>@param[in]     ACLADM     Mean diameter of active layer
!>@param[in]     CHARR      Logical, if bedload or not
!>@param[in,out] CSTAEQ     Equilibrium concentration
!>@param[in]     CSRATIO    Equilibrium concentration for soulby-van rijn eq.
!>@param[in]     DEBUG      Flag for debugging
!>@param[in]     GRAV       Acceleration of gravity
!>@param[in]     HN         Water depth
!>@param[in]     ICQ        Reference concentration formula
!>@param[in]     NPOIN      Number of points
!>@param[in]     QSC        Bed load transport rate
!>@param[in,out] RATIO_TOCE Ratio between critical shear stress of pure
!!                          sediment and mixed sediment in the same layer
!>@param[in]     TAUP       Skin friction
!>@param[in]     VCE        Water viscosity
!>@param[in]     XMVE       Fluid density
!>@param[in]     XMVS       Sediment density
!>@param[in]     ZERO       Zero
!>@param[in]     ZREF       Reference elevation
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE INTERFACE_GAIA, EX_SUSPENSION_COMPUTE_CAE =>
     &       SUSPENSION_COMPUTE_CAE
      USE BIEF
      USE DECLARATIONS_GAIA, ONLY : NOMBLAY
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
!     GLOBAL VARIABLES
!     -------------------
      TYPE (BIEF_OBJ),  INTENT(IN)    :: TAUP,HN,ZREF,QSC
      TYPE (BIEF_OBJ),  INTENT(IN)    :: U2D,V2D,CSRATIO
      INTEGER,          INTENT(IN)    :: NPOIN,DEBUG,ICQ
      LOGICAL,          INTENT(IN)    :: CHARR
      DOUBLE PRECISION, INTENT(IN)    :: XMVE,XMVS,GRAV,VCE
      DOUBLE PRECISION, INTENT(IN)    :: ZERO,DCLA
      DOUBLE PRECISION, INTENT(IN)    :: AC
      TYPE (BIEF_OBJ),  INTENT(INOUT) :: CSTAEQ,RATIO_TOCE
!======================================================================!
!======================================================================!
!                               PROGRAM                                !
!======================================================================!
!======================================================================!
!
!  COMPUTES THE NEAR BED EQUILIBRIUM CONCENTRATION --> CSTAEQ
!
      IF(ICQ.EQ.1) THEN
!
        IF(DEBUG > 0) WRITE(LU,*) 'SUSPENSION_FREDSOE'
        CALL SUSPENSION_FREDSOE(DCLA,TAUP,NPOIN,
     &                          GRAV,XMVE,XMVS,AC,CSTAEQ,RATIO_TOCE)
        IF(DEBUG > 0) WRITE(LU,*) 'END SUSPENSION_FREDSOE'
!
      ELSEIF(ICQ.EQ.2) THEN
        IF(DEBUG > 0) WRITE(LU,*) 'SUSPENSION_BIJKER'
            IF(NOMBLAY.GE.1)THEN
!>@to do
            WRITE(LU,*)'QSC IS COMING FROM FIRST LAYER OF BEDLOAD PART
     &                    IN THE CASE OF MULTILAYER OR ACTIVE LAYER,
     &                    QSC HAVE BEEN TO BE
     &                    COMPUTED FOR OTHERS LAYER IF THERE IS EROSION
     &                    OF THE FIRST LAYER IN BED1_SUSPENSION_ERODE'
              CALL PLANTE(1)
              STOP
            ENDIF
        CALL SUSPENSION_BIJKER(TAUP,NPOIN,CHARR,QSC,ZREF,
     &                         ZERO,CSTAEQ,XMVE,RATIO_TOCE)
        IF(DEBUG > 0) WRITE(LU,*) 'END SUSPENSION_BIJKER'
!
      ELSEIF(ICQ.EQ.3) THEN
!
        IF(DEBUG > 0) WRITE(LU,*) 'SUSPENSION_VANRIJN'
        CALL SUSPENSION_VANRIJN(DCLA,TAUP,NPOIN,GRAV,XMVE,XMVS,
     &                          VCE,ZERO,AC,CSTAEQ,ZREF,RATIO_TOCE)
        IF(DEBUG > 0) WRITE(LU,*) 'END SUSPENSION_VANRIJN'

      ELSEIF(ICQ.EQ.4) THEN
        IF(DEBUG > 0) WRITE(LU,*) 'SUSPENSION_SANDFLOW'
        CALL SUSPENSION_SANDFLOW(DCLA,NPOIN,GRAV,XMVE,XMVS,
     &             ZERO,CSTAEQ,HN,U2D,V2D,CSRATIO,RATIO_TOCE)
        IF(DEBUG > 0) WRITE(LU,*) 'END SUSPENSION_SANDFLOW'
!
      ELSEIF(ICQ.EQ.0) THEN
        IF(DEBUG > 0) WRITE(LU,*) 'SUSPENSION_CAE_USER_GAIA'
        CALL USER_SUSPENSION_CAE(DCLA,NPOIN,XMVS,CSTAEQ)
        IF(DEBUG > 0) WRITE(LU,*) 'END SUSPENSION_CAE_USER_GAIA'
!
      ENDIF
!
!======================================================================!
!======================================================================!
!
      RETURN
      END
!
!#######################################################################
!
