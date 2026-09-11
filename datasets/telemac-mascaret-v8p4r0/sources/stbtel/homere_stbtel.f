!                       *********************
                        PROGRAM HOMERE_STBTEL
!                       *********************
!
!***********************************************************************
!  STBTEL V7P0
!***********************************************************************
!
!brief
!+      1) Loading all data necessary to allocate pointers:
!+         CAS file and GEO file
!+
!+      2) Call STBTEL
!+
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
!     USE BIEF
      USE DECLARATIONS_TELEMAC
      USE DECLARATIONS_STBTEL
      USE DECLARATIONS_SPECIAL
      USE INTERFACE_STBTEL
      USE INTERFACE_HERMES
      IMPLICIT NONE
!
      INTEGER TDEB,TFIN
!
      CHARACTER(LEN=24), PARAMETER :: CODE='STBTEL                  '
!
      INTEGER  TIME_IN_SECONDS
      EXTERNAL TIME_IN_SECONDS
!
      INTEGER NPOIN1
!
      INTEGER NSFOND ,NFOND(5)
!
      CHARACTER(LEN=11) TYPELE
      CHARACTER(LEN=80) TITRE
      CHARACTER(LEN=6) PRECIS

      INTEGER IERR
!
!
!======================================================================
!
      INTEGER NCAR
      CHARACTER(LEN=PATH_LEN) FORTXY(50)
      CHARACTER(LEN=MAXLENTMPDIR) PATH
      NGEO=1
      NCLE=2
      NCAS=3
      NLIM=7
      NRES=8
      NSOU=11
      NIMP=12
      NFRC=20
      NFON=23
      NFO1=26
      NFO2=27
      NINP=28
      NOUT=29
      NBND=30
      NLOG=31
      NOBND=32
      NOLOG=33
      NBND2=34
      NOMGEO=' '
      NOMFO1=' '
      NOMFO2=' '
      NOMFON=' '
      NOMIMP=' '
      NOMSOU=' '
      NOMFRC=' '
      NOMFOR=' '
      NOMCAS=' '
      NOMLIM=' '
      NOMRES=' '
      INFILE=' '
      OUTFILE=' '
      BOUNDFILE=' '
      LOGFILE=' '
      OUTBNDFILE=' '
      OUTLOGFILE=' '
      NOMBND2 = ' '
      CALL P_INIT(PATH,NCAR,IPID,NCSIZE)
      CALL READ_CONFIG(PATH,NCAR)
      FORTXY(NGEO) ='STBGEO'
      FORTXY(NCLE) ='STBDICO'
      FORTXY(NCAS) ='STBCAS'
      FORTXY(NLIM) ='STBLIM'
      FORTXY(NRES) ='STBRES'
      FORTXY(NSOU) ='STBSOU'
      FORTXY(NIMP) ='STBIMP'
      FORTXY(NFRC) ='STBFRC'
      FORTXY(NFON) ='STBFON'
      FORTXY(NFO1) ='STBFO1'
      FORTXY(NFO2) ='STBFO2'
      FORTXY(NINP) ='STBINP'
      FORTXY(NOUT) ='STBOUT'
      FORTXY(NBND) ='STBBND'
      FORTXY(NLOG) ='STBLOG'
      FORTXY(NOBND) ='STBOBD'
      FORTXY(NOLOG) ='STBOLG'
      FORTXY(NBND2) ='STBND2'
!
      TDEB = TIME_IN_SECONDS()
!
!     LISTING HEADER
!
      CALL PRINT_HEADER(CODE,'                        ')
!
!=======================================================================
!     READING THE CAS FILE
!=======================================================================
!
      OPEN(NCLE , FILE=FORTXY(NCLE) , FORM='FORMATTED'  ,ACTION='READ')
      OPEN(NCAS , FILE=FORTXY(NCAS) , FORM='FORMATTED'  ,ACTION='READ')
      CALL LECDON_STBTEL

