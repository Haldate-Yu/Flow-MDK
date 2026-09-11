!                       *****************
                        SUBROUTINE ELMSEC
!                       *****************
!
     &( ELPSEC, SEUSEC, TPSFIN,  X, Y, IKLE, NCOLOR, ISDRY,
     &  IHAUT, NVAR, H, WORK, NEW, STD, NGEO, TEXTE )
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Removing dried-up elements
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| NBPB          |<--| Number of nodes to be deleted
!| NUMPB         |-->| Node numbers to be deleted
!| X,Y           |<--| Coordinates
!| IKLE          |-->| Connectivity matrix
!| MESH          |<--| Mesh
!| NDP           |-->| Number of nodes per element
!| NPOIN         |<--| Total number of nodes in the mesh
!| NELEM         |<--| Total number of element in the mesh
!| NPMAX         |-->| Actual size of the node-based x and y arrays
!|               |   | (NPMAX = NPOIN + 0.1*NELEM)
!| NCOLOR        |<--| Array of node colours
!| ELPSEC        |<--| Elimin marker for virtually dried up elements
!| SEUSEC        |-->| Threshold defining wet/dry values
!| ISDRY(NELMAX) |-->| Marker for virtually dried up elements
!|               |   | = 1 node always dry,
!|               |   | = 0 below seusec at least for 1 time step
!| IHAUT         |-->| Index for the variable water depth in the selafin
!| NVAR          |-->| Number of variables in the selfin
!| H             |-->| Water depth
!| WORK          |-->| Working array
!| NRES          |-->| Index refering to the serafin file
!| NGEO          |-->| Index refering to the mesh generator file
!| NLIM          |-->| Index refering to the dynam file
!| NFO1          |-->| Index refering to the triangle trigrid file
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELEM,NPOIN,NELMAX,NPMAX,FFORMAT
      USE INTERFACE_STBTEL, EX_ELMSEC => ELMSEC
      USE INTERFACE_HERMES
      IMPLICIT NONE
!
      LOGICAL, INTENT(IN) :: ELPSEC
      DOUBLE PRECISION, INTENT(IN) :: SEUSEC
      DOUBLE PRECISION, INTENT(INOUT) :: X(NPMAX),Y(NPMAX)
      DOUBLE PRECISION, INTENT(INOUT) :: H(NPMAX),TPSFIN(1)
      INTEGER, INTENT(INOUT) :: IKLE(NELMAX,4), ISDRY(NPMAX), NEW(NPMAX)
      INTEGER, INTENT(INOUT) :: NCOLOR(NPMAX)
      INTEGER, INTENT(IN) :: IHAUT, NVAR
      REAL, INTENT(INOUT) :: WORK(*)
      INTEGER, INTENT(IN) :: NGEO
      CHARACTER(LEN=3), INTENT(IN) :: STD
      CHARACTER(LEN=32), INTENT(IN) :: TEXTE(NVAR)
!
!
!     LOCAL VARIABLES
!
      INTEGER I, IEL, NPDT, NPSEC, NSEC
      INTEGER J, NELI, IERR
      INTEGER NP1, NP2, NP3, ISECH
!------------------------------------------------------------
      IF (NVAR.EQ.0) THEN
        WRITE(LU,2012)
        RETURN
      ENDIF
      IF (IHAUT.EQ.0) THEN
        WRITE(LU,2013)
        RETURN
      ENDIF
!     INITIALISATION OF ISDRY : EVERYTHING DRY BY DEFAULT
      DO I = 1, NPOIN
        ISDRY(I) = 1
      ENDDO
!     LOADING SELFIN VALUE INTO ISDRY
!     -------------------------------------------------------------

