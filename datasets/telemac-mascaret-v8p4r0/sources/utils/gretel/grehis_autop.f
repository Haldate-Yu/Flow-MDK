!                   ********************
                    PROGRAM GREHIS_AUTOP
!                   ********************
!
!
!***********************************************************************
! PARALLEL   V8P5
!***********************************************************************
!
!brief    MERGES THE TIME SERIES OF A PARALLEL COMPUTATION
!+                TO WRITE A SINGLE FILE IN A GIVEN FORMAT.
!
!
!
!history W.A. Breugem (IMDC)
!+        19/11/2022
!+
!+   Creation from gretel_autop to add merging of time series files.
!
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in] GEO Name of the geometry file
!>@param[in,out] GEOFORMAT Format of the geometry file
!>@param[in] BND Name of the boudnary file
!>@param[in] RES Name of the result file
!>@param[in,out] RESFORMAT Format of the result file
!>@param[in] NPROC Number of processors
!>@param[in] NPLAN_RES Number of planes for the result file
!>@param[in] METHOD method for merging data information:
!!                  1: No more dans npoin*nvar in memory loop on time
!!                  2: Max memory npoin*nvar*ntimestep loop on files
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE INTERFACE_HERMES
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_PARTEL, ONLY: MAXNPROC
!
      IMPLICIT NONE
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
!
      LOGICAL IS
      CHARACTER(LEN=PATH_LEN) :: GEO
      CHARACTER(LEN=PATH_LEN) :: BND
      CHARACTER(LEN=8)   :: GEOFORMAT,RESFORMAT
      CHARACTER(LEN=PATH_LEN) :: RES
      INTEGER            :: NPROC, NPLAN_RES, METHOD
!
!-------------------------------------------------------------------------
!
      INTEGER IPID
      INTEGER I,J,IELEM
      INTEGER NPLAN_GEO,NELEM_GEO,NDP,NPTFR, NPTIR
      INTEGER :: NDIM
!
      INTEGER, DIMENSION(:)  , ALLOCATABLE :: IPOBO_GEO
      INTEGER, DIMENSION(:), ALLOCATABLE :: KNOLG, TMP2
      INTEGER, DIMENSION(:), ALLOCATABLE :: IKLE_GEO
!
      DOUBLE PRECISION, DIMENSION(:), ALLOCATABLE :: TMP,X,Y
!
      CHARACTER(LEN=300) :: RESPAR
!
      CHARACTER(LEN=80) TITSEL
      CHARACTER(LEN=32),ALLOCATABLE :: TEXTELU(:)
      CHARACTER(LEN=16),ALLOCATABLE :: VAR_NAME(:), VAR_UNIT(:)
      CHARACTER(LEN=11) EXTENS
      EXTERNAL  EXTENS
!
      INTEGER IERR,NRES,NRESPAR,TYP_ELEM,TYP_BND_ELEM
      INTEGER DATE(3),TIME(3)
      INTEGER NTIMESTEP_RES,NPOIN_GEO,NPOIN_RES,NPOIN_PAR,NVAR_RES
      INTEGER DATE_TMP(6)

! For history files
      INTEGER NELEM_PAR,FIRST_FILE
      !Note that 64-bit integer is needed, otherwise problems exist for files larger than 2.1Gb
      INTEGER(KIND=8) :: RESPAR_SIZE
      INTEGER RES_ELEM,RES_NDP
      LOGICAL RESPAR_EXIST
      INTEGER, ALLOCATABLE, DIMENSION(:) :: RESPAR_NPOIN, IKLE_PAR
      LOGICAL, ALLOCATABLE, DIMENSION(:) :: USE_RESPAR
!
!-------------------------------------------------------------------------
!
      LI=5
      LU=6
      LNG=2
!
!-------------------------------------------------------------------------
!
!
!----------------------------------------------------------------------
! INTRODUCE YOURSELF
!
      WRITE(LU,*) ' '
      WRITE(LU,*) '+-------------------------------------------------+'
      WRITE(LU,*) '  I AM GREHIS, COUSIN OF GRETEL FROM BAW HAMBURG'
      WRITE(LU,*) '  FOR TIME SERIES FILE'
      WRITE(LU,*) '+-------------------------------------------------+'
      WRITE(LU,*) ' '
      WRITE(LU,*) '  MAXIMUM NUMBER OF PARTITIONS: ',MAXNPROC
      WRITE(LU,*) ' '
      WRITE(LU,*) '+--------------------------------------------------+'
      WRITE(LU,*) ' '
!
      WRITE (LU,*) '--GLOBAL GEOMETRY FILE: '
      READ(LI,*) GEO