!     CHECK IF WE SWITCH TO THE CONVERTER PROGRAM
      IF(CONVER) THEN
        IF (BOUNDFILE.EQ.' ')  FORTXY(NBND) = ' '
        IF (LOGFILE.EQ.' ')    FORTXY(NLOG) = ' '
        IF (OUTBNDFILE.EQ.' ') FORTXY(NOBND) = ' '
        IF (OUTLOGFILE.EQ.' ') FORTXY(NOLOG) = ' '
        CALL CONVERTER(FORTXY(NINP),FORTXY(NBND),
     &                 FORTXY(NOUT),FORTXY(NOBND))
        ! GO TO THE END OF STBTEL
        GOTO 666
      ENDIF
!
!     THE UNIVERSAL FILE IS OF BINARY TYPE OR FORMATTED
!
      IF(MAILLE.EQ.'SIMAIL') THEN
        OPEN(NGEO,FILE=FORTXY(NGEO), FORM='UNFORMATTED')
      ELSE IF(MAILLE.EQ.'SELAFIN') THEN
        CALL OPEN_MESH(FFORMAT,FORTXY(NGEO),NGEO,'READ     ',IERR)
        CALL CHECK_CALL(IERR, 'OPEN_MESH:NGEO')
      ELSE
        OPEN(NGEO,FILE=FORTXY(NGEO), FORM='FORMATTED')
      ENDIF
!
!=======================================================================
!     OPENING FILES
!=======================================================================
!
!     IN CASE THE OUTPUT FORMAT WAS NOT SPECIFIED USING FFORMAT (THAT
!     BY DEFAULT IS SERAFIN) AND IF THE INPUT FILE IS SERAFIN IT WILL
!     BE THE SAME FORMAT AS THE INPUT FILE (FFORMAT WILL BE REPLACE BY
!     THE FORMAT OF THE FILE WHEN WE OPEN IT)
      IF (OUT_FORMAT == '') THEN
        OUT_FORMAT = FFORMAT
      ENDIF

      IF(NOMRES(1:1).NE.' ') THEN
        CALL OPEN_MESH(OUT_FORMAT,FORTXY(NRES),NRES,'WRITE    ',IERR)
        CALL CHECK_CALL(IERR, 'OPEN_MESH:NRES')
      ENDIF
!
      IF(NOMLIM(1:1).NE.' ') THEN
        CALL OPEN_BND(OUT_FORMAT,FORTXY(NLIM),NRES,'WRITE    ',IERR)
        CALL CHECK_CALL(IERR, 'OPEN_BND:NRES')
      ENDIF
!
      IF(NOMBND2(1:1).NE.' ') THEN
        CALL OPEN_BND(FFORMAT,FORTXY(NBND2),NGEO,'READ     ',IERR)
        CALL CHECK_CALL(IERR, 'OPEN_BND:NGEO')
      ENDIF
!
      IF(NOMSOU(1:1).NE.' ') THEN
        OPEN(NSOU,FILE=FORTXY(NSOU),FORM='FORMATTED',ACTION='READWRITE')
      ENDIF
!
      IF(NOMIMP(1:1).NE.' ') THEN
        OPEN(NIMP,FILE=FORTXY(NIMP),FORM='FORMATTED',ACTION='READ')
      ENDIF
!
      IF(NOMFRC(1:1).NE.' ') THEN
        OPEN(NFRC,FILE=FORTXY(NFRC),FORM='FORMATTED',ACTION='READ')
      ENDIF
!
      IF(NOMFON(1:1).NE.' ') THEN
        OPEN(NFON,FILE=FORTXY(NFON),FORM='FORMATTED',ACTION='READ')
      ENDIF
!
      IF(NOMFO1(1:1).NE.' ') THEN
        OPEN(NFO1,FILE=FORTXY(NFO1),FORM='FORMATTED',ACTION='READ')
      ENDIF
!
      IF(NOMFO2(1:1).NE.' ') THEN
        OPEN(NFO2,FILE=FORTXY(NFO2),FORM='FORMATTED',ACTION='READ')
      ENDIF
!
!
!
      IF(NOMFO1(1:1).NE.' '.AND.MAILLE.EQ.'SELAFIN') THEN
!       POUR SELAFIN : NFO1 EST BINAIRE
        CLOSE(NFO1)
        CALL OPEN_MESH(FFORMAT,FORTXY(NFO1),NFO1,'READ     ',IERR)
        CALL CHECK_CALL(IERR, 'OPEN_MESH:NFO1')
      ENDIF