!     -----------------------
!     GETTING OUT IF NO TIME STEP
      CALL GET_DATA_NTIMESTEP(FFORMAT, NGEO, NPDT, IERR)
      CALL CHECK_CALL(IERR, 'ELMSEC:GET_DATA_NTIMESTEP')

      IF (NPDT.EQ.0) THEN
        WRITE(LU,2001)
        CALL PLANTE(1)
        STOP
      ENDIF

      CALL GET_DATA_TIME(FFORMAT, NGEO, NPDT-1, TPSFIN(1), IERR)
      CALL CHECK_CALL(IERR, 'ELMSEC:GET_DATA_TIME')

      CALL GET_DATA_VALUE(FFORMAT, NGEO, NPDT-1, TEXTE(IHAUT),
     &                    H, NPOIN,IERR)
      CALL CHECK_CALL(IERR, 'ELMSEC:GET_DATA_VALUE')

      NPSEC = 0
      DO I = 1, NPOIN
        IF (H(I).GT.SEUSEC) THEN
          ISDRY(I) = 0
        ELSE
          NPSEC = NPSEC + 1
        ENDIF
      ENDDO
      WRITE(LU,2000) TPSFIN(1), NPSEC, SEUSEC
!
!     TESTING DRY/WET ELEMENTS
!     ---------------------------------------------
      NPSEC = 0
      NSEC = 0
!
!     LOOP OVER ELEMENTS
      DO IEL = 1, NELEM
        NP1 = IKLE(IEL, 1)
        NP2 = IKLE(IEL, 2)
        NP3 = IKLE(IEL, 3)
        ISECH = ISDRY(NP1) * ISDRY(NP2) * ISDRY(NP3)
!       IF ISECH (PRODUCT) = 1 ELEMENT IEL ALWAYS DRY
        IF (ISECH.EQ.1) THEN
!         SET TO 0 ALL NODES OF THE ELEMENT
          NSEC = NSEC + 1
          IKLE(IEL, 1) = 0
          IKLE(IEL, 2) = 0
          IKLE(IEL, 3) = 0
        ELSE
          IF (ELPSEC) THEN
!         TEST IF THE ELEMENT PARTLY DRY
            ISECH =  ISDRY(NP1) + ISDRY(NP2) + ISDRY(NP3)
            IF (ISECH.GE.1) THEN
!             PARTLY DRY ELEMENT TO BE REMOVED
!             SET TO ZERO ALL NODES OF THE ELEMENTS
              IKLE(IEL, 1) = 0
              IKLE(IEL, 2) = 0
              IKLE(IEL, 3) = 0
              NPSEC = NPSEC + 1
            ENDIF
!           END LOOP REMOVING PARTLY DRIED ELEMENTS
          ENDIF
        ENDIF
      ENDDO !IEL
!     END LOOP OVER ALL ELEMENTS
      IF (NSEC.EQ.0) THEN
        WRITE(LU,2002)
      ELSE IF (NSEC.EQ.1) THEN
        WRITE(LU,2003)
      ELSE
        WRITE(LU,2004) NSEC
      ENDIF
!
      IF (ELPSEC) THEN
        IF (NPSEC.EQ.0) THEN
          WRITE(LU,2005)
        ELSE IF (NPSEC.EQ.1) THEN
          WRITE(LU,2006)
        ELSE
          WRITE(LU,2007) NPSEC
        ENDIF
      ENDIF
!
!     EXIT IF THERE ARE NO DRIED OR PARTLY DRIED ELEMENT
      IF ((NSEC.EQ.0) .AND. (NPSEC.EQ.0)) RETURN
!
!     REMOVAL OF DRIED OR PARTLY DRIED ELEMENTS
!     ---------------------------------------------
      NELI = 0
      IEL = 1
!     FOR EACH ELEMENT DO
 20   CONTINUE
        IF ((IKLE(IEL, 1).EQ.0).AND.(IKLE(IEL, 2).EQ.0).AND.
     &     (IKLE(IEL, 3).EQ.0)) THEN
          NELI = NELI + 1
          DO I = IEL, NELEM - NELI
            IKLE(I,1) = IKLE(I+1, 1)
            IKLE(I,2) = IKLE(I+1, 2)
            IKLE(I,3) = IKLE(I+1, 3)
          ENDDO
        ELSE
          IEL = IEL + 1
        ENDIF
      IF (IEL .LE. NELEM-NELI) GOTO 20
!     END LOOP FOR EACH ELEMENT
!
      IF (NELI .LE. 0) THEN
        WRITE(LU,2008)
      ELSE
        WRITE(LU,2009) NELI
      ENDIF
!
      NELEM = NELEM - NELI
!
!      REMOVING NODES NOT IN THE MESH ANYMORE
!      REUSE OF ISDRY TO MARK UNUSED NODES
!     ---------------------------------------------
      DO I = 1, NPOIN
        ISDRY(I) = 0
        NEW(I) = 0
      ENDDO
