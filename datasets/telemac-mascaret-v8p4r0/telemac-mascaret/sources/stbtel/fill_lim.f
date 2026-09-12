!                       *******************
                        SUBROUTINE FILL_LIM
!                       *******************
!
     & (NPTFR,NPTFRX,NTRAC,LIHBOR,LIUBOR,LIVBOR,LITBOR,
     &  HBOR,UBOR,VBOR,CHBORD,TBOR,ATBOR,BTBOR, NBOR, OLD_NBOR, KP1BOR)
!
!***********************************************************************
! STBTEL  V5P2
!***********************************************************************
!
!brief    Fills the boundary conditions arrays based on the
!+           coarser mesh information
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| HBOR      | <->| Prescribed depth
!| LIHBOR    | -->| Type of boundary conditions on depth
!| LITBOR    | -->| Type of boundary conditions on tracers
!| LIUBOR    | -->| Type of boundary conditions on velocity
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE BIEF
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE

      INTEGER, INTENT(IN)    :: NPTFR,NPTFRX,NTRAC
      INTEGER,INTENT(INOUT) :: LIHBOR(NPTFRX),LIUBOR(NPTFRX)
      INTEGER,INTENT(INOUT) :: LIVBOR(NPTFRX)
      TYPE(BIEF_OBJ)  , INTENT(INOUT) :: LITBOR
      DOUBLE PRECISION, INTENT(INOUT) :: UBOR(NPTFRX,2),VBOR(NPTFRX,2)
      DOUBLE PRECISION, INTENT(INOUT) :: HBOR(NPTFRX)
      DOUBLE PRECISION, INTENT(INOUT) :: CHBORD(NPTFRX)
      TYPE(BIEF_OBJ)  , INTENT(INOUT) :: TBOR, ATBOR, BTBOR
      INTEGER, INTENT(IN) :: NBOR(NPTFRX), OLD_NBOR(NPTFRX)
      INTEGER, INTENT(IN) :: KP1BOR(NPTFRX)

      INTEGER I, P1, P2
      INTEGER VAL_P1, VAL_P2, IDX

      LOGICAL :: REORDER, FOUND
      INTEGER, ALLOCATABLE :: CONV(:)
      INTEGER J, NODE1, NODE2

      INTEGER :: OLD_LIHBOR(NPTFR),OLD_LIUBOR(NPTFR)
      INTEGER :: OLD_LIVBOR(NPTFR)
      INTEGER :: OLD_LITBOR(NPTFR)
      DOUBLE PRECISION :: OLD_UBOR(NPTFR,2),OLD_VBOR(NPTFR,2)
      DOUBLE PRECISION :: OLD_HBOR(NPTFR)
      DOUBLE PRECISION :: OLD_CHBORD(NPTFR)
      DOUBLE PRECISION :: OLD_TBOR(NPTFR), OLD_ATBOR(NPTFR)
      DOUBLE PRECISION :: OLD_BTBOR(NPTFR)


