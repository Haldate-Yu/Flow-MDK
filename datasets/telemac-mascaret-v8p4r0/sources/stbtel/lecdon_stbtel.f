!                       ************************
                        SUBROUTINE LECDON_STBTEL
!                       ************************
!
!***********************************************************************
!  STBTEL V5P2
!***********************************************************************
!
!brief    Parsing the CAS file by calling DAMOCLES
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| FILE_DESC      |<--| Stores strings 'submit' of dictionary
!| MOTCAR         |<--| Values of key-words of type character
!| NCAR           |-->| Number of letters in string path
!| PATH           |-->| Full path to code dictionary
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_TELEMAC
      USE DECLARATIONS_STBTEL
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
!
!     ADDED BELOW FOR EDAMOX:
!
      INTEGER          TROUVE(4,MAXKEYWORD)
      INTEGER          ADRES(4,MAXKEYWORD) , DIMENS(4,MAXKEYWORD)
      INTEGER          MOTINT(MAXKEYWORD)
      INTEGER          NLNG
      CHARACTER(LEN=PATH_LEN)    MOTCAR(MAXKEYWORD)
      CHARACTER(LEN=72)     MOTCLE(4,MAXKEYWORD,2)
      DOUBLE PRECISION MOTREA(MAXKEYWORD)
      LOGICAL          DOC
      LOGICAL          MOTLOG(MAXKEYWORD)
!
!     ADDED ABOVE FOR EDAMOX
!
      INTEGER I
!
!-----------------------------------------------------------------------
!
      DOC = .FALSE.
      NLNG=2
!
      CALL DAMOCLES( ADRES , DIMENS, MAXKEYWORD   , DOC    , LNG , LU ,
     &               MOTINT, MOTREA, MOTLOG , MOTCAR ,
     &               MOTCLE, TROUVE, NCLE  , NCAS   , .FALSE. )
!
!     SETTING PARAMETERS UNDER THEIR FORTRAN NAME
!
!-----------------------------------------------------------------------
!     KEYWORDS OF TYPE INTEGER
!-----------------------------------------------------------------------
!
      NBAT      = MOTINT  (ADRES(1,1))
      LGVEC     = MOTINT  (ADRES(1,2))
      NSOM      = MIN(MOTINT  (ADRES(1,3)),9)
      NSOM2     = MOTINT  (ADRES(1,4))
      ALLOCATE(SOM2(NSOM2, 2))
      MAX_SEG_PER_POINT     = MOTINT(ADRES(1,6))
!
!-----------------------------------------------------------------------
!     KEYWORDS OF TYPE FLOAT
!-----------------------------------------------------------------------
!
      EPSI      = MOTREA  (ADRES(2,1))
      DM        = MOTREA  (ADRES(2,2))
      CORTRI    = MOTREA  (ADRES(2,3))
!
      IF (NSOM.GE.3) THEN
        DO I=1,NSOM
          SOM(I,1) = MOTREA  (ADRES(2,4)+I-1)
          SOM(I,2) = MOTREA  (ADRES(2,5)+I-1)
        ENDDO
        SOM(NSOM+1,1) = SOM(1,1)
        SOM(NSOM+1,2) = SOM(1,2)
      ENDIF
!
      IF (NSOM2.GE.3) THEN
        DO I=1,NSOM2
          SOM2(I,1) = MOTREA  (ADRES(2,6)+I-1)
          SOM2(I,2) = MOTREA  (ADRES(2,7)+I-1)
        ENDDO
      ENDIF
!
      SEUSEC =  MOTREA  (ADRES(2,8))
      DX =  MOTREA  (ADRES(2,9))
      DY =  MOTREA  (ADRES(2,10))
!
!-----------------------------------------------------------------------
!     KEYWORDS OF TYPE BOOLEAN
!-----------------------------------------------------------------------
!
      DECTRI    = MOTLOG  (ADRES(3,1))
      COLOR     = MOTLOG  (ADRES(3,2))
      ELIDEP    = MOTLOG  (ADRES(3,3))
      DIV4      = MOTLOG  (ADRES(3,4))
      FONTRI    = MOTLOG  (ADRES(3,5))
      OPTASS    = MOTLOG  (ADRES(3,6))
!
      ADDFAS    = MOTLOG  (ADRES(3,7))
      PROJEX    = MOTLOG  (ADRES(3,8))
!
      IF (NSOM2.GE.3) DIV4 = .TRUE.
