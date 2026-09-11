!                   *************************
                    SUBROUTINE MERGE_DATA_HIS
!                   *************************
!
     &(NPOIN_RES,NVAR_RES,NTIMESTEP_RES,NPROC,RESFORMAT,NRES,TYP_ELEM,
     & TEXTELU,RES,METHOD,FIRST_FILE,USE_RESPAR)
!
!***********************************************************************
! PARALLEL   V8P5
!***********************************************************************
!
!brief    MERGES THE RESULTS OF A PARALLEL COMPUTATION
!+                TO WRITE A SINGLE FILE IN A GIVEN FORMAT.
!
!
!history W.A. Breugem (IMDC)
!+        19/11/2022
!+
!+   Creation from merge_data, for time series files
!
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!>@param[in] GEO Name of the geometry file
!>@param[in,out] GEOFORMAT Format of the geometry file
!>@param[in] BND Name of the boudnary file
!>@param[in] RES Name of the result file
!>@param[in,out] RESFORMAT Format of the result file
!>@param[in] NPROC Number of processors
!>@param[in] FIRST_FILE Number of the first non-empty file
!>@param[in] USE_RESPAR Mask whether a file is used
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE INTERFACE_HERMES
      USE DECLARATIONS_SPECIAL
!
      IMPLICIT NONE
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
!
      INTEGER, INTENT(IN) :: NPOIN_RES,NVAR_RES,NTIMESTEP_RES,NPROC
      CHARACTER(LEN=8), INTENT(INOUT) :: RESFORMAT
      INTEGER, INTENT(IN) :: NRES,TYP_ELEM,METHOD,FIRST_FILE
      CHARACTER(LEN=32), INTENT(IN) :: TEXTELU(NVAR_RES)
      CHARACTER(LEN=PATH_LEN), INTENT(IN) :: RES
      LOGICAL, INTENT(IN) :: USE_RESPAR(NPROC)
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
!
      INTEGER :: I,J,IERR,IVAR
      INTEGER :: ITIME,IPID
      INTEGER NRESPAR
      INTEGER NPOIN_PAR
      INTEGER, DIMENSION(:), ALLOCATABLE :: KNOLG
      DOUBLE PRECISION, DIMENSION(:), ALLOCATABLE :: TMP
      DOUBLE PRECISION AT
      CHARACTER(LEN=16) :: VARNAME
      DOUBLE PRECISION, DIMENSION(:,:), ALLOCATABLE :: RESDATA
      DOUBLE PRECISION, DIMENSION(:,:,:), ALLOCATABLE :: RESDATA2
      DOUBLE PRECISION, DIMENSION(:), ALLOCATABLE :: TIMES
      CHARACTER(LEN=PATH_LEN) :: RESPAR
      CHARACTER(LEN=11) EXTENS
      EXTERNAL  EXTENS

      IF(METHOD.EQ.1) THEN
        ALLOCATE(RESDATA(NPOIN_RES,NVAR_RES),STAT=IERR)
        CALL CHECK_ALLOCATE(IERR,'GREHIS:RESDATE')
        ! LOOP ON ALL THE PARTITIONNED FILES
        DO ITIME=0,NTIMESTEP_RES-1
          DO IPID = 0, NPROC-1
          
            ! SKIP EMPTY OR NON-EXISTING FILES (OCCURS FOR HISTORY FILES)
            IF(.NOT.USE_RESPAR(IPID+1)) THEN
              CYCLE
            ENDIF
!
            RESPAR = TRIM(RES) // EXTENS(NPROC-1,IPID)
            CALL OPEN_MESH(RESFORMAT,RESPAR,NRESPAR,'READ     ',IERR)
            CALL CHECK_CALL(IERR,"GREHIS:OPEN_MESH:RESPAR2")
!
            CALL GET_MESH_NPOIN(RESFORMAT,NRESPAR,TYP_ELEM,
     &                          NPOIN_PAR,IERR)
            CALL CHECK_CALL(IERR,"GREHIS:GET_MESH_NPOIN:RESPAR")
!
            ALLOCATE(KNOLG(NPOIN_PAR),STAT=IERR)
            CALL CHECK_ALLOCATE(IERR,'GREHIS:KNOLG')
            ALLOCATE(TMP(NPOIN_PAR),STAT=IERR)
            CALL CHECK_ALLOCATE(IERR,'GREHIS:TMP')
            ! GET THE TIME OF THE TIMSTEP
            IF(IPID.EQ.FIRST_FILE) THEN
              CALL GET_DATA_TIME(RESFORMAT,NRESPAR,ITIME,AT,IERR)
              CALL CHECK_CALL(IERR,'GREHIS:GET_DATA_TIME:RESPAR')
            ENDIF
!
            CALL GET_MESH_L2G_NUMBERING(RESFORMAT,NRESPAR,KNOLG,
     &                                  NPOIN_PAR,IERR)
            CALL CHECK_CALL(IERR,'GREHIS:GET_MESH_L2G_NUMBERING:RESPAR')
