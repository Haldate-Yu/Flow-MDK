!                       ****************
                        SUBROUTINE ELMPB
!                       ****************
!
     &(NBPB,NUMPB,X,Y,IKLE,NCOLOR,ISDRY,NEW)
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Removing elements contained within more than one element
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| NBPB          |<--| Number of nodes to be deleted
!| NUMPB         |-->| Node numbers to be deleted
!| X,Y           |<--| Coordinates
!| IKLE          |-->| Connectivity matrix
!| NCOLOR        |<--| Array of node colours
!| ELPSEC        |<--| Elimin marker for virtually dried up elements
!| ISDRY(NELMAX) |-->| MARKER FOR VIRTUALLY DRIED UP ELEMENTS
!|               |    | = 1 node always dry,
!|               |    | = 0 below seusec at least for 1 time step
!| IHAUT         |-->| Index for the variable water depth in the selafin
!| NVAR          |-->| Number of variables in the selafin
!| H             |-->| Water depth
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL
      IMPLICIT NONE
!
      INTEGER, INTENT(INOUT) :: IKLE(NELMAX,4), ISDRY(NPMAX), NEW(NPMAX)
      INTEGER, INTENT(INOUT) :: NCOLOR(NPMAX)
      INTEGER,INTENT(IN) :: NBPB, NUMPB(100)
      DOUBLE PRECISION, INTENT(INOUT) :: X(NPMAX) , Y(NPMAX)
!
      INTEGER I, IEL, J, NELI

!
!
!     -------------------------------------------------------------
!     REMOVING ELEMENTS HAVING TROUBLING NODES
!     -------------------------------------------------------------
!
      DO I=1,NBPB
        DO IEL = 1, NELEM
          IF (IKLE(IEL,1).EQ.NUMPB(I).OR.IKLE(IEL,2).EQ.NUMPB(I)
     &        .OR.IKLE(IEL,3).EQ.NUMPB(I)) THEN
            IKLE(IEL, 1) = 0
            IKLE(IEL, 2) = 0
            IKLE(IEL, 3) = 0
          ENDIF
        ENDDO
      ENDDO
!
!     REMOVING ELEMENTS
!     ------------------------
!
      NELI = 0
      IEL = 1
!     FOR EACH ELEMENT - DO
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
      WRITE(LU,2009) NELI
!
      NELEM = NELEM - NELI
!
!      REMOVING NODES NOT IN THE MESH ANYMORE
!      REUSE OF ISDRY TO MARK UNUSED NODES
!      ---------------------------------------------
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
!     FOR EACH NODE DO
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
        IF (ISDRY(I) .EQ.0) THEN
!         NODE I TO BE DELETED
          NELI = NELI + 1
!         SLIDING NODE RECORDS IN THE ARRAY
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
      WRITE(LU,2011) NELI
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
 2009 FORMAT(1X,'ELEMENTS CANCELLED IN THE MESH:',I8)
 2011 FORMAT(1X,'POINTS CANCELLED IN THE MESH:  ',I8)
      END