! CHECK IF THE NBOR OF THE ORIGINAL MESH HAS THE SAME OREDERING AS
! THE ONE IN THE REFINE MESH THAT WENT THROUGH RANBO
      REORDER = .FALSE.
      DO I=1,NPTFR
        IF (OLD_NBOR(I) .NE. NBOR(2*(I-1)+1)) THEN
          REORDER = .TRUE.
          EXIT
        ENDIF
      ENDDO

      ALLOCATE(CONV(NPTFR))

      IF (REORDER) THEN
        DO I=1,NPTFR
          NODE1 = NBOR(2*I)
          NODE2 = NBOR(2*(I-1)+1)
          FOUND = .FALSE.
          DO J=1,NPTFR
            IF (OLD_NBOR(J).EQ.NODE1.OR.OLD_NBOR(J).EQ.NODE2) THEN
              FOUND = .TRUE.
              EXIT
            ENDIF
          ENDDO
          IF(.NOT.FOUND) THEN
            WRITE(LU,*) 'COULD NOT FIND', J, NODE1, NODE2
            CALL PLANTE(1)
          ENDIF
          CONV(I) = J
        ENDDO
      ELSE
        DO I=1,NPTFR
          CONV(I) = I
        ENDDO
      ENDIF

      LIHBOR(1:NPTFR*2:2)=LIHBOR(CONV)
      LIUBOR(1:NPTFR*2:2)=LIUBOR(CONV)
      LIVBOR(1:NPTFR*2:2)=LIVBOR(CONV)

      CHBORD(1:NPTFR*2:2)=CHBORD(CONV)
      HBOR(1:NPTFR*2:2)=HBOR(CONV)
      UBOR(1:NPTFR*2:2,1)=UBOR(CONV,1)
      VBOR(1:NPTFR*2:2,1)=VBOR(CONV,1)
      UBOR(1:NPTFR*2:2,2)=UBOR(CONV,2)
      VBOR(1:NPTFR*2:2,2)=VBOR(CONV,2)

      IF (NTRAC.GT.0) THEN
        LITBOR%ADR(1)%P%I(1:NPTFR*2:2)=LITBOR%ADR(1)%P%I(CONV)
        TBOR%ADR(1)%P%R(1:NPTFR*2:2)=TBOR%ADR(1)%P%R(CONV)
        ATBOR%ADR(1)%P%R(1:NPTFR*2:2)=ATBOR%ADR(1)%P%R(CONV)
        BTBOR%ADR(1)%P%R(1:NPTFR*2:2)=BTBOR%ADR(1)%P%R(CONV)
      ENDIF
!
      DEALLOCATE(CONV)
!
!     FILLING THE POINT IN THE MIDDLE OF EACH SEGMENT
      DO I=1,NPTFR

        P1 = 2*I-1
!     USING KP1BOR TO IDENTIFY THE NEXT POINT (NOT 2*I+1 FOR I=NPTFR)
        P2 = KP1BOR(2*I)
!
        VAL_P1 = LIHBOR(P1)*1000 +
     &           LIUBOR(P1)*100  +
     &           LIVBOR(P1)*10
        IF(NTRAC.GT.0) THEN
          VAL_P1 = VAL_P1 + LITBOR%ADR(1)%P%I(P1)*1
        ENDIF

        VAL_P2 = LIHBOR(P2)*1000 +
     &           LIUBOR(P2)*100  +
     &           LIVBOR(P2)*10
        IF(NTRAC.GT.0) THEN
          VAL_P2 = VAL_P2 + LITBOR%ADR(1)%P%I(P2)*1
        ENDIF

!       IF SAME TYPE ON EACH POINT APPLY THE SAME TYPE
        IF (VAL_P1.EQ.VAL_P2) THEN
          IDX = P1
!       IF ONE OF THE POINTS IS A SOLID POINT TAKING THAT ONE
        ELSE IF(LIHBOR(P1).EQ.2) THEN
          IDX = P1
        ELSEIF(LIHBOR(P2).EQ.2) THEN
          IDX = P2
!       OTHERWISE TAKING THE SMALLEST ONE
        ELSEIF(VAL_P1.LT.VAL_P2) THEN
          IDX = P1
        ELSE
          IDX = P2
        ENDIF

        LIHBOR(2*I)=LIHBOR(IDX)
        LIUBOR(2*I)=LIUBOR(IDX)
        LIVBOR(2*I)=LIVBOR(IDX)
        CHBORD(2*I)=CHBORD(IDX)
        HBOR(2*I)=HBOR(IDX)
        UBOR(2*I,1)=UBOR(IDX,1)
        VBOR(2*I,1)=VBOR(IDX,1)
        UBOR(2*I,2)=UBOR(IDX,2)
        VBOR(2*I,2)=VBOR(IDX,2)
!
        IF(NTRAC.GT.0) THEN
          LITBOR%ADR(1)%P%I(2*I)=LITBOR%ADR(1)%P%I(IDX)
          ATBOR%ADR(1)%P%R(2*I)=ATBOR%ADR(1)%P%R(IDX)
          BTBOR%ADR(1)%P%R(2*I)=BTBOR%ADR(1)%P%R(IDX)
        ENDIF
!
      ENDDO
!
      END SUBROUTINE