!
!     FILE UNITS: FOND1 AND FOLLOWING
!
      IF(NBFOND.NE.0) THEN
        NFOND(1) = 23
        NFOND(2) = 27
        NFOND(3) = 12
        NFOND(4) = 11
        NFOND(5) = 20
      ENDIF
!
!=======================================================================
!     INITIALISATION : GATHER NUMBER OF POINTS, OF ELEMENTS AND
!                  OF TYPES OF ELEMENTS
!=======================================================================
!
!     INITIALISATION OF THE LENGTH OF THE ARRAY NOP5 TO 1
!
      INOP5 = 1
      NSFOND = 0
!
      IF (MAILLE.EQ.'SELAFIN') THEN
        CALL INISEL (NPOIN1,TYPELE,STD,NSFOND,FUSION,IHAUT,
     &                NGEO , NFO1)
      ELSEIF (MAILLE.EQ.'TRIGRID') THEN
        CALL INITRI (NPOIN1,TYPELE,NGEO,NFO1)
      ELSEIF (MAILLE.EQ.'FASTTABS') THEN
        CALL INIFAS (TYPELE,NGEO)
      ELSEIF (MAILLE.EQ.'SIMAIL') THEN
        CALL INISIM (NPOIN1,TYPELE,INOP5,NGEO)
      ELSEIF (MAILLE.EQ.'ADCIRC') THEN
        CALL INIADC (NPOIN1,TYPELE,NSFOND,IHAUT,NGEO,TITRE)
      ELSE
        CALL INISTB (NPOIN1,TYPELE,MAILLE,PRECIS,NGEO,
     &                NSEC2,NSEC11,NSEC12)
      ENDIF
!
!=======================================================================
!     DEFINITION OF POINTERS
!=======================================================================
!
      CALL POINT_STBTEL
!
!=======================================================================
!     CALL MAIN PROGRAM
!=======================================================================
!
      CALL STBTEL(NPOIN1,TYPELE,NFOND,PRECIS,NSFOND,TITRE)
!
!=======================================================================
!     CLOSING FILES
!=======================================================================
!
      IF(NOMLIM(1:1).NE.' ') then
        CALL CLOSE_BND(FFORMAT,NRES,IERR)
        CALL CHECK_CALL(IERR, 'CLOSE_BND:NRES')
      ENDIF
      IF(NOMRES(1:1).NE.' ') THEN
        CALL CLOSE_MESH(FFORMAT,NRES,IERR)
        CALL CHECK_CALL(IERR, 'CLOSE_MESH:NRES')
      ENDIF

      IF(NOMBND2(1:1).NE.' ') THEN
        CALL CLOSE_BND(FFORMAT,NGEO,IERR)
        CALL CHECK_CALL(IERR, 'CLOSE_BND:NGEO')
      ENDIF
      IF(MAILLE.EQ.'SELAFIN') THEN
        CALL CLOSE_MESH(FFORMAT, NGEO,IERR)
        CALL CHECK_CALL(IERR, 'CLOSE_MESH:NGEO')
      ELSE
        CLOSE(NGEO)
      ENDIF

      IF(NOMFO1(1:1).NE.' '.AND.MAILLE.EQ.'SELAFIN') THEN
        CALL CLOSE_MESH(FFORMAT, NFO1,IERR)
        CALL CHECK_CALL(IERR, 'CLOSE_MESH:NFO1')
      ENDIF

      CLOSE(NCLE)
      CLOSE(NCAS)
      IF(NOMSOU(1:1).NE.' ') CLOSE(NSOU)
      IF(NOMIMP(1:1).NE.' ') CLOSE(NIMP)
      IF(NOMFRC(1:1).NE.' ') CLOSE(NFRC)
      IF(NOMFON(1:1).NE.' ') CLOSE(NFON)
      IF(NOMFO2(1:1).NE.' ') CLOSE(NFO2)
!
!-----------------------------------------------------------------------
!
      WRITE(LU,11)
11    FORMAT(1X,///,1X,'CORRECT END OF RUN',///)
!
!-----------------------------------------------------------------------
!
666   TFIN = TIME_IN_SECONDS()
      WRITE(LU,*) 'COMPUTER TIME: ',TFIN-TDEB,' SECONDS'
      CALL P_EXIT()
!
!-----------------------------------------------------------------------
!
      STOP 0
      END
