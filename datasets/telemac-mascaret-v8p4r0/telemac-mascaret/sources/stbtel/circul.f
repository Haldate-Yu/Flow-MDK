!                       *****************
                        SUBROUTINE CIRCUL
!                       *****************
!
     &(IKLE,ITEST1 ,IELEM,I1,I2,I3,X,Y,NNELMAX)
!
!***********************************************************************
!  STBTEL V5P2
!***********************************************************************
!
!brief
!+    Compute the area within the 3 points I1,I2,I3 and swap points
!+       I2 and I3 when the area is negative.
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| IKLE           |-->| Connectivity table
!| ITEST1         |-->| Interator
!| IELEM          |-->| Element number
!| I1,I2,I3       |-->| Ikle indices
!| X,Y            |-->| Coordinates
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) :: NNELMAX
      INTEGER, INTENT(IN) :: IELEM
      INTEGER, INTENT(INOUT) :: IKLE(NNELMAX,4)
      INTEGER, INTENT(IN) :: I1 , I2 , I3
      INTEGER, INTENT(INOUT) :: ITEST1
      DOUBLE PRECISION, INTENT(IN) :: X(*),Y(*)

      INTEGER I
!
      DOUBLE PRECISION X2 , X3 , Y2 , Y3
      DOUBLE PRECISION AIRE
!
!
      X2 = X(IKLE(IELEM,I2))-X(IKLE(IELEM,I1))
      X3 = X(IKLE(IELEM,I3))-X(IKLE(IELEM,I1))
!
      Y2 = Y(IKLE(IELEM,I2))-Y(IKLE(IELEM,I1))
      Y3 = Y(IKLE(IELEM,I3))-Y(IKLE(IELEM,I1))
!
      AIRE = X2*Y3 - X3*Y2
!
      IF (AIRE.LT.0.D0) THEN
        ITEST1 = ITEST1 + 1
        I = IKLE(IELEM,I2)
!
        IKLE(IELEM,I2) = IKLE(IELEM,I3)
        IKLE(IELEM,I3) = I
      ENDIF
!
      RETURN
      END
