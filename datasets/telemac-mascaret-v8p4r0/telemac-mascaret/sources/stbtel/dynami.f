!                       *****************
                        SUBROUTINE DYNAMI
!                       *****************
!
     &(NPTFR,NBOR,LIHBOR,LIUBOR,LIVBOR,LITBOR,NCOLFR,MAILLE,NLIM)
!
!***********************************************************************
! STBTEL V6P0
!***********************************************************************
!
!brief    Writing the DYNAM file for TELEMAC
!+        For all changes to the boundary conditions, see in the SPGM
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| NPTFR     |-->| Number of boundary nodes
!| NBOR      |-->| Array of boundary nodes
!| NCOLFR    |-->| Array of boundary node colours
!| MAILLE    |-->| Name of the mesh generator
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE INTERFACE_HERMES
      USE DECLARATIONS_STBTEL, ONLY: OUT_FORMAT, TYP_BND_ELEM
!
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) :: NPTFR, NLIM
      INTEGER, INTENT(IN) :: NBOR(*) , NCOLFR(*)
      INTEGER, INTENT(INOUT) :: LIHBOR(*) , LIUBOR(*)
      INTEGER, INTENT(INOUT) :: LIVBOR(*) ,LITBOR(*)
      CHARACTER(LEN=9), INTENT(IN) :: MAILLE
!
      INTEGER ILOG , IADH , IENT , IENTU , IINC , ISORT
!
      INTEGER I,J,IERR
!
      DOUBLE PRECISION, ALLOCATABLE :: ZEROS(:)
      INTEGER, ALLOCATABLE :: NCOLOR(:)
!
!
!***********************************************************************
!
      ILOG = 2
      IADH = 0
      IENT = 5
      IENTU= 6
      ISORT= 4
      IINC = 1
!
      REWIND NLIM
!
      DO J =1,NPTFR
!
!     BY DEFAULT, WE ASSUME THAT THE NODE IS A SOLID BOUNDARY NODE
!     WITHOUT FRICTION. COLOUR 11 PROVIDES THIS FUNCTIONALITY,
!     WHICH IS STANDRD FOR SUPERTAB.
!
        LIHBOR(J)=ILOG
        LIUBOR(J)=ILOG
        LIVBOR(J)=ILOG
        LITBOR(J)=ILOG
!
        IF(NCOLFR(J).EQ.1) THEN
!
! H IMPOSED , U AND V OPEN BOUNDARY
!
          LIHBOR(J)=IENT
          LIUBOR(J)=ISORT
          LIVBOR(J)=ISORT
          LITBOR(J)=ISORT
!
        ELSE IF (NCOLFR(J).EQ.2) THEN
!
!  H  IMPOSED , IMPOSED DISCHARGED
!
          LIHBOR(J)=IENT
          LIUBOR(J)=IENT
          LIVBOR(J)=IENT
          LITBOR(J)=IENT
!
        ELSE IF (NCOLFR(J).EQ.3) THEN
!
!  H , U ET V INPOSED
!
          LIHBOR(J)=IENT
          LIUBOR(J)=IENTU
          LIVBOR(J)=IENTU
          LITBOR(J)=IENT
!
        ELSE IF (NCOLFR(J).EQ.4) THEN
!
! H IMPOSED , U OPEN , V SET TO ZERO
!
          LIHBOR(J)=IENT
          LIUBOR(J)=ISORT
          LIVBOR(J)=IADH
          LITBOR(J)=ISORT
!
        ELSE IF (NCOLFR(J).EQ.5) THEN
!
!  INCOMING WAVE CONDITION
!
          LIHBOR(J)=IINC
          LIUBOR(J)=IINC
          LIVBOR(J)=IINC
          LITBOR(J)=ISORT
!
        ELSE IF (NCOLFR(J).EQ.7) THEN
!
! H IMPOSED , U SET TO ZERO , V OPEN BOUNDARY
!
          LIHBOR(J)=IENT
          LIUBOR(J)=IADH
          LIVBOR(J)=ISORT
          LITBOR(J)=ISORT
!
        ELSE IF (NCOLFR(J).EQ.8) THEN
!
! H OPEN BOUNDARY , U AND V IMPOSED
!
          LIHBOR(J)=ISORT
          LIUBOR(J)=IENT
          LIVBOR(J)=IENT
          LITBOR(J)=IENT
!
        ELSE IF (NCOLFR(J).EQ.9) THEN
!
!  H OPEN BOUNDARY , U AND V IMPOSED
!
          LIHBOR(J)=ISORT
          LIUBOR(J)=IENTU
          LIVBOR(J)=IENTU
          LITBOR(J)=IENT
!
        ELSE IF (NCOLFR(J).EQ.12) THEN
!
! H OPEN BOUNDARY , U IMPOSED , V SET TO ZERO
!
          LIHBOR(J)=ISORT
          LIUBOR(J)=IENT
          LIVBOR(J)=IADH
          LITBOR(J)=IENT
!
        ELSE IF (NCOLFR(J).EQ.13) THEN
!
! SOLID BOUNDARY WITH V SET TO ZERO
!
          LIHBOR(J)=ILOG
          LIUBOR(J)=ILOG
          LIVBOR(J)=IADH
          LITBOR(J)=ILOG
!
        ELSE IF (NCOLFR(J).EQ.14) THEN
!
! SOLID BOUNDARY WITH U SET TO ZERO
!
          LIHBOR(J)=ILOG
          LIUBOR(J)=IADH
          LIVBOR(J)=ILOG
          LITBOR(J)=ILOG
!
        ELSE IF (NCOLFR(J).EQ.15) THEN
!
! H OPEN BOUNDARY , U SET TO ZERO , V IMPOSED
!
          LIHBOR(J)=ISORT
          LIUBOR(J)=IADH
          LIVBOR(J)=IENT
          LITBOR(J)=IENT
!
        ENDIF
!
      ENDDO
!
      ALLOCATE(NCOLOR(NPTFR))
      ALLOCATE(ZEROS(NPTFR))
      DO I=1,NPTFR
        NCOLOR(I) = I
      ENDDO
      ZEROS = 0.D0
!
      CALL SET_BND(OUT_FORMAT, NLIM, TYP_BND_ELEM, NPTFR, 1, NBOR,NPTFR,
     &             LIHBOR, LIUBOR, LIVBOR, ZEROS, ZEROS, ZEROS, ZEROS,
     &             LITBOR, ZEROS, ZEROS, ZEROS, NCOLOR, IERR)
      CALL CHECK_CALL(IERR, 'DYNAMI:SET_BND')

      DEALLOCATE(NCOLOR)
      DEALLOCATE(ZEROS)
!
      IF (MAILLE(1:8).NE.'SUPERTAB'.AND.
     &    MAILLE(1:7).NE.'TRIGRID') WRITE(LU,3040) MAILLE
!
!-----------------------------------------------------------------------
!
 3040 FORMAT(/,
     & ' **************************************************',/,
     & ' BEWARE: THE UNIVERSAL FILE FORMAT IS ',A8,/,
     & '         BOUNDARY CONDITIONS WILL HAVE TO BE',/,
     & '         CHECKED IN THE BOUNDARY CONDITIONS FILE',/,
     & ' **************************************************',/)
!
!-----------------------------------------------------------------------
!
      RETURN
      END
