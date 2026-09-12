!                   ******************
                    MODULE OUT_HISTORY
!                   ******************
!
!***********************************************************************
! BIEF
!***********************************************************************
!
      USE BIEF
      USE DECLARATIONS_SPECIAL
!
      IMPLICIT NONE
!
!----------------------------------------------------------------------
!
      ! Definition of data types
      TYPE INTERPDATA
        ! Data for interpolation
        DOUBLE PRECISION, POINTER, DIMENSION(:,:) :: WEIGHTS
        INTEGER, DIMENSION(:,:), POINTER :: POINTLIST
        LOGICAL, DIMENSION(:), POINTER :: MASKARR
        INTEGER :: NRCELLLOC
      END TYPE

      TYPE LOCALDATA
        ! Data on local processor
        INTEGER :: NRCELLLOC
        INTEGER, POINTER, DIMENSION(:) :: STATOUT
        INTEGER, POINTER, DIMENSION(:) :: INDEX
        DOUBLE PRECISION, POINTER, DIMENSION(:) :: X
        DOUBLE PRECISION, POINTER, DIMENSION(:) :: Y
        DOUBLE PRECISION, POINTER, DIMENSION(:) :: DATAARR
      END TYPE

      TYPE TIMECOORDATA
      ! Times and coordinates
        CHARACTER(LEN=100),DIMENSION(:), POINTER :: STATNAME
        INTEGER,          DIMENSION(:), POINTER :: STATOUT
        INTEGER,          DIMENSION(:), POINTER :: INDEX
        DOUBLE PRECISION, DIMENSION(:), POINTER :: XHISTOUT,YHISTOUT
        DOUBLE PRECISION, DIMENSION(:), POINTER :: THISTSTART,THISTEND,DTHIST
        INTEGER :: NRPOINT
        INTEGER :: NRTIME
      END TYPE

      TYPE HISTDATA
        ! Variables for history file
        INTEGER :: HISTSTEP
        CHARACTER(LEN=32), ALLOCATABLE, DIMENSION(:) :: VARNAME
      END TYPE
!
!----------------------------------------------------------------------
!
      TYPE(INTERPDATA), ALLOCATABLE, DIMENSION(:) :: INTDAT
      TYPE(HISTDATA), ALLOCATABLE, DIMENSION(:) :: HISTDAT
      TYPE(TIMECOORDATA), ALLOCATABLE, DIMENSION(:) :: TCDAT
      TYPE(LOCALDATA), ALLOCATABLE, DIMENSION(:) :: LOCDAT

      LOGICAL, ALLOCATABLE, DIMENSION(:) :: LEO_PER_FILE
      LOGICAL :: IS_INIT = .FALSE.
      LOGICAL :: IS_CLEAN
      LOGICAL :: YAHIST = .FALSE.

      ! Counter for the number of files to be made
      INTEGER :: NRFILE  = 0
      INTEGER, PARAMETER :: MAXFILE = 10
      CHARACTER(LEN=6), ALLOCATABLE, DIMENSION(:) :: MODULE_LIST

      INTEGER, PARAMETER :: DEBUG = 0
      INTEGER, DIMENSION(:), ALLOCATABLE :: NPOIN_GLB
      PRIVATE

      PUBLIC :: HISTPERIOD,OUTHIST_END,OUTHIST,OUTHIST_PREPARE, &
     &          OUTHIST_INIT,YAHIST

      SAVE

      CONTAINS

!                   *********************
                    SUBROUTINE HISTPERIOD &
!                   *********************
!
      (MODNAME,TIME,LEO)
!
!***********************************************************************
! BIEF
!***********************************************************************
!
!>@brief    Checks whether output needs to be generated
!+
!+
!
!history WA BREUGEM (IMDC)
!+        1-9-2020
!+
!+
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param [in,out] LEO     Write history file at this time step
!>@param [in]     TIME    Time of current time step
!>@param [in]     MODNAME Name of the calling module
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      DOUBLE PRECISION, INTENT(IN) :: TIME
      CHARACTER(LEN=6), INTENT(IN) :: MODNAME
      LOGICAL, INTENT(INOUT) :: LEO
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER IFILE,ITIME
!
!-----------------------------------------------------------------------
!
      LEO = .FALSE.
      IF(NRFILE.EQ.0) THEN
        RETURN
      ENDIF
      ! Find the right module
      DO IFILE=1,NRFILE
        ! Note, only the first three characters are checked,
        ! in order to make sure that this works for both output files
        ! in TELEMAC-3D
        IF(MODULE_LIST(IFILE)(1:3).EQ.MODNAME(1:3)) THEN
          EXIT
        ENDIF
        IF(IFILE.EQ.NRFILE) THEN
          ! No history file. then LEO = .FALSE.
          RETURN
        ENDIF
      ENDDO

! Check whether output is needed at the current time step
      LEO = .FALSE.
      DO ITIME=1,TCDAT(IFILE)%NRTIME
        IF(TIME.GE.TCDAT(IFILE)%THISTSTART(ITIME) .AND. &
     &     TIME.LE.TCDAT(IFILE)%THISTEND(ITIME)) THEN
          IF(MOD(NINT(TIME-TCDAT(IFILE)%THISTSTART(ITIME)), &
     &           NINT(TCDAT(IFILE)%DTHIST(ITIME))).EQ.0) THEN
            LEO = .TRUE.
            EXIT
          ENDIF
        ENDIF
      ENDDO
      LEO_PER_FILE(IFILE) = LEO
!
!-----------------------------------------------------------------------
!
      RETURN
      END SUBROUTINE HISTPERIOD

!                   ***********************
                    SUBROUTINE OUTHIST_INIT
