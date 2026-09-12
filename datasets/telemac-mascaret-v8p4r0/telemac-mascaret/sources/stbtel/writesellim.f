!                   *****************
                    SUBROUTINE WRITESELLIM
!                   *****************
!
     &(NLIM,LIHBOR,LIUBOR,LIVBOR,HBOR,UBOR,VBOR,
     & CHBORD,NBOR,NPMAX,NPTFR)
!
!***********************************************************************
! STBTEL
!***********************************************************************
!
!brief    READS THE BOUNDARY CONDITIONS FILE AND
!+                STORES IN ARRAYS THE DATA READ.
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| NLIM           |-->| Logical unit of boundary conditions file
!| LIHBOR         |-->| Type of boundary conditions on depth
!| LIUBOR         |-->| Type of boundary conditions on u
!| LIVBOR         |-->| Type of boundary conditions on v
!| HBOR           |<--| Prescribed boundary condition on depth
!| UBOR           |<--| Prescribed boundary condition on velocity u
!| VBOR           |<--| Prescribed boundary condition on velocity v
!| CHBORD         |<--| Friction coefficient at boundary
!| NBORD          |<--| Boundary numbering
!| NPTFR          |-->| Number of boundary points
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: OUT_FORMAT, TYP_BND_ELEM
!
      IMPLICIT NONE
!
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER, INTENT(IN)    :: NLIM
      INTEGER, INTENT(IN)    :: NPTFR
      INTEGER, INTENT(IN)    :: NPMAX
      INTEGER, INTENT(INOUT) :: LIUBOR(NPMAX),LIVBOR(NPMAX)
      INTEGER, INTENT(INOUT) :: LIHBOR(NPMAX)
      INTEGER, INTENT(INOUT) :: NBOR(NPMAX)
      DOUBLE PRECISION,  INTENT(INOUT) :: UBOR(NPMAX),VBOR(NPMAX)
      DOUBLE PRECISION,  INTENT(INOUT) :: HBOR(NPMAX),CHBORD(NPMAX)
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER I, IERR
      INTEGER, ALLOCATABLE :: NCOLOR(:)

      ALLOCATE(NCOLOR(NPTFR))
      DO I=1,NPTFR
        NCOLOR(I) = I
      ENDDO
!
      CALL SET_BND(OUT_FORMAT, NLIM, TYP_BND_ELEM, NPTFR, 1, NBOR,
     &             NPTFR, LIHBOR, LIUBOR, LIVBOR, HBOR, UBOR, VBOR,
     &             CHBORD, LIHBOR, HBOR, HBOR, HBOR, NCOLOR, IERR)
      CALL CHECK_CALL(IERR, 'WRITESELLIM:SET_BND')

      DEALLOCATE(NCOLOR)
!
      END SUBROUTINE