!
      IF (GEO.EQ.' ') THEN
        WRITE (LU,*) ' NO FILENAME '
        CALL PLANTE(1)
        STOP
      ELSE
        WRITE(LU,*) 'INPUT: ',TRIM(GEO)
      ENDIF

      INQUIRE (FILE=GEO,EXIST=IS)
      IF (.NOT.IS) THEN
        WRITE (LU,*)' FILE DOES NOT EXIST: ',TRIM(GEO)
        CALL PLANTE(1)
        STOP
      ENDIF
!
      WRITE(LU,*)
     & '--GEOMETRY FILE FORMAT <FFORMAT> [MED,SERAFIN,SERAFIND]: '
      READ(LI,*) GEOFORMAT
      IF ( (GEOFORMAT .NE. 'MED     ') .AND.
     &     (GEOFORMAT(1:7) .NE. 'SERAFIN') ) THEN
        WRITE(LU,*)
     &  ' FILE FORMAT MUST BE "MED" OR "SERAFIN" OR "SERAFIND" '
        CALL PLANTE(1)
        STOP
      ELSE
        WRITE(LU,*) ' INPUT: ', GEOFORMAT
      ENDIF
!
      WRITE (LU,*) '--GLOBAL BOUNDARY FILE: '
      READ(LI,*) BND
!
      IF (BND.EQ.' ') THEN
        WRITE (LU,*) ' NO FILENAME '
        CALL PLANTE(1)
        STOP
      ELSE
        WRITE(LU,*) 'INPUT: ',TRIM(BND)
      ENDIF

      INQUIRE (FILE=BND,EXIST=IS)
      IF (.NOT.IS) THEN
        WRITE (LU,*)' FILE DOES NOT EXIST: ',TRIM(BND)
        CALL PLANTE(1)
        STOP
      ENDIF
!
      WRITE(LU,*) '--RESULT FILE: '
      READ(LI,*) RES
!
      IF (RES.EQ.' ') THEN
        WRITE (LU,*) ' NO FILENAME '
        CALL PLANTE(1)
        STOP
      ELSE
        WRITE(LU,*) 'INPUT: ',TRIM(RES)
      ENDIF
!
      WRITE(LU,*)
     & '--RESULT FILE FORMAT <FFORMAT> [MED,SERAFIN,SERAFIND]: '
      READ(LI,*) RESFORMAT
      IF ( (RESFORMAT .NE. 'MED     ') .AND.
     &     (RESFORMAT(1:7) .NE. 'SERAFIN') ) THEN
        WRITE(LU,*)
     &  ' FILE FORMAT MUST BE "MED" OR "SERAFIN" OR "SERAFIND" '
        CALL PLANTE(1)
        STOP
      ELSE
        WRITE(LU,*) ' INPUT: ', RESFORMAT
      ENDIF
!
      WRITE(LU,FMT='(A,I6,A)')
     &  '--NUMBER OF PARTITIONS <NPARTS> [2 -',MAXNPROC,']: '
      READ(LI,*) NPROC
!
      IF ( (NPROC > MAXNPROC) .OR. (NPROC < 2) ) THEN
        WRITE(LU,FMT='(A,I6,A)')
     &  ' NUMBER OF PARTITIONS MUST BE IN [2 -',MAXNPROC,']'
        CALL PLANTE(1)
        STOP
      ELSE
        WRITE(LU,*)' INPUT: ', NPROC
      ENDIF
!
      WRITE (LU,*) '--NUMBER OF PLANES: '
      READ (LI,*) NPLAN_RES
      WRITE (LU,*) ' INPUT: ',NPLAN_RES

      WRITE (LU,*) '--METHOD (1: min memory, 2:max memory): '
      READ (LI,*) METHOD
      WRITE (LU,*) ' INPUT: ',METHOD
!
!-------------------------------------------------------------------------
!
!
!|==================================================================|
!|                                                                  |
!| START: MERGES FILES RESULTING FROM THE DOMAIN DECOMPOSITION      |
!|                                                                  |
!|==================================================================|
!
! READS FILE NAMES AND THE NUMBER OF PROCESSORS / PARTITIONS
!
!
!      Find empty files (or non existing files)
!
      ALLOCATE(USE_RESPAR(NPROC),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'GREHIS:USE_RESPAR')
      DO I = 0,NPROC-1
        RESPAR = TRIM(RES) // EXTENS(NPROC-1,I)
        INQUIRE(FILE=RESPAR,EXIST=RESPAR_EXIST)
        IF(RESPAR_EXIST) THEN
          INQUIRE(FILE=RESPAR,SIZE=RESPAR_SIZE)
          IF(RESPAR_SIZE.GT.0) THEN
            USE_RESPAR(I+1) = .TRUE.
          ELSE
            USE_RESPAR(I+1) = .FALSE.
          ENDIF
        ELSE
          USE_RESPAR(I+1) = .FALSE.
        ENDIF
      ENDDO