!
            ! LOOP ON ALL THE VARIABLE FOR THE TIMESTEP ITIME
            DO IVAR=1,NVAR_RES
              VARNAME = TEXTELU(IVAR)(1:16)
              CALL GET_DATA_VALUE(RESFORMAT,NRESPAR,ITIME,
     &                            VARNAME,TMP,
     &                            NPOIN_PAR,IERR)
              CALL CHECK_CALL(IERR,'GREHIS:GET_DATA_VALUE')
              DO I=1,NPOIN_PAR
                RESDATA(KNOLG(I),IVAR) = TMP(I)
              ENDDO
            ENDDO ! IVAR
            CALL CLOSE_MESH(RESFORMAT,NRESPAR,IERR)
            CALL CHECK_CALL(IERR,'GREHIS:CLOSEMESH:RESPAR')
            DEALLOCATE(TMP)
            DEALLOCATE(KNOLG)
          ENDDO ! IPID
          ! WRITING TIME STEP
          WRITE(LU,*)'WRITING DATASET NO.',ITIME,' TIME =',REAL(AT)
          !
          DO I=1,NVAR_RES
            CALL ADD_DATA(RESFORMAT,NRES,TEXTELU(I),AT,ITIME,I.EQ.1,
     &                    RESDATA(:,I),NPOIN_RES,IERR)
            CALL CHECK_CALL(IERR,'GREHIS:ADD_DATA:RES')
          ENDDO

        ENDDO ! ITIME
        DEALLOCATE(RESDATA)
      ELSEIF (METHOD.EQ.2) THEN
        ALLOCATE(RESDATA2(NPOIN_RES,NVAR_RES,NTIMESTEP_RES),STAT=IERR)
        CALL CHECK_ALLOCATE(IERR,'GREHIS:RESDATA2')
        ALLOCATE(TIMES(NTIMESTEP_RES),STAT=IERR)
        CALL CHECK_ALLOCATE(IERR,'GREHIS:TIMES')
        ! LOOP ON ALL THE PARTITIONNED FILES
        DO IPID = 0, NPROC-1
!
          ! SKIP EMPTY OR NON-EXISTING FILES
          IF(.NOT.USE_RESPAR(IPID+1)) THEN
            CYCLE
          ENDIF

          RESPAR = TRIM(RES) // EXTENS(NPROC-1,IPID)
          CALL OPEN_MESH(RESFORMAT,RESPAR,NRESPAR,'READ     ',IERR)
          CALL CHECK_CALL(IERR,"GREHIS:OPEN_MESH:RESPAR2")
!
          CALL GET_MESH_NPOIN(RESFORMAT,NRESPAR,TYP_ELEM,
     &                        NPOIN_PAR,IERR)
          CALL CHECK_CALL(IERR,"GREHIS:GET_MESH_NPOIN:RESPAR")
!
          ALLOCATE(KNOLG(NPOIN_PAR),STAT=IERR)
          CALL CHECK_ALLOCATE(IERR,'GREHIS:KNOLG')
          ALLOCATE(TMP(NPOIN_PAR),STAT=IERR)
          CALL CHECK_ALLOCATE(IERR,'GREHIS:TMP')
          ! GET THE TIME OF THE TIMSTEP
!
          CALL GET_MESH_L2G_NUMBERING(RESFORMAT,NRESPAR,KNOLG,
     &                                NPOIN_PAR,IERR)
          CALL CHECK_CALL(IERR,'GREHIS:GET_MESH_L2G_NUMBERING:RESPAR')
!
          DO ITIME=0,NTIMESTEP_RES-1
            ! LOOP ON ALL THE VARIABLE FOR THE TIMESTEP ITIME
            IF(IPID.EQ.FIRST_FILE) THEN
              CALL GET_DATA_TIME(RESFORMAT,NRESPAR,ITIME,
     &                           TIMES(ITIME+1),IERR)
              CALL CHECK_CALL(IERR,'GREHIS:GET_DATA_TIME:RESPAR')
            ENDIF
            DO IVAR=1,NVAR_RES
              VARNAME = TEXTELU(IVAR)(1:16)
              CALL GET_DATA_VALUE(RESFORMAT,NRESPAR,ITIME,
     &                            VARNAME,TMP,
     &                            NPOIN_PAR,IERR)
              CALL CHECK_CALL(IERR,'GREHIS:GET_DATA_VALUE')
              DO I=1,NPOIN_PAR
                RESDATA2(KNOLG(I),IVAR,ITIME+1) = TMP(I)
              ENDDO
            ENDDO ! IVAR
          ENDDO ! ITIME
          CALL CLOSE_MESH(RESFORMAT,NRESPAR,IERR)
          CALL CHECK_CALL(IERR,'GREHIS:CLOSEMESH:RESPAR')
          DEALLOCATE(TMP)
          DEALLOCATE(KNOLG)
        ENDDO ! IPID
        ! WRITING RESULTS
        DO ITIME=0,NTIMESTEP_RES-1
          ! WRITING TIME STEP
          WRITE(LU,*) 'WRITING DATASET NO.',ITIME,' TIME =',
     &               REAL(TIMES(ITIME+1))
          !
          DO I=1,NVAR_RES
            CALL ADD_DATA(RESFORMAT,NRES,TEXTELU(I),TIMES(ITIME+1),
     &                    ITIME,I.EQ.1,
     &                    RESDATA2(:,I,ITIME+1),NPOIN_RES,IERR)
            CALL CHECK_CALL(IERR,'GREHIS:ADD_DATA:RES')
          ENDDO
        ENDDO

        DEALLOCATE(RESDATA2)
        DEALLOCATE(TIMES)
      ELSE
        WRITE(LU,*) 'UNKOWN METHOD:',METHOD
        CALL PLANTE(1)
      ENDIF
      END SUBROUTINE MERGE_DATA_HIS
