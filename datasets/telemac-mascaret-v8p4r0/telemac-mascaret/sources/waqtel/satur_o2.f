!                   *******************
                    SUBROUTINE SATUR_O2
!                   *******************
!
     &(SATO2,FORMCS,WATTEMP,WATSAL,EPS)
!
!***********************************************************************
! WAQTEL   V8P5
!***********************************************************************
!
!brief    COMPUTES THE CONCENTRATION OF O2 SATURATION OF WATER
!
!
!history  R. ATA (LNHE)
!+        02/09/2015
!+        V7P1
!+    First version.
!
!history  A. LEVASSEUR (ARTELIA)
!+        18/08/2023
!+        V8P5
!+    Add Cs as a function of temperature and salinity
!+    3rd version
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| EPS            |-->| TO AVOID DIVISION BY 0
!| FORMCS         |-->| WHICH FORMULAE FOR SATUR_O2
!| SATO2          |<--| CONCENTRATION OF O2 SATURATION OF WATER
!| WATTEMP        |-->| TEMPERATURE OF WATER
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE BIEF
      USE DECLARATIONS_SPECIAL
      USE INTERFACE_WAQTEL, EX_SATUR_O2 => SATUR_O2
!
      IMPLICIT NONE
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER         , INTENT(IN)    :: FORMCS
      DOUBLE PRECISION, INTENT(IN)    :: WATTEMP,WATSAL,EPS
      DOUBLE PRECISION, INTENT(INOUT) :: SATO2
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      DOUBLE PRECISION TEMP_BK,SAL_BK
!
      INTRINSIC ABS
!
!-----------------------------------------------------------------------
!
      IF(FORMCS.NE.0) THEN
        IF(FORMCS.EQ.1) THEN
          SATO2 = 14.652D0 - 0.41022D0  * WATTEMP
     &                     + 0.007991D0 * WATTEMP**2
     &                     - 7.7774D-5  * WATTEMP**3
        ELSEIF(FORMCS.EQ.2)THEN
          IF(ABS(31.6D0+WATTEMP).GT.EPS)THEN
            SATO2 = 468.D0/(31.6D0+WATTEMP)
          ELSE
            SATO2 = 468.D0/EPS
          ENDIF
        ELSEIF(FORMCS.EQ.3) THEN
! SATO2 AS A FUNCTION OF TEMPERATURE AND SALINITY
!
! REF: BENSON AND KRAUSE, 1984
! THE CONCENTRATION AND ISOTOPIC FRACTIONATION OF DISSOLVED OXYGEN
! IN FRESHWATER AND SEA WATER IN EQUILIBRIUM WITH THE ATMOSPHERE
! LIMNOLOGY AND OCEANOGRAPHY, 29, 620-632
!
! VALIDITY: TEMPERATURE=0-40 DEGREE C, SALINITY=0-40G/L
!
          TEMP_BK=MAX(WATTEMP,0.D0)
          TEMP_BK=MIN(TEMP_BK,40.D0)
          SAL_BK=MAX(WATSAL,0.D0)
          SAL_BK=MIN(SAL_BK,40.D0)
!         CONVERSION OF TEMP_BK TO KELVIN
          TEMP_BK=TEMP_BK+273.15D0
!         CS IN MICROMOL/L
          SATO2 = -135.90205D0 + 1.575701D5/TEMP_BK
     &          - 6.642308D7/TEMP_BK**2
     &          + 1.2438D10/TEMP_BK**3
     &          - 8.621949D11/TEMP_BK**4
     &          - SAL_BK*(  1.7674D-2 - 10.754D0/TEMP_BK
     &                    + 2140.7D0/TEMP_BK**2 )
          SATO2=EXP(SATO2)
!         CONVERSION OF CS IN MG/L
          SATO2=SATO2*2.23916D-2*1.429D0
        ELSE
          WRITE(LU,101) FORMCS
          CALL PLANTE(1)
          STOP
        ENDIF
      ENDIF
!
!     ERROR MESSAGES
!
101   FORMAT(1X,'CS FORMULA :',I3,/,1X, 'NOT AVAILABLE')
!
!-----------------------------------------------------------------------
!
      RETURN
      END
