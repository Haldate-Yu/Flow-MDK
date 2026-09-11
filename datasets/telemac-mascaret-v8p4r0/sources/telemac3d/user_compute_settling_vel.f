!                 ************************************
                  SUBROUTINE USER_COMPUTE_SETTLING_VEL
!                 ************************************
!
     &(WCHU,U,V,TRAV1,TRAV2,TRAV3,S,MESH3D, IELM3,
     & NPOIN2,NPOIN3,NPLAN,MSK,MASKEL,UETCAR,TA,HN)
!
!***********************************************************************
! TELEMAC3D   V8P5
!***********************************************************************
!
!brief    USER SUBROUTINE TO CUSTOMIZE THE COMPUTATION OF SETTLING
!+        VELOCITIES.
!+        CREATED FROM ALREADY EXISTING SUBROUTINE: COMPUTE_SETTLING_VEL
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| HN             |-->| WATER DEPTH AT TIME N
!| IELM3          |-->| DISCRETISATION TYPE FOR 3D
!| MASKEL         |-->| MASKING OF ELEMENTS
!|                |   | =1. : NORMAL   =0. : MASKED ELEMENT
!| MESH3D         |<->| 3D MESH
!| MSK            |-->| IF YES, THERE IS MASKED ELEMENTS.
!| NPOIN2         |-->| NUMBER OF POINTS IN 2D
!| NPOIN3         |-->| NUMBER OF POINTS IN 3D
!| NPLAN          |-->| NUMBER OF PLANES IN THE 3D MESH OF PRISMS
!| S              |-->| VOID STRUCTURE
!| TA             |-->| TRACER CONCENTRATION (LAST ONE, NTRAC, IS SED)
!| TOB            |-->| BED SHEAR STRESS (INCLUDES TURBULENCE DAMPING)
!| TRAV1          |<->| WORK ARRAY
!| TRAV2          |<->| WORK ARRAY
!| TRAV3          |<->| WORK ARRAY
!| U,V            |-->| VELOCITY COMPONENTS
!| UETCAR         |-->| SQUARE OF THE FRICTION VELOCITY
!| WCHU           |<->| SEDIMENT SETTLING VELOCITY (M/S)
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE BIEF
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_TELEMAC3D, ONLY: IND_SED
      USE DECLARATIONS_GAIA, ONLY:NSUSP_TEL,NUM_ISUSP_ICLA,
     &     FLOC,FLOC_TYPE,HINDER,HIND_TYPE,CGEL,CINI,TURBA,TURBB,
     &     XWC0,TYPE_SED
      USE INTERFACE_TELEMAC3D, EX_USER_COMPUTE_SETTLING_VEL =>
     &                         USER_COMPUTE_SETTLING_VEL
      IMPLICIT NONE
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      TYPE(BIEF_MESH),INTENT(INOUT) :: MESH3D
      TYPE(BIEF_OBJ), INTENT(INOUT) :: WCHU,TRAV1,TRAV2,TRAV3
      TYPE(BIEF_OBJ), INTENT(IN)    :: MASKEL,S,HN,U,V
      TYPE(BIEF_OBJ), INTENT(IN)    :: TA,UETCAR
      LOGICAL, INTENT(IN)           :: MSK
      INTEGER, INTENT(IN)           :: NPOIN2,NPOIN3,NPLAN,IELM3
!
      INTEGER ITRAC,ISUSP,IPLAN,IPOIN,IPOIN3
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
!     EXAMPLE OF FLOCCULATION FORMULA - IT USES THE CONCENTRATION FOR ALL
!     SEDIMENT CLASSES AND APPLIES THE SAME SETTLING VELOCITY TO ALL
!     CLASSES CALCULATED USING THE SOULSBY FLOCCULATION MODEL
!
!     CALCULATE THE TOTAL CONCENTRATION
!      CALL OS('X=0     ',TRAV1)
!      DO ITRAC=IND_SED,IND_SED+NSUSP_TEL-1
!        ISUSP=ITRAC-IND_SED+1
!        IF(TYPE_SED(NUM_ISUSP_ICLA(ISUSP)).EQ.'CO') THEN
!          CALL OS('X=X+Y   ',X=TRAV1,Y=TA%ADR(ITRAC)%P)
!        ENDIF
!      ENDDO
!
!     USE THE TOTAL CONCENTRATION TO CALCULATE SETTLING VELOCITY
!
!      IF(HINDER) THEN
!        CALL OS('X=-(Y,C)',X=TRAV1,Y=TRAV1,C=CINI)
!      ENDIF
!
!!     CALCULATE SETTLING USING SOULSBY FORMULA - USING TOTAL CONC
!!      CALL SOULSBYFLOC3D(TRAV2,TRAV1%R,MESH3D,
!!     &     NPOIN2,NPOIN3,NPLAN,HN,UETCAR%R)
!!
!!     APPLY THE SETTLING VELOCITY TO ALL COHESIVE FRACTIONS
!!      DO ITRAC=IND_SED,IND_SED+NSUSP_TEL-1
!!         ISUSP=ITRAC-IND_SED+1
!!          IF(TYPE_SED(NUM_ISUSP_ICLA(ISUSP)).EQ.'CO') THEN
!!             CALL OS('X=Y     ',X=WCHU%ADR(ITRAC)%P,Y=TRAV2)
!!          ENDIF
!!       ENDDO
!
!      DO ITRAC=IND_SED,IND_SED+NSUSP_TEL-1
!        ISUSP=ITRAC-IND_SED+1
!          IF(TYPE_SED(NUM_ISUSP_ICLA(ISUSP)).EQ.'CO') THEN
!            CALL SOULSBYFLOC3D(WCHU%ADR(ITRAC)%P,TRAV1%R,MESH3D,
!     &      NPOIN2,NPOIN3,NPLAN,HN,UETCAR%R)
!          ENDIF
!      ENDDO
!
!-----------------------------------------------------------------------
!
      RETURN
      END