!
!    Find master file to open first
!
      FIRST_FILE = -1
      DO I = 1,NPROC
        IF(USE_RESPAR(I)) THEN
          FIRST_FILE = I-1
          EXIT
        ENDIF
      ENDDO
      IF(FIRST_FILE.EQ.-1) THEN
        WRITE(LU,*) 'ALL FILES ARE EMPTY FOR  ', RES
        CALL PLANTE(1)
      ENDIF

!
!     Header information
!
      RESPAR = TRIM(RES) // EXTENS(NPROC-1,FIRST_FILE)
      CALL OPEN_MESH(RESFORMAT,RESPAR,NRESPAR,'READ     ',IERR)
      CALL CHECK_CALL(IERR,"GREHIS:OPEN_MESH:RESPAR")
!     Opening result file after so that it will be the same endianess as
!     the partitionned result files
      CALL OPEN_MESH(RESFORMAT,RES,NRES,'WRITE    ',IERR)
      CALL CHECK_CALL(IERR,"GREHIS:OPEN_MESH:RES")
!
      ! Get the mesh title
      CALL GET_MESH_TITLE(RESFORMAT,NRESPAR,TITSEL,IERR)
      CALL CHECK_CALL(IERR,"GREHIS:GET_MESH_TITLE")

!     Get the number of variable
      CALL GET_DATA_NVAR(RESFORMAT,NRESPAR,NVAR_RES,IERR)
      CALL CHECK_CALL(IERR,"GREHIS:GET_DATA_NVAR")
!
      ALLOCATE(TEXTELU(NVAR_RES),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'GREHIS:TEXTELU')
      ALLOCATE(VAR_NAME(NVAR_RES),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'GREHIS:VAR_NAME')
      ALLOCATE(VAR_UNIT(NVAR_RES),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'GREHIS:VAR_UNIT')
!
      CALL GET_DATA_VAR_LIST(RESFORMAT,NRESPAR,NVAR_RES,VAR_NAME,
     &                       VAR_UNIT,IERR)
      CALL CHECK_CALL(IERR,"GREHIS:GET_DATA_VAR_LIST")
!
      WRITE(LU,*) 'TITLE=',TITSEL
      WRITE(LU,*) 'NBVAR=',NVAR_RES
      DO I=1,NVAR_RES
        TEXTELU(I)(1:16) = VAR_NAME(I)
        TEXTELU(I)(17:32) = VAR_UNIT(I)
        WRITE(LU,*) 'VARIABLE ',I,' : ',TEXTELU(I)
      ENDDO ! I
!
      DEALLOCATE(VAR_NAME)
      DEALLOCATE(VAR_UNIT)
!
!     We need to get the number of planes in the partitionned file
!     To know if we need to tranform the geometry in 3d geometry
      CALL GET_MESH_NPLAN(RESFORMAT,NRESPAR,NPLAN_RES,IERR)
      CALL CHECK_CALL(IERR,"GREHIS:MESH_NPLAN")