!
      ELISEC = MOTLOG  (ADRES(3,9))
      ELPSEC = MOTLOG  (ADRES(3,10))
      STOTOT = MOTLOG  (ADRES(3,11))
      DEBUG  = MOTLOG  (ADRES(3,12))
      CONVER = MOTLOG  (ADRES(3,13))
      SRF_BND = MOTLOG  (ADRES(3,14))
      TRANSLATE = MOTLOG  (ADRES(3,15))
      AUTO_PRECISION = MOTLOG  (ADRES(3,16))
!
!-----------------------------------------------------------------------
!     KEYWORDS OF TYPE CHARACTERE
!-----------------------------------------------------------------------
!
      NBFOND=0

      IF (MOTCAR(ADRES(4,8)).NE.' ') THEN
        NBFOND = NBFOND + 1
        FOND(NBFOND) = MOTCAR(ADRES(4,8))
        NOMFON = MOTCAR(ADRES(4,8))
      ENDIF
      IF (MOTCAR(ADRES(4,9)).NE.' ') THEN
        NBFOND = NBFOND + 1
        FOND(NBFOND) = MOTCAR(ADRES(4,9))
        NOMFO2 = MOTCAR(ADRES(4,9))
      ENDIF
      IF (MOTCAR(ADRES(4,10)).NE.' ') THEN
        NBFOND = NBFOND + 1
        FOND(NBFOND) = MOTCAR(ADRES(4,10))
        NOMIMP = MOTCAR(ADRES(4,10))
      ENDIF
      IF (MOTCAR(ADRES(4,17)).NE.' ') THEN
        NBFOND = NBFOND + 1
        FOND(NBFOND) = MOTCAR(ADRES(4,17))
        NOMSOU = MOTCAR(ADRES(4,17))
      ENDIF
      IF (MOTCAR(ADRES(4,18)).NE.' ') THEN
        NBFOND = NBFOND + 1
        FOND(NBFOND) = MOTCAR(ADRES(4,18))
        NOMFRC = MOTCAR(ADRES(4,18))
      ENDIF
!
      NOMGEO = MOTCAR( ADRES(4, 5) )
      NOMFOR = MOTCAR( ADRES(4, 3) )
      NOMCAS = MOTCAR( ADRES(4, 4) )
      NOMLIM = MOTCAR( ADRES(4, 7) )
      NOMRES = MOTCAR( ADRES(4, 6) )
      FFORMAT = 'SERAFIN '
      OUT_FORMAT = MOTCAR( ADRES(4, 31) )(1:8)
      NOMFO1 = MOTCAR( ADRES(4,15) )
      INFILE = MOTCAR( ADRES(4,24) )
      OUTFILE = MOTCAR( ADRES(4,25) )
      BOUNDFILE = MOTCAR( ADRES(4,26) )
      LOGFILE = MOTCAR( ADRES(4,27) )
      OUTBNDFILE = MOTCAR( ADRES(4,28) )
      OUTLOGFILE = MOTCAR( ADRES(4,29) )
      NOMBND2 = MOTCAR( ADRES(4,30) )
!
      STD       = MOTCAR ( ADRES(4,11))(1:3)
      MAILLE    = MOTCAR ( ADRES(4,14))(1:9)
      INFMT     = MOTCAR ( ADRES(4,22))(1:9)
      OUTFMT    = MOTCAR ( ADRES(4,23))(1:9)
!
      FUSION = .FALSE.
      IF (MOTCAR(ADRES(4,15)).NE.' '.AND.MAILLE.EQ.'SELAFIN')
     &   FUSION = .TRUE.
!
!-----------------------------------------------------------------------
!     CHECK ON VALUES READ
!-----------------------------------------------------------------------
!
      IF (FONTRI) NBFOND = 1
      IF (NBFOND.GT.5) THEN
        WRITE(LU,4000)
        CALL PLANTE(1)
        STOP
      ENDIF
!
      IF (STD.NE.'IBM'.AND.STD.NE.'I3E'.AND.STD.NE.'STD') THEN
        WRITE(LU,4100) STD
        CALL PLANTE(1)
        STOP
      ENDIF
!
      IF (MAILLE.NE.'SUPERTAB4'.AND.MAILLE.NE.'SUPERTAB6'.AND.
     &    MAILLE.NE.'SIMAIL'   .AND.MAILLE.NE.'SELAFIN'  .AND.
     &    MAILLE.NE.'TRIGRID'  .AND.MAILLE.NE.'MASTER2'  .AND.
     &    MAILLE.NE.'FASTTABS' .AND.MAILLE.NE.'ADCIRC'   ) THEN
        WRITE(LU,4200) MAILLE
        CALL PLANTE(1)
        STOP
      ENDIF