!
      DO IEL = 1, NELEM
        ISDRY(IKLE(IEL,1)) = IKLE(IEL,1)
        ISDRY(IKLE(IEL,2)) = IKLE(IEL,2)
        ISDRY(IKLE(IEL,3)) = IKLE(IEL,3)
      ENDDO
!
      NELI = 0
      I = 1
!     FOR EACH NODE - DO
      DO I = 1, NPOIN
        IF (ISDRY(I) .EQ.0) THEN
          NELI = NELI + 1
          NEW(I) = 0
        ELSE
          NEW(I) = I - NELI
        ENDIF
      ENDDO
!     END LOOP FOR EACH NODE
!
      NELI = 0
      I = 1
!     FOR EACH NODE - DO
 30   CONTINUE
      IF (ISDRY(I).EQ.0) THEN
!       NODE I TO BE REMOVED
        NELI = NELI + 1
!       SLIDING NODE RECORDS
        DO J = I, NPOIN - NELI
          X(J) = X(J+1)
          Y(J) = Y(J+1)
          NCOLOR(J) = NCOLOR(J+1)
          IF (ISDRY(J+1).GT.0) THEN
            ISDRY(J) = ISDRY(J+1) - 1
          ELSE
            ISDRY(J) = 0
          ENDIF
        ENDDO
      ELSE
        I = I + 1
      ENDIF
      IF (I .LE. NPOIN - NELI) GOTO 30
!     END LOOP FOR EACH NODE
      IF (NELI .LE. 0) THEN
        WRITE(LU,2010)
      ELSE
        WRITE(LU,2011) NELI
      ENDIF
      NPOIN = NPOIN - NELI
!
!     RETRACE NUMBERING IN IKLE
!     ----------------------------------------
      DO IEL = 1, NELEM
        J = IKLE(IEL,1)
        IKLE(IEL,1) = NEW(J)
        J = IKLE(IEL,2)
        IKLE(IEL,2) = NEW(J)
        J = IKLE(IEL,3)
        IKLE(IEL,3) = NEW(J)
      ENDDO
      RETURN
!***********************************************************************
 2000 FORMAT(1X,'TIME ',G15.3,' : ',I8,
     &' POINT(S) WITH WATER DEPTH BELOW',G15.3)
!
 2001 FORMAT(/,1X,'SORRY, THE UNIVERSAL FILE DOES NOT CONTAIN',
     & /,1X,'ANY COMPUTATION RESULTS.',
     & /,1X,'FINDING OUT DRY ELEMENTS IS IMPOSSIBLE !')
!
 2002 FORMAT(1X,'NO COMPLETELY DRY ELEMENT IN THE MESH.')
!
 2003 FORMAT(1X,'ONLY ONE COMPLETELY DRY ELEMENT FOUND',
     & /,1X,'IN THE MESH.')
!
 2004 FORMAT(1X,'COMPLETELY DRY ELEMENTS IN THE MESH: ',I8)
!
 2005 FORMAT(1X,'NO PARTIALLY DRY ELEMENT IN THE MESH.')
!
 2006 FORMAT(1X,'ONLY ONE PARTIALLY DRY ELEMENT IN THE MESH.')
!
 2007 FORMAT(1X,'PARTIALLY DRY ELEMENTS IN THE MESH:',I8)
!
 2008 FORMAT(1X,'NO ELEMENT HAS BEEN CANCELLED IN THE MESH.')
!
 2009 FORMAT(1X,'ELEMENTS CANCELLED IN THE MESH:',I8)
!
 2010 FORMAT(1X,'NO POINT HAS BEEN CANCELLED IN THE MESH.')
!
 2011 FORMAT(1X,'POINTS CANCELLED IN THE MESH:  ',I8)
!
 2012 FORMAT(/,1X,'NO VARIABLE STORED ON THE FILE. ',
     & /,1X,'DRY ELEMENT SUPPRESSION IS IMPOSSIBLE.')
!
 2013 FORMAT(/,1X,'THE WATER DEPTH VARIABLE IS NOT STORED ON THE FILE',
     & /,1X,'DRY ELEMENT SUPPRESSION IS IMPOSSIBLE.')
      END
