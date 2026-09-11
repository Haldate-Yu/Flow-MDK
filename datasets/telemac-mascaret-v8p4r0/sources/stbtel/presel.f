!                       *****************
                        SUBROUTINE PRESEL
!                       *****************
!
     &(IKLE,TRAV1,NELEM,NELMAX,NDP,TEXTE,NBFOND,SORLEO,COLOR,
     & NSFOND,NVARIN,NVAROU,MAILLE)
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Preprocess parameters and data before calling FMTSEL
!+           TRIGRID file
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| IKLE      |<->| Connectivity
!| TRAV1     |<->| Working arrays
!| NELEM     |-->| Total number of elements in the mesh
!| NPMAX     |-->| Actual siwe of the x and y arrays
!|           |   | (npmax = npoin + 0.1*nelem)
!| NDP       |-->| Number of node per element
!| TEXTE     |<->| Names and units of the variables
!| NBFOND    |-->| Number of bathymetric files (5 maxi)
!| SORLEO    |-->| Variables that we wish to write to (26 bools)
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) :: NDP,NELEM,NELMAX,NBFOND,NVARIN
      INTEGER, INTENT(INOUT) :: NSFOND,NVAROU
      INTEGER, INTENT(INOUT) :: TRAV1(NELEM,NDP)
      INTEGER, INTENT(IN) :: IKLE(NELMAX,NDP)
      CHARACTER(LEN=32), INTENT(INOUT) :: TEXTE(26)
      CHARACTER(LEN=9), INTENT(IN) :: MAILLE
      LOGICAL, INTENT(INOUT) :: SORLEO(26),COLOR
!
      INTEGER I,IDP,IELEM
!
!-----------------------------------------------------------------------
!
!     IKLE IS REBUILD DEPENDING ON THE TOTAL NUMBER OF ELEMENTS
!     THE RESULT IS SET TO THE WORKIGN ARRAY TRAV1
!
      DO IELEM = 1 , NELEM
        DO IDP = 1 , NDP
          TRAV1(IELEM,IDP) = IKLE(IELEM,IDP)
        ENDDO
      ENDDO
!
!-----------------------------------------------------------------------
!
!     VARIABLE NAMES TAKEN FROM THE GEOMETRIE FILE
!     ARRAY MARKING THOSE THAT WILL BE EVENTUALLY WRITTEN
!
      DO I = 1 , 26
        SORLEO(I) = .FALSE.
      ENDDO
!
      NVAROU = NVARIN
      IF (NVAROU.GT.0) THEN
        DO I = 1 , NVAROU
          SORLEO(I) = .TRUE.
        ENDDO
      ENDIF
!
!-----------------------------------------------------------------------
!
!     ADDING BATHYMETRY THEN NODE COLOUR THEN A DUMMY VARIABLE
!     IF NECESSARY AS OUTPUT VARIABLES
!
      IF (NBFOND.GT.0.AND.NSFOND.EQ.0.AND.NVAROU.LT.26) THEN
        NVAROU = NVAROU + 1
        SORLEO(NVAROU) = .TRUE.
        IF (LNG.EQ.LNG_FR)
     &    TEXTE(NVAROU)='FOND                            '
        IF (LNG.EQ.LNG_EN)
     &    TEXTE(NVAROU)='BOTTOM                          '
        NSFOND = NVAROU
      ELSEIF (NBFOND.EQ.0) THEN
        NSFOND = 0
      ENDIF
!
      IF (COLOR) THEN
        IF (NVAROU.LT.26) THEN
          NVAROU = NVAROU + 1
          SORLEO(NVAROU) = .TRUE.
          TEXTE(NVAROU) = 'COULEUR                         '
        ELSE
          COLOR = .FALSE.
        ENDIF
      ENDIF
!
      IF(NVAROU.EQ.0) THEN
        SORLEO(1) = .TRUE.
        IF(MAILLE.NE.'ADCIRC') THEN
          TEXTE(1) = 'MAILLAGE                        '
        ELSE
          IF (LNG.EQ.LNG_FR) TEXTE(1)='FOND                            '
          IF (LNG.EQ.LNG_EN) TEXTE(1)='BOTTOM                          '
        ENDIF
      ENDIF
!
!-----------------------------------------------------------------------
!
      RETURN
      END