!
      IF (MAILLE.EQ.'SUPERTAB4') THEN
!     START POSITION OF THE LIST OF NODES
        NSEC11 = 15
        NSEC12 = 0
!     START POSITION OF THE LIST OF IKLE
        NSEC2  = 71
!     START POSITION FOR THE TITLE
        NSEC3  = 151
      ELSEIF (MAILLE.EQ.'SUPERTAB6') THEN
!     START POSITION OF THE LIST OF NODES (SINGLE PRECISION)
        NSEC11 = 15
!     START POSITION OF THE LIST OF NODES (DOUBLE PRECISION)
        NSEC12 = 781
!     START POSITION OF THE LIST OF IKLE
        NSEC2  = 780
!     START POSITION OF THE LIST OF THE TITLE
        NSEC3  = 151
      ELSEIF (MAILLE.EQ.'MASTER2') THEN
!     START POSITION OF THE LIST OF NODES
        NSEC11 = 0
        NSEC12 = 2411
!     START POSITION OF THE LIST OF IKLE
        NSEC2  = 2412
!     START POSITION OF THE LIST OF THE TITLE
        NSEC3  = 151
      ENDIF
!
!-----------------------------------------------------------------------
!
      IF (ELISEC) THEN
        IF (MAILLE.NE.'SELAFIN') THEN
          WRITE(LU,4300)
          CALL PLANTE(1)
          STOP
        ENDIF
        IF (NBFOND.GT.0) THEN
          WRITE(LU,4301)
          CALL PLANTE(1)
          STOP
        ENDIF
        IF (DIV4) THEN
          WRITE(LU,4302)
          CALL PLANTE(1)
          STOP
        ENDIF
        DIV4      = .FALSE.
        FONTRI    = .FALSE.
        OPTASS    = .FALSE.
        ADDFAS    = .FALSE.
        PROJEX    = .FALSE.
      ENDIF
!
!-----------------------------------------------------------------------
!
4000  FORMAT(//,1X,'||||||||||||||||||||||||||||||||||||||||||||||',/,
     &          1X,'LECDON . THE NUMBER OF BOTTOM TOPOGRAPHY FILES',/,
     &          1X,'         IS LIMITED TO 5 |',/,
     &          1X,'         (KEYWORD : BOTTOM TOPOGRAPHY FILE)',/,
     &          1X,'||||||||||||||||||||||||||||||||||||||||||||||',//)
!
4100  FORMAT(//,1X,'||||||||||||||||||||||||||||||||||||||||||||',/,
     &          1X,'LECDON . UNKNOWN BINARY FILE STANDARD : ',A3,/,
     &          1X,'         (KEYWORD : BINARY FILE STANDARD)',/,
     &          1X,'||||||||||||||||||||||||||||||||||||||||||||',//)
!
4200  FORMAT(//,1X,'||||||||||||||||||||||||||||||||||||||||||||||',/,
     &          1X,'LECDON . UNKNOWN TYPE OF MESH GENERATOR : ',A9,/,
     &          1X,'         (KEYWORD : MESH GENERATOR)',/,
     &          1X,'||||||||||||||||||||||||||||||||||||||||||||||',//)
 4300 FORMAT(//,1X,'||||||||||||||||||||||||||||||||||||||||||||',/,
     &          1X,'LECDON . THE DRY ELEMENTS ELIMINATION IS ONLY',/,
     &          1X,'AVAILABLE WHEN USING SELAFIN FILE.',/,
     &          1X,'||||||||||||||||||||||||||||||||||||||||||||',//)
 4301 FORMAT(//,1X,'||||||||||||||||||||||||||||||||||||||||||||',/,
     &          1X,'LECDON . BATHYMETRY INTERPOLATION IMPOSSIBLE',/,
     &          1X,'WHEN USING DRY ELEMENTS ELIMINATION.',/,
     &          1X,'||||||||||||||||||||||||||||||||||||||||||||',//)
 4302 FORMAT(//,1X,'||||||||||||||||||||||||||||||||||||||||||||',/,
     &          1X,'LECDON . TRIANGLE CUTTING IMPOSSIBLE',/,
     &          1X,'WHEN USING DRY ELEMENTS ELIMINATION.',/,
     &          1X,'||||||||||||||||||||||||||||||||||||||||||||',//)
!
!-----------------------------------------------------------------------
!
      RETURN
      END