!
!     Get the number of timestep
      CALL GET_DATA_NTIMESTEP(RESFORMAT,NRESPAR,NTIMESTEP_RES,IERR)
      CALL CHECK_CALL(IERR,"GREHIS:GET_DATA_NTIMESTEP")

      !Get the dimensions of the results (because of a separate treatment of history files
      !Work-around because HERMES only returns 2 or 3 for the dimension
      !So we look for elements with one point per element, to know we have history files
      RES_ELEM = POINT_ELT_TYPE
      CALL GET_MESH_NPOIN_PER_ELEMENT(RESFORMAT,NRESPAR,
     &                                RES_ELEM,RES_NDP,IERR)
      CALL CHECK_CALL(IERR,"GREHIS:GET_MESH_NPOIN_PER_ELEMENT")
      CALL CLOSE_MESH(RESFORMAT,NRESPAR,IERR)
      CALL CHECK_CALL(IERR,"GREHIS:CLOSE_MESH:RESPAR")

      CALL SET_HEADER(RESFORMAT,NRES,TITSEL,NVAR_RES,TEXTELU,IERR)

!---------------------------------------------------------------------
      ! History file
      ! Here we do not have an external mesh
      ! Instead we count the number of points in each output file
      ! Note that files may not exist if there is no output on a specified processor

      ! Note that is is assumed that each point occurs only once in the data
      ! This should be true generally (as it is checked in which element a point is, and elements occur only once
      ! However, there may be exceptions in case a point is exactly of the edge of the domain
      ALLOCATE(RESPAR_NPOIN(NPROC),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'GREHIS::RESPAR_NPOIN')

      DO IPID = 0, NPROC-1
!
        ! Find the number of points in each result file
        !Skip files that do not exist or are empty (happens for history files)
        IF(USE_RESPAR(IPID+1)) THEN
          RESPAR = TRIM(RES) // EXTENS(NPROC-1,IPID)
          CALL OPEN_MESH(RESFORMAT,RESPAR,NRESPAR,'READ     ',
     &                   IERR)
          CALL CHECK_CALL(IERR,"GREHIS:OPEN_MESH:RESPAR2")

          CALL GET_MESH_NPOIN(RESFORMAT,NRESPAR,POINT_ELT_TYPE,
     &                        NPOIN_PAR,IERR)
          CALL CHECK_CALL(IERR,"GREHIS:GET_MESH_NPOIN:RESPAR")

          CALL CLOSE_MESH(RESFORMAT,NRESPAR,IERR)
          CALL CHECK_CALL(IERR,'GREHIS:CLOSEMESH:RESPAR')

          RESPAR_NPOIN(IPID+1) = NPOIN_PAR
        ELSE
          RESPAR_NPOIN(IPID+1) = 0
        ENDIF
      ENDDO

      ! Construct and allocate the global mesh

      NPOIN_GEO = SUM(RESPAR_NPOIN)
      TYP_ELEM  = 1
      NELEM_GEO = NPOIN_GEO
      NPTFR     = NPOIN_GEO
      NPTIR     = 0
      NDP       = 1
      NPLAN_GEO = NPLAN_RES
      IF(NPLAN_RES.LE.1) THEN
        NDIM = 0
      ELSE
        NDIM = 1
      ENDIF

      ALLOCATE(X(NPOIN_GEO),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'GREHIS:X')
      ALLOCATE(Y(NPOIN_GEO),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'GREHIS:Y')
      ALLOCATE(IKLE_GEO(NELEM_GEO*NDP),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'GREHIS:IKLE_GEO')
      ALLOCATE(IPOBO_GEO(NPOIN_GEO),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'GREHIS:IPOBO')
      ! FILL IPOBO WITH USELESS DATA
      DO I=1,NPOIN_GEO
        IPOBO_GEO(I) = I
      ENDDO
      DEALLOCATE(RESPAR_NPOIN)
      
!----------------------------------------------------------------------

      !
      ! Update coordinates with coordinates from the partitioned files
      ! as they could have been modified by corrxy
      DO IPID = 0, NPROC-1
!
        ! Skip files that do not exist or are empty (happens for history files)
        IF(.NOT.USE_RESPAR(IPID+1)) THEN
          CYCLE
        ENDIF

        RESPAR = TRIM(RES) // EXTENS(NPROC-1,IPID)
        CALL OPEN_MESH(RESFORMAT,RESPAR,NRESPAR,'READ     ',IERR)
        CALL CHECK_CALL(IERR,"GREHIS:OPEN_MESH:RESPAR2")
!
        CALL GET_MESH_NPOIN(RESFORMAT,NRESPAR,TYP_ELEM,NPOIN_PAR,IERR)
        CALL CHECK_CALL(IERR,"GREHIS:GET_MESH_NPOIN:RESPAR")
!
        ALLOCATE(KNOLG(NPOIN_PAR),STAT=IERR)
        CALL CHECK_ALLOCATE(IERR,'GREHIS:KNOLG')
        ALLOCATE(TMP(NPOIN_PAR),STAT=IERR)
        CALL CHECK_ALLOCATE(IERR,'GREHIS:TMP')
!
        CALL GET_MESH_L2G_NUMBERING(RESFORMAT,NRESPAR,KNOLG,
     &                              NPOIN_PAR,IERR)
        CALL CHECK_CALL(IERR,'GREHIS:GET_MESH_L2G_NUMBERING:RESPAR')
!
        CALL GET_MESH_COORD(RESFORMAT,NRESPAR,1,NDIM,NPOIN_PAR,TMP,IERR)
        CALL CHECK_CALL(IERR,'GREHIS:GET_MESH_COORD:X:RESPAR')
        ! VERTICAL TREATEMENT IS DIFFERENT FOR HISTORY FILE.
        ! ALL X AND Y COORDINATES ARE COPIED
        DO I=1,NPOIN_PAR
          X(KNOLG(I)) = TMP(I)
        ENDDO
        CALL GET_MESH_COORD(RESFORMAT,NRESPAR,2,NDIM,NPOIN_PAR,TMP,IERR)
        CALL CHECK_CALL(IERR,'GREHIS:GET_MESH_COORD:Y:RESPAR')
        DO I=1,NPOIN_PAR
          Y(KNOLG(I)) = TMP(I)
        ENDDO
        ! For history filea, IKLE contains the station_id. It needs to be copied here
        IF(NDIM.LE.1) THEN
          IF(NDP.NE.1) THEN
            WRITE (LU,*) 'INVALID HISTORY FILE FORMAT. '//
     &                   'NDP SHOULD BE 1.'
            CALL PLANTE(1)
          ENDIF
          NELEM_PAR = NPOIN_PAR
          ALLOCATE(IKLE_PAR(NELEM_PAR),STAT=IERR)
          CALL CHECK_ALLOCATE(IERR,'GREHIS:IKLE_PAR')
          CALL GET_MESH_CONNECTIVITY(RESFORMAT,NRESPAR,POINT_ELT_TYPE,
     &                                  IKLE_PAR,NELEM_PAR,NDP,IERR)
          CALL CHECK_CALL(IERR,'GREHIS:GET_MESH_CONNECTIVITY')

          DO I=1,NELEM_PAR
            IKLE_GEO(KNOLG(I)) = IKLE_PAR(I)
          ENDDO
          DEALLOCATE(IKLE_PAR)
        ENDIF

!----------------------------------------------------------------------
        ! Getting the date from result file
        CALL GET_MESH_DATE(RESFORMAT,NRESPAR,DATE_TMP,IERR)
        CALL CHECK_CALL(IERR,'GREHIS:GET_MESH_DATE;RESPAR')
        DO I=1,3
          DATE(I) = DATE_TMP(I)
          TIME(I) = DATE_TMP(I+3)
        ENDDO
        !
        CALL CLOSE_MESH(RESFORMAT,NRESPAR,IERR)
        CALL CHECK_CALL(IERR,'GREHIS:CLOSEMESH:RESPAR')
        DEALLOCATE(TMP)
        DEALLOCATE(KNOLG)
      ENDDO ! IPID
      
!----------------------------------------------------------------------
      !
      ! If we have a 3d result we need to transform the mesh in 3d
      ! Writes the mesh information to the merged file
      WRITE(LU,*) 'WRITING MESH'
      !Also used for history files
!      IF(NDIM.LE.2) THEN
      ! 2D
      ALLOCATE(TMP2(NELEM_GEO*NDP),STAT=IERR)
      CALL CHECK_ALLOCATE(IERR,'GREHIS:TMP0')

      ! This also works for history files.
      ! Then NDP.EQ.1, so it is basically a copy
      DO I = 1,NDP
        DO IELEM = 1,NELEM_GEO
          TMP2((I-1)*NELEM_GEO + IELEM) = IKLE_GEO((IELEM-1)*NDP+I)
        ENDDO
      ENDDO

      CALL SET_MESH(RESFORMAT,NRES,2,TYP_ELEM,NDP,NPTFR,NPTIR,
     &              NELEM_GEO,NPOIN_GEO,TMP2,IPOBO_GEO,IPOBO_GEO,X,Y,
     &              NPLAN_RES,DATE,TIME,0,0,IERR,
     &              IN_PLACE=.TRUE.)
      CALL CHECK_CALL(IERR,'GREHIS:SET_MESH:RES')
      DEALLOCATE(IKLE_GEO)
      DEALLOCATE(TMP2)
      DEALLOCATE(IPOBO_GEO)
      DEALLOCATE(X)
      DEALLOCATE(Y)
      NPOIN_RES = NPOIN_GEO
!----------------------------------------------------------------------
!
!     Read results informations from partitioned files
!
      CALL MERGE_DATA_HIS
     &(NPOIN_RES,NVAR_RES,NTIMESTEP_RES,NPROC,RESFORMAT,NRES,TYP_ELEM,
     & TEXTELU,RES,METHOD,FIRST_FILE,USE_RESPAR)

      ! DONE
      CALL CLOSE_MESH(RESFORMAT,NRES,IERR)
      CALL CHECK_CALL(IERR,'GREHIS:CLOSEMESH:RES')

      DEALLOCATE(TEXTELU)
      DEALLOCATE(USE_RESPAR)
      WRITE(LU,*) 'END OF PROGRAM, ',NTIMESTEP_RES,' DATASETS FOUND'
!
      STOP 0

      END PROGRAM GREHIS_AUTOP