!                   ***********************
!
!
!***********************************************************************
! BIEF
!***********************************************************************
!
!>@brief  Initializes the module for history files
!+
!+
!
!history WA BREUGEM (IMDC)
!+      1-9-2020
!+
!+
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER IERR
!
!-----------------------------------------------------------------------
!
      ! Check whether the module is already initialized
      IF(IS_INIT) THEN
        RETURN
      ENDIF
      IS_INIT = .TRUE.
      IS_CLEAN = .FALSE.
      NRFILE  = 0

      !Allocate variabels
      ALLOCATE(MODULE_LIST(MAXFILE),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUTHIST::MODULE_LIST')

      ! Allocate data types
      ALLOCATE(INTDAT(MAXFILE),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUTHIST::INTDAT')
      ALLOCATE(HISTDAT(MAXFILE),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUTHIST::HISTDAT')
      ALLOCATE(TCDAT(MAXFILE),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUTHIST::TCDAT')
      ALLOCATE(LOCDAT(MAXFILE),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUTHIST::LOCDAT')
      ALLOCATE(LEO_PER_FILE(MAXFILE),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUTHIST::LEO_PER_FILE')

      LEO_PER_FILE = .FALSE.
!
!-----------------------------------------------------------------------
!
      RETURN
      END SUBROUTINE OUTHIST_INIT

!                   ****************************
                    SUBROUTINE OUTHIST_MAKE_FILE &
!                   ****************************
!
      (OUTFILE,MAXVAR,IFILE,SORG,TEXTE,NPOIN,LD,NPLAN,DATE,TIME, &
       X_ORIG,Y_ORIG,IERR)
!
!***********************************************************************
! BIEF
!***********************************************************************
!
!>@brief
!
!history WA BREUGEM (IMDC)
!+        20/06/2016
!+        V7P1
!+
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in]     OUTFILE File structure of output file
!>@param[in]     MAXVAR  Maximum number of output variables
!>@param[in]     IFILE   Number of files to write
!>@param[in]     SORG    Mask which variables to write to the file
!>@param[in]     TEXTE   List of variable names and units
!>@param[in]     NPOIN   Number of points to write to the file
!>@param[in]     LD      Structure with x and y coordinates of the
!                        points to write
!>@param[in]     NPLAN   Number of vertical planes
!>@param[in]     DATE    Reference date of the simulation
!>@param[in]     TIME    Time
!>@param[in]     X_ORIG  X-coordinate of the origin on the mesh
!>@param[in]     Y_ORIG  Y-coordinate of the origin on the mesh
!>@param[in,out] IERR    Error code. Zero means no error
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE INTERFACE_HERMES
      USE DECLARATIONS_PARALLEL
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      TYPE(BIEF_FILE),INTENT(IN) :: OUTFILE
      INTEGER, INTENT(IN) :: MAXVAR,NPOIN,NPLAN,IFILE
      LOGICAL, INTENT(IN) :: SORG(MAXVAR)
      CHARACTER(LEN=32),INTENT(IN) :: TEXTE(MAXVAR)
      TYPE(LOCALDATA), INTENT(IN) :: LD
      INTEGER,DIMENSION(3), INTENT(IN) :: DATE,TIME
      INTEGER, INTENT(IN) :: X_ORIG,Y_ORIG
      ! Why is this integer?
      INTEGER, INTENT(INOUT) :: IERR
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER , PARAMETER :: TYPEELM = POINT_ELT_TYPE !
      INTEGER,  PARAMETER :: NDP = 1
      INTEGER,  PARAMETER :: NPTIR = 0
      INTEGER , DIMENSION(:), ALLOCATABLE :: IPOBO
      INTEGER , DIMENSION(:,:), ALLOCATABLE :: IKLE
      INTEGER :: I,N,NRVAR,NELEM,NPTFR,DIM1
      CHARACTER(LEN=80), PARAMETER :: TITLE = 'HISTORY FILE'
!
!-----------------------------------------------------------------------
!
      ! Prepare output file
      NRVAR = COUNT(SORG)
      N = 0
      ! Make a list of variable names
      ALLOCATE(HISTDAT(IFILE)%VARNAME(NRVAR),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::VARNAME')
      DO I=1,MAXVAR
        IF(SORG(I)) THEN
          N = N + 1
          HISTDAT(IFILE)%VARNAME(N)= TEXTE(I)
        ENDIF
      ENDDO
      ! Make the header
      CALL SET_HEADER(OUTFILE%FMT,OUTFILE%LU,TITLE,NRVAR, &
     &                HISTDAT(IFILE)%VARNAME,IERR)
      CALL CHECK_CALL(IERR,'OUT_HIST:SET_HEADER')

      ! Make a fake mesh (NPOIN * 1 )
      ALLOCATE(IKLE(NPOIN,1),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::IKLE')
      ALLOCATE(IPOBO(NPOIN),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::IPOBO')

! DIMENSION. In case of points (2D): 0-dimensional
!            In case of a profile(3D): 1-dimensional
      IF(NPLAN.GT.1) THEN
        DIM1 = 1
      ELSE
        DIM1 = 0
      ENDIF
      ! Take care. npoin is "3D".
      NPTFR = NPOIN
      NELEM = NPOIN
      DO I=1,NPOIN
        ! Copy station id to ikle
        IKLE(I,1) = LD%STATOUT(I)
        IPOBO(I)  = LD%INDEX(I)
      ENDDO

      ! Write the fake mesh
      CALL SET_MESH(OUTFILE%FMT,OUTFILE%LU,DIM1,TYPEELM,NDP, &
     &              NPTFR,NPTIR,NELEM,                    &
     &              NPOIN,IKLE,IPOBO,IPOBO,            &
     &              LD%X,LD%Y,NPLAN,DATE,TIME,         &
     &              X_ORIG,Y_ORIG,IERR,IN_PLACE=.FALSE.)
      CALL CHECK_CALL(IERR,'OUT_HIST:SET_MESH')

      DEALLOCATE(IPOBO,IKLE)
!
!-----------------------------------------------------------------------
!
      RETURN
      END SUBROUTINE OUTHIST_MAKE_FILE

!                   **************************
                    SUBROUTINE OUTHIST_PREPARE &
!                   **************************
!
      (MODNAME,COORFILE,OUTFILE,MESH2D,NELEM2,NPOIN2,DATE,TIME,MAXVAR, &
       SORG2D,TEXTE,VARSOR,NPLAN)                         
!
!***********************************************************************
! BIEF
!***********************************************************************
!
!>@brief  Prepares the generation of history files
!
! Steps: Read coordinate files
!        Allocate memory
!        Determine weights for linear interpolation
!        Make output file
!+
!
!history WA BREUGEM (IMDC)
!+        1/9/2020
!+
!+
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in]  MODNAME  Name of the calling module
!>@param[in]  COORFILE File structure for the coordinate files
!>@param[in]  OUTFILE  File structure for the output file
!>@param[in]  MESH2D   The mesh
!>@param[in]  NELEM2   Number of 2D elements
!>@param[in]  NPOIN2   Number of 2D nodes
!>@param[in]  DATE     Reference date of the simulation
!>@param[in]  TIME     Reference time of the simulation
!>@param[in]  MAXVAR   Maximum number of variables
!>@param[in]  SORG2D   Mask which variables are written to the file
!>@param[in]  TEXTE    Variable names and units
!>@param[in]  VARSOR   Output data
!>@param[in]  NPLAN    Number of vertical planes
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_PARALLEL
      USE INTERFACE_PARALLEL, ONLY : P_SUM
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      CHARACTER(LEN=6) :: MODNAME
      TYPE(BIEF_FILE), INTENT(IN) :: COORFILE,OUTFILE
      TYPE(BIEF_MESH), INTENT(IN) :: MESH2D
      INTEGER , INTENT(IN) :: NELEM2,NPOIN2,NPLAN
      INTEGER, INTENT(IN) :: MAXVAR
      INTEGER,DIMENSION(3), INTENT(IN) :: DATE,TIME
      LOGICAL, INTENT(IN) :: SORG2D(MAXVAR)
      CHARACTER(LEN=32),INTENT(IN) :: TEXTE(MAXVAR)
      TYPE(BIEF_OBJ), INTENT(IN) :: VARSOR
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER I,NRCOOR,IFILE,NRCOORGLB

      INTEGER IERR
      INTEGER, DIMENSION(2) :: DATA2
      DOUBLE PRECISION, DIMENSION(3) :: DATADD3

! Interpolation method: set to 1 for linear interpolation or 0 for
! nearest neighbour interpolation
      INTEGER, PARAMETER :: INTERP_METHOD = 1

      INTEGER NRPOINT,NRTIME,NRCELLLOC
      CHARACTER(LEN=100)  :: DATASTR
!
!-----------------------------------------------------------------------
!
      ! Read ascii file with input time series
      ! FORMAT: NRTIME, NRPOINTS,
      ! STARTTIME ENDDTIME DT(NRTIME TIMES)
      ! X COORDINATE, Y COORDINATE, STATNR (NRPOINT TIMES)
      !

      ! Check if coordinate file and output file exist
      IF(COORFILE%NAME(1:1).EQ.' ') THEN
        IF(OUTFILE%NAME(1:1).EQ.' ') THEN
          ! History files not used
          RETURN
        ELSE
          WRITE(LU,*)'COORDINATE FILE IS NEEDED WHEN USING HISTORY FILE'
          CALL PLANTE(1)
        ENDIF
      ELSE
        IF(OUTFILE%NAME(1:1).EQ. ' ')THEN
          ! History files not used
          RETURN
        ENDIF
      ENDIF

      ! Add data to the correct file
      NRFILE = NRFILE + 1
      MODULE_LIST(NRFILE) = MODNAME
      YAHIST = .TRUE.

      IF(NRFILE.GT.MAXFILE) THEN
        WRITE (LU,*) 'TOO MANY OUTPUT FILES'
        CALL PLANTE(1)
      ENDIF
      IFILE = NRFILE

      ! Make sure we are at the start of the file, in case it was read
      ! already earlier for another file
      REWIND(COORFILE%LU,IOSTAT=IERR)
      IF(IERR.NE.0) THEN
        WRITE(LU,*) 'ERROR REWINDING FILE ',TRIM(COORFILE%NAME)
        WRITE(LU,*) 'ERROR NUMBER ', IERR
        CALL PLANTE(1)
      ENDIF

      ! Read the number of data
      READ(COORFILE%LU,*,IOSTAT=IERR) DATA2

      IF(IERR.NE.0) THEN
        WRITE(LU,*) 'ERROR READING FILE ',TRIM(COORFILE%NAME)
        WRITE(LU,*) 'ERROR NUMBER ', IERR
        CALL PLANTE(1)
      ENDIF

      TCDAT(IFILE)%NRTIME  = DATA2(1)
      TCDAT(IFILE)%NRPOINT = DATA2(2)

      IF(DEBUG.GT.0) THEN
        WRITE(LU,*) 'NR TIME ', TCDAT(IFILE)%NRTIME, '; NRPOINT ', &
                    TCDAT(IFILE)%NRPOINT
      ENDIF
     
      NRPOINT = TCDAT(IFILE)%NRPOINT
      NRTIME  = TCDAT(IFILE)%NRTIME

      ! Allocate data

      ALLOCATE(TCDAT(IFILE)%XHISTOUT(NRPOINT),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::TCDAT.XHISTOUT')
      TCDAT(IFILE)%XHISTOUT = 0.D0

      ALLOCATE(TCDAT(IFILE)%YHISTOUT(NRPOINT),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::TCDAT.YHISTOUT')
      TCDAT(IFILE)%YHISTOUT = 0.D0
      
      ALLOCATE(TCDAT(IFILE)%INDEX(NRPOINT),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::TCDAT.INDEX')
      TCDAT(IFILE)%INDEX = 0

      ALLOCATE(INTDAT(IFILE)%POINTLIST(NRPOINT,3),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::INTDAT.POINTLIST')
      INTDAT(IFILE)%POINTLIST = 0

      ALLOCATE(INTDAT(IFILE)%WEIGHTS(NRPOINT,3),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::INTDAT.WEIGHTS')
      INTDAT(IFILE)%WEIGHTS = 0.D0

      ALLOCATE(INTDAT(IFILE)%MASKARR(NRPOINT),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::INTDAT.MASKARR')
      INTDAT(IFILE)%MASKARR = .FALSE.

      ALLOCATE(TCDAT(IFILE)%STATNAME(NRPOINT),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::TCDAT.STATNAME')
      TCDAT(IFILE)%STATNAME = ''

      ALLOCATE(TCDAT(IFILE)%STATOUT(NRPOINT),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::TCDAT.STATOUT')
      TCDAT(IFILE)%STATOUT = 0

      ALLOCATE(TCDAT(IFILE)%THISTSTART(NRTIME),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::TCDAT.THISTSTART')
      TCDAT(IFILE)%THISTSTART = 0.D0

      ALLOCATE(TCDAT(IFILE)%THISTEND(NRTIME),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::TCDAT.THISTEND')
      TCDAT(IFILE)%THISTEND = 0.D0

      ALLOCATE(TCDAT(IFILE)%DTHIST(NRTIME),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::TCDAT.DTHIST')
      TCDAT(IFILE)%DTHIST =0.D0

      ! Read time information in the coordinate file
      DO I=1,NRTIME
        READ(COORFILE%LU,*,IOSTAT=IERR) DATADD3
        IF(IERR.NE.0) THEN
          WRITE(LU,*) 'ERROR READING TIME ',I,' IN FILE ', &
                      COORFILE%TELNAME
          CALL PLANTE(1)
        ENDIF
        TCDAT(IFILE)%THISTSTART(I) = DATADD3(1)
        TCDAT(IFILE)%THISTEND(I)   = DATADD3(2)
        TCDAT(IFILE)%DTHIST(I)     = DATADD3(3)
        IF(DEBUG.GT.0) THEN
          WRITE(LU,*) 'TIME ',I,TCDAT(IFILE)%THISTSTART(I), &
                      TCDAT(IFILE)%THISTEND(I),TCDAT(IFILE)%DTHIST(I)
        ENDIF
      ENDDO

      ! Read coordinates in the coordinate file
      DO I=1,NRPOINT
        READ(COORFILE%LU,*,IOSTAT=IERR) DATADD3,DATASTR
        IF(IERR.NE.0) THEN
          WRITE(LU,*) 'ERROR READING POINT ',I,' IN FILE ', &
                      COORFILE%TELNAME
          CALL PLANTE(1)
        ENDIF
        TCDAT(IFILE)%XHISTOUT(I) = DATADD3(1)
        TCDAT(IFILE)%YHISTOUT(I) = DATADD3(2)
        TCDAT(IFILE)%STATOUT(I)  = DATADD3(3)
        TCDAT(IFILE)%INDEX(I)    = I
        TCDAT(IFILE)%STATNAME(I) = DATASTR
        IF(DEBUG.GT.0) THEN
          WRITE(LU,*) 'XY ',I, &
                TCDAT(IFILE)%XHISTOUT(I),TCDAT(IFILE)%YHISTOUT(I), &
                TCDAT(IFILE)%STATOUT(I)
        ENDIF
      ENDDO

      ! File might be read multiple times, so do not close.

!----------------------------------------------------------------------
      ! Prepare interpolation

      CALL INTERP_POINT_PREPARE(TCDAT(IFILE)%XHISTOUT, &
           TCDAT(IFILE)%YHISTOUT,TCDAT(IFILE)%NRPOINT,INTDAT(IFILE), &
           INTERP_METHOD,MESH2D)

      ! Determine which points to consider
      INTDAT(IFILE)%MASKARR = INTDAT(IFILE)%POINTLIST(:,1).NE.0
      LOCDAT(IFILE)%NRCELLLOC = COUNT(INTDAT(IFILE)%MASKARR)
      NRCELLLOC = LOCDAT(IFILE)%NRCELLLOC
      IF(DEBUG.GT.0) THEN
        WRITE(LU,*) INTDAT(IFILE)%MASKARR
      ENDIF

      ! Check the total number of points
      NRCOOR = TCDAT(IFILE)%NRPOINT
      IF(NCSIZE.GT.1) THEN
        NRCOORGLB = P_SUM(NRCELLLOC)
      ELSE
        NRCOORGLB = NRCELLLOC
      ENDIF
      IF(NRCOORGLB.LT.NRCOOR) THEN
        WRITE (LU,*) 'WARNING! ',NRCOOR-NRCOORGLB, &
             ' OUTPUT POINTS ARE OUTSIDE THE MODEL DOMAIN.'
        WRITE (LU,*) 'NO HISTORY FILE WILL BE GENERATED FOR THESE POINTS.'
      ENDIF

      ! Look for point numbers in parallel (to use in gretel afterward)
#if defined (HAVE_MPI)
      IF(NCSIZE.GT.1) THEN
        ALLOCATE(NPOIN_GLB(NCSIZE),STAT=IERR)
        CALL CHECK_ALLOCATE(IERR,'OUT_HIST::NPOIN_GLB')
        CALL MPI_ALLGATHER(NRCELLLOC,1,MPI_INTEGER,NPOIN_GLB,1,  &
                           MPI_INTEGER,COMM,IERR)
      ENDIF
#endif
!     No more action is needed in case there are no points on this
!     processor
      IF(NRCELLLOC.EQ.0) THEN
        !Deallocate global point list
        IF(NCSIZE.GT.1) THEN
          DEALLOCATE(NPOIN_GLB,STAT=IERR)
        ENDIF
        RETURN
      ENDIF

      ! ALLOCATE DATA
      ALLOCATE(LOCDAT(IFILE)%STATOUT(NRCELLLOC*NPLAN),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::LOCDAT.INDEX')
      LOCDAT(IFILE)%STATOUT = 0
      ALLOCATE(LOCDAT(IFILE)%X(NRCELLLOC*NPLAN),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::LOCDAT.X')
      LOCDAT(IFILE)%X = 0.D0
      ALLOCATE(LOCDAT(IFILE)%Y(NRCELLLOC*NPLAN),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::LOCDAT.Y')
      LOCDAT(IFILE)%Y = 0.D0
      ALLOCATE(LOCDAT(IFILE)%DATAARR(NRCELLLOC*NPLAN),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::LOCDAT.DATAARR')
      LOCDAT(IFILE)%DATAARR = 0.D0
      ALLOCATE(LOCDAT(IFILE)%INDEX(NRCELLLOC*NPLAN),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'OUT_HIST::LOCDAT.INDEX')
      LOCDAT(IFILE)%INDEX = 0

!-----------------------------------------------------------------------

      ! Copy id of the data point to local id.
      ! This will be written in IKLE
      CALL COPY_ARR_INT(TCDAT(IFILE)%STATOUT,LOCDAT(IFILE)%STATOUT, &
     &                  INTDAT(IFILE)%MASKARR,NPLAN)
      ! Copy x and y coordinates
      CALL COPY_ARR(TCDAT(IFILE)%XHISTOUT,LOCDAT(IFILE)%X, &
     &              INTDAT(IFILE)%MASKARR,NPLAN)
      CALL COPY_ARR(TCDAT(IFILE)%YHISTOUT,LOCDAT(IFILE)%Y, &
     &              INTDAT(IFILE)%MASKARR,NPLAN)
      ! Copy index (used for parallel merging)
      CALL COPY_ARR_INT(TCDAT(IFILE)%INDEX,LOCDAT(IFILE)%INDEX, &
     &                  INTDAT(IFILE)%MASKARR,NPLAN,.TRUE.)

!----------------------------------------------------------------------

      ! Open file for writing
       CALL OUTHIST_MAKE_FILE(OUTFILE,MAXVAR,IFILE,SORG2D,TEXTE, &
     &                        NRCELLLOC*NPLAN,LOCDAT(IFILE),NPLAN,DATE, &
     &                        TIME,MESH2D%X_ORIG,MESH2D%Y_ORIG,IERR)
      ! Initialize the time step
      HISTDAT(IFILE)%HISTSTEP = 0

      ! Deallocate global point list
      IF(NCSIZE.GT.1) THEN
        DEALLOCATE(NPOIN_GLB,STAT=IERR)
      ENDIF
!
!-----------------------------------------------------------------------
!
      END SUBROUTINE OUTHIST_PREPARE

!                   ******************
                    SUBROUTINE OUTHIST &
!                   ******************
!
      (MODNAME,OUTFILE,TIME,NPOIN2,NPLAN,MAXVAR,SORGND,VARSOR)
!
!***********************************************************************
! BIEF
!***********************************************************************
!
!>@brief    Writes history data to a file
!+
!+   Steps: Interpolate data
!+          Write data
!+
!
!history WA BREUGEM (IMDC)
!+        1-9-2020
!+
!+
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@ param[in]   MODNAME   Name of the calling module
!>@ param[in]   OUTFILE   Structure with data of the output file
!>@ param[in]   TIME      Time (in seconds since the reference time) of
!                         the current time step
!>@ param[in]   NPOIN2    Number of 2D points
!>@ param[in]   NPLAN     Number of vertical planes
!>@ param[in]   MAXVAR    Maximum number of variables
!>@ param[in]   SORGND    Mask specifying which variable to write
!>@ param[in]   VARSOR    Data of the variables for output
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      CHARACTER(LEN=6), INTENT(IN) :: MODNAME
      TYPE(BIEF_FILE), INTENT(IN)  :: OUTFILE
      DOUBLE PRECISION, INTENT(IN) :: TIME
      INTEGER, INTENT(IN) :: MAXVAR
      INTEGER, INTENT(IN) :: NPOIN2,NPLAN
      LOGICAL, INTENT(IN) :: SORGND(MAXVAR)
      TYPE(BIEF_OBJ), INTENT(IN) :: VARSOR
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER IFILE,I,IERR,IPLAN,IVAR,NRCELLLOC,NRPOINT,HISTSTEP
      DOUBLE PRECISION, POINTER, DIMENSION(:) :: TMPDAT, OUTDAT
      LOGICAL LEO
!
!-----------------------------------------------------------------------
!
      ! Find the right module
      IF(NRFILE.EQ.0) THEN
        RETURN
      ENDIF
      DO IFILE=1,NRFILE
        IF(MODULE_LIST(IFILE)(1:6).EQ.MODNAME(1:6)) THEN
          EXIT
        ENDIF
        IF(IFILE.EQ.NRFILE) THEN
          ! No file for this module
          RETURN
        ENDIF
      ENDDO

      ! Make sure the right output period is there
      CALL HISTPERIOD (MODNAME,TIME,LEO)
      IF(.NOT.LEO) THEN
        RETURN
      ENDIF
      NRCELLLOC = LOCDAT(IFILE)%NRCELLLOC
      IF(NRCELLLOC.EQ.0) THEN
        RETURN
      ENDIF
      HISTSTEP = HISTDAT(IFILE)%HISTSTEP

      NRPOINT = TCDAT(IFILE)%NRPOINT

      ! Interpolate and write history data
      IVAR = 0
      DO I=1,MAXVAR
        IF(SORGND(I)) THEN
          IVAR = IVAR +1
          LOCDAT(IFILE)%DATAARR = 0.D0
          ! Interpolation of 2-d variables
          DO IPLAN=1,NPLAN
            TMPDAT => VARSOR%ADR(I)%P%R((IPLAN-1)*NPOIN2+1:IPLAN*NPOIN2)
            OUTDAT => LOCDAT(IFILE)%DATAARR((IPLAN-1)*NRCELLLOC+1:IPLAN*NRCELLLOC)
            CALL INTERP_POINT(INTDAT(IFILE),NRPOINT,TMPDAT,OUTDAT, &
                              NRCELLLOC)
          ENDDO
          ! Add data to file
          CALL ADD_DATA(OUTFILE%FMT,OUTFILE%LU, &
                        HISTDAT(IFILE)%VARNAME(IVAR),TIME, &
                        HISTDAT(IFILE)%HISTSTEP,IVAR.EQ.1, &
                        LOCDAT(IFILE)%DATAARR,NRCELLLOC*NPLAN,IERR)
          CALL CHECK_CALL(IERR,'OUT_HIST:ADD_DATA')
        ENDIF
      ENDDO
      ! Update counter for the time step in the file
      HISTDAT(IFILE)%HISTSTEP = HISTDAT(IFILE)%HISTSTEP + 1
!
!-----------------------------------------------------------------------
!
      RETURN
      END SUBROUTINE OUTHIST

!                   **********************
                    SUBROUTINE OUTHIST_END
!                   **********************
!
!
!***********************************************************************
! BIEF
!***********************************************************************
!
!>@brief    Resets the module for writing history files and cleans all
!           memory
!
!history WA BREUGEM (IMDC)
!+        1/09/2020
!+
!+
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER I,IERR
!
!-----------------------------------------------------------------------
!
! Reset default values
      IF(IS_CLEAN) THEN
        RETURN
      ENDIF
      IS_CLEAN = .TRUE.
      IS_INIT  = .FALSE.

! Deallocate arrays
      DO I=1,NRFILE
        DEALLOCATE(INTDAT(I)%WEIGHTS)
        DEALLOCATE(INTDAT(I)%POINTLIST)
        DEALLOCATE(INTDAT(I)%MASKARR)

        IF(LOCDAT(I)%NRCELLLOC.GT.0) THEN
          DEALLOCATE(LOCDAT(I)%STATOUT)
          DEALLOCATE(LOCDAT(I)%X)
          DEALLOCATE(LOCDAT(I)%Y)
          DEALLOCATE(LOCDAT(I)%DATAARR)
        ENDIF

        DEALLOCATE(TCDAT(I)%STATNAME)
        DEALLOCATE(TCDAT(I)%STATOUT)
        DEALLOCATE(TCDAT(I)%XHISTOUT)
        DEALLOCATE(TCDAT(I)%YHISTOUT)
        DEALLOCATE(TCDAT(I)%THISTSTART)
        DEALLOCATE(TCDAT(I)%THISTEND)
        DEALLOCATE(TCDAT(I)%DTHIST)

        IF(LOCDAT(I)%NRCELLLOC.GT.0) THEN
          DEALLOCATE(HISTDAT(I)%VARNAME)
        ENDIF
      ENDDO
      DEALLOCATE(INTDAT,STAT=IERR)
      DEALLOCATE(TCDAT,STAT=IERR)
      DEALLOCATE(LOCDAT,STAT=IERR)
      DEALLOCATE(HISTDAT,STAT=IERR)
      DEALLOCATE(LEO_PER_FILE)
      DEALLOCATE(MODULE_LIST)

      ! Reset the number of files
      NRFILE = 0
!
!-----------------------------------------------------------------------
!
      RETURN
      END SUBROUTINE OUTHIST_END

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!                         COPY ROUTINES
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

!                   *******************
                    SUBROUTINE COPY_ARR &
!                   *******************
!
      (DATAIN,DATAOUT,MASKARR,NRCOPY)
!
!***********************************************************************
! BIEF
!***********************************************************************
!
!>@brief    Copies data to an array, eliminating masks
!
!history WA BREUGEM (IMDC)
!+        1/09/2020
!+
!+
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in]     DATAIN  Input data
!>@param[in,out] DATAOUT Output data
!>@param[in]     MAKSARR Mask to apply to the data
!>@param[in]     NRCOPY  Number of copies that need to be made of the
!                        data
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      DOUBLE PRECISION, DIMENSION(:), INTENT(IN) :: DATAIN
      DOUBLE PRECISION, DIMENSION(:), INTENT(INOUT) :: DATAOUT
      LOGICAL, DIMENSION(:),INTENT(IN) :: MASKARR
      INTEGER, INTENT(IN) :: NRCOPY
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER I,J,N
!
!-----------------------------------------------------------------------
!
      N = 1
      DO J=1,NRCOPY
        DO I=1,SIZE(DATAIN)
          IF(MASKARR(I)) THEN
            DATAOUT(N) = DATAIN(I)
            N = N + 1
          ENDIF
        ENDDO
      ENDDO
!
!-----------------------------------------------------------------------
!
      RETURN
      END SUBROUTINE COPY_ARR

!                   ***********************
                    SUBROUTINE COPY_ARR_INT &
!                   ***********************
!
      (DATAIN,DATAOUT,MASKARR,NRCOPY,IS3D)
!
!***********************************************************************
! BIEF
!***********************************************************************
!
!>@brief    Copies data to an array, eliminating masks
!
!history WA BREUGEM (IMDC)
!+        1/09/2020
!+
!+
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in]     DATAIN  Input data
!>@param[in,out] DATAOUT Output data
!>@param[in]     MAKSARR Mask to apply to the data
!>@param[in]     NRCOPY  Number fo copies that need to be made of the
!                        data
!>@param[in]     IS3D (optional) If true, each layer gets a new number
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER, DIMENSION(:), INTENT(IN) :: DATAIN
      INTEGER, DIMENSION(:), INTENT(INOUT) :: DATAOUT
      LOGICAL, DIMENSION(:), INTENT(IN) :: MASKARR
      INTEGER, INTENT(IN) :: NRCOPY
      LOGICAL, OPTIONAL, INTENT(IN) :: IS3D
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER I,N,J,NPOIN,NRADD
!
!-----------------------------------------------------------------------
!
      N = 1
      NPOIN = SIZE(DATAIN)
      NRADD = 0
      IF(PRESENT(IS3D)) THEN
        IF(IS3D) THEN
          NRADD = NPOIN
        ENDIF
      ENDIF
      DO J=1,NRCOPY
        DO I=1,NPOIN
          IF(MASKARR(I)) THEN
            DATAOUT(N) = DATAIN(I)+ (J-1)*NRADD
            N = N + 1
          ENDIF
        ENDDO
      ENDDO
!
!-----------------------------------------------------------------------
!
      RETURN
      END SUBROUTINE COPY_ARR_INT

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!                         INTERPOLATION ROUTINES
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

!                   *******************************
                    SUBROUTINE INTERP_POINT_PREPARE &
!                   *******************************
!
     (XINT,YINT,NPINT,INTVAR,INTERP_METHOD,MESH2D)
!
!***********************************************************************
! BIEF
!***********************************************************************
!
!>@brief    Determines weight factors for interpolation
!
!           Note: May be slow for large number of output points
!
!history WA BREUGEM (IMDC)
!+        1/09/2020
!+
!+
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in]      XINT   X coordinates to interpolate
!>@param[in]      YINT   Y coordinates to interpolate
!>@param[in]      NPINT  Number of points to interpolate
!>@param[in]      XINT   Structure with coordinates to use
!>@param[in,out]  INTVAR Structure with data for interpolation
!>@param[in]      INTERP_METHOD 1 if linear interpolation, 0 if nearest
!                               neighbour interpolation 
!>@param[in]      MESH2D Structure with the 2d mesh
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER, INTENT(IN) :: NPINT
      DOUBLE PRECISION, INTENT(IN) :: XINT(NPINT),YINT(NPINT)
      TYPE(INTERPDATA), INTENT(INOUT) :: INTVAR

      INTEGER, INTENT(IN) :: INTERP_METHOD
      TYPE(BIEF_MESH), INTENT(IN) :: MESH2D
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER I,J,J2,J3

      LOGICAL INTRI
      DOUBLE PRECISION XP,YP,W1,W2,W3,W
      DOUBLE PRECISION, DIMENSION(3) :: XTRI,YTRI
      INTEGER, POINTER, DIMENSION(:) :: IKLE2
      INTEGER NELEM2
!
!-----------------------------------------------------------------------
!
      ! Preparxation
      NELEM2 = MESH2D%NELEM
      IKLE2=>MESH2D%IKLE%I
      INTVAR%POINTLIST  = 0
      INTVAR%WEIGHTS = 0.D0

! Loop over all points that need to interpolated

      DO I=1,NPINT

        XP = XINT(I)
        YP = YINT(I)
        ! Loop over all elements in the mesh
        DO J=1,NELEM2
          J2 = J + NELEM2
          J3 = J + 2*NELEM2

          ! Get coordinates of the triangle
          XTRI(1) = MESH2D%X%R(IKLE2(J))
          XTRI(2) = MESH2D%X%R(IKLE2(J2))
          XTRI(3) = MESH2D%X%R(IKLE2(J3))
          YTRI(1) = MESH2D%Y%R(IKLE2(J))
          YTRI(2) = MESH2D%Y%R(IKLE2(J2))
          YTRI(3) = MESH2D%Y%R(IKLE2(J3))

          ! Check if a point is in a trinagle
          CALL IN_TRIANGLE(XP,YP,XTRI,YTRI,INTRI)

          IF(INTRI) THEN
            ! Store points
            INTVAR%POINTLIST(I,1) = IKLE2(J)
            INTVAR%POINTLIST(I,2) = IKLE2(J2)
            INTVAR%POINTLIST(I,3) = IKLE2(J3)
            ! Determine weights for linear interpolation
            ! Area  p-2-3
            XTRI(1) = XP
            YTRI(1) = YP
            CALL TRI_AREA(XTRI,YTRI,W1)
            !Area p-1-3: point
            XTRI(2) = MESH2D%X%R(IKLE2(J))
            YTRI(2) = MESH2D%Y%R(IKLE2(J))
            CALL TRI_AREA(XTRI,YTRI,W2)
            !Area p-1-2: point
            XTRI(3) = MESH2D%X%R(IKLE2(J2))
            YTRI(3) = MESH2D%Y%R(IKLE2(J2))
            CALL TRI_AREA(XTRI,YTRI,W3)
            W = W1 + W2 + W3

            IF(INTERP_METHOD.EQ.1) THEN
!             Linear interpolation
              INTVAR%WEIGHTS (I,1) = W1/W
              INTVAR%WEIGHTS (I,2) = W2/W
              INTVAR%WEIGHTS (I,3) = W3/W
            ELSE
              ! Nearest neighbour
              IF((W1.GE.W2).AND.(W1.GE.W3)) THEN
                INTVAR%WEIGHTS (I,1) = 1.D0
              ENDIF
              IF((W2.GE.W1).AND.(W2.GE.W3)) THEN
                INTVAR%WEIGHTS (I,2) = 1.D0
              ENDIF
              IF((W3.GE.W2).AND.(W3.GE.W1)) THEN
                INTVAR%WEIGHTS (I,3) = 1.D0
              ENDIF
            ENDIF
            ! Continue to next point of the list
            EXIT
          ENDIF
        ENDDO
      ENDDO
!
!-----------------------------------------------------------------------
!
      RETURN
      END SUBROUTINE INTERP_POINT_PREPARE

!                   ***********************
                    SUBROUTINE INTERP_POINT &
!                   ***********************
!
      (INTVAR,NRPOINTS,DATA_IN,DATA_OUT,OUT_SIZE)
!
!***********************************************************************
! BIEF
!***********************************************************************
!
!>@brief    Interpolates data by applying the weight factors determined
!           earlier
!
!history WA BREUGEM (IMDC)
!+        1/09/2020
!+
!+
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in]      DATA_IN  Data to interpolate
!>@param[in]      INTVAR   Structure with data for interpolation
!>@param[in,out]  DATA_OUT Interpolated data
!>@param[in]      OUT_SIZE Size of the output data
!>@param[in]      NRPOINTS Size of the input data
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      TYPE(INTERPDATA), INTENT(IN) :: INTVAR
      INTEGER, INTENT(IN) :: NRPOINTS,OUT_SIZE
      DOUBLE PRECISION, DIMENSION(:), INTENT(IN) :: DATA_IN
      DOUBLE PRECISION, DIMENSION(OUT_SIZE), INTENT(INOUT):: DATA_OUT
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER I,I1,I2,I3
      DOUBLE PRECISION, DIMENSION(NRPOINTS) :: TEMP_ARR
!
!-----------------------------------------------------------------------
!
      DATA_OUT = 0.D0

      ! Loop over all coordinates
      DO I=1,NRPOINTS
        I1 = INTVAR%POINTLIST(I,1)
        I2 = INTVAR%POINTLIST(I,2)
        I3 = INTVAR%POINTLIST(I,3)

        ! Check for valid point
        IF(I1.GT.0 .AND. I2.GT.0 .AND. I3.GT.0) THEN
        ! Perform interpolation by matrix vector product
          TEMP_ARR(I) = INTVAR%WEIGHTS(I,1)*DATA_IN(I1) +  &
                        INTVAR%WEIGHTS(I,2)*DATA_IN(I2) +  &
                        INTVAR%WEIGHTS(I,3)*DATA_IN(I3)
        ENDIF
      ENDDO
      ! Copy data to right array
      CALL COPY_ARR(TEMP_ARR,DATA_OUT,INTVAR%MASKARR,1)
!
!-----------------------------------------------------------------------
!
      RETURN
      END SUBROUTINE INTERP_POINT

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!                        TRIANGLE ROUTINES
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

!                   **********************
                    SUBROUTINE IN_TRIANGLE &
!                   **********************
!
      (XP,YP,XTRI,YTRI,INTRI)
!
!***********************************************************************
! BIEF
!***********************************************************************
!
!>@brief    Checks if a point is inside a triangle
!
!          Reference: http://www.blackpawn.com/texts/pointinpoly/
!
!history WA BREUGEM (IMDC)
!+        1/09/2020
!+
!+
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in]     XP    x-coordinates of the point
!>@param[in]     YP    y-coordinates of the point
!>@param[in]     XTRI  x-coordinates of the triangle
!>@param[in]     YTRI  y-coordinates of the triangle
!>@param[in,out] INTRI true if the point is in a triangle
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      DOUBLE PRECISION, INTENT(IN) :: XP,YP
      DOUBLE PRECISION, INTENT(IN), DIMENSION(3) :: XTRI,YTRI
      LOGICAL, INTENT(INOUT) :: INTRI
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      DOUBLE PRECISION, DIMENSION(2) :: V0,V1,V2
      DOUBLE PRECISION DOT00,DOT01,DOT02,DOT11,DOT12,INV_DENOM,U,V
!
!-----------------------------------------------------------------------
!
!     Compute vectors
      V0(1) =  XTRI(3) - XTRI(1)
      V0(2) =  YTRI(3) - YTRI(1)
      V1(1) =  XTRI(2) - XTRI(1)
      V1(2) =  YTRI(2) - YTRI(1)
      V2(1) =  XP - XTRI(1)
      V2(2) =  YP - YTRI(1)

!     Compute dot products
      DOT00 = DOT_PRODUCT(V0,V0)
      DOT01 = DOT_PRODUCT(V0,V1)
      DOT02 = DOT_PRODUCT(V0,V2)
      DOT11 = DOT_PRODUCT(V1,V1)
      DOT12 = DOT_PRODUCT(V1,V2)

!     Compute barycentric coordinates
      INV_DENOM = 1.D0 / (DOT00 * DOT11 - DOT01 * DOT01)
      U = (DOT11 * DOT02 - DOT01 * DOT12) * INV_DENOM
      V = (DOT00 * DOT12 - DOT01 * DOT02) * INV_DENOM

!     Check if point is in the triangle
      INTRI = (U.GE.0.D0).AND.(V.GE.0.D0).AND.(U+V.LE.1.D0)
!
!-----------------------------------------------------------------------
!
      RETURN
      END SUBROUTINE IN_TRIANGLE

!                   *******************
                    SUBROUTINE TRI_AREA &
!                   *******************
!
      (XTRI,YTRI,AREA)
!
!***********************************************************************
! BIEF
!***********************************************************************
!
!>@brief    Computes the area of a triangle
!
!history WA BREUGEM (IMDC)
!+        1/09/2020
!+
!+
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in,out] XTRI x-coordinates of the triangle
!>@param[in]     YTRI y-coordinates of the triangle
!>@param[in]     AREA area of the triangle
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      DOUBLE PRECISION, INTENT(IN), DIMENSION(3) :: XTRI,YTRI
      DOUBLE PRECISION, INTENT(INOUT) :: AREA
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      DOUBLE PRECISION P1,P2
!
!-----------------------------------------------------------------------
!
      P1 = (XTRI(1)-XTRI(3))*(YTRI(2)-YTRI(1))
      P2 = (XTRI(1)-XTRI(2))*(YTRI(3)-YTRI(1))
      AREA = 0.5D0*ABS(P1-P2)
!
!-----------------------------------------------------------------------
!
      RETURN
      END SUBROUTINE TRI_AREA

      END MODULE OUT_HISTORY
