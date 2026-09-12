!                       *****************
                        SUBROUTINE DECOUP
!                       *****************
!
     &(ISURC,X,Y,IKLE,NCOLOR,IFABOR, NELEM2,NPOIN2,COLOR)
!
!***********************************************************************
!  STBTEL V6P2
!***********************************************************************
!
!brief    Split over-constrained triangles in 3 triangles
!+           by adding a extra node at the barycentric location
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| ISURC          |-->| To-be-split over-constrained element number
!| X,Y            |<->| Mesh coordinates
!| IKLE           |<->| Connectivity table
!| NCOLOR         |<->| Array of node colours
!| IFABOR         |<->| Array of neighbouring elements
!| NELEM2         |<->| New number of elements after split
!| NPOIN2         |<->| New number of nodes after split
!| COLOR          |<->| Colours by node from the geo file
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELMAX
      IMPLICIT NONE
!
      DOUBLE PRECISION, INTENT(INOUT) :: X(*) , Y(*)
      INTEGER, INTENT(IN) :: ISURC
      INTEGER, INTENT(INOUT) :: NELEM2 , NPOIN2
      INTEGER, INTENT(INOUT) :: IKLE(NELMAX,4) , NCOLOR(*)
      INTEGER, INTENT(INOUT) :: IFABOR(NELMAX,*)
      LOGICAL, INTENT(INOUT) :: COLOR
!
      INTEGER KELEM
      INTEGER IFAC , ICOLOR , I , I1 , I2 , I3
!
!
!
!=======================================================================
!     COMPUTE THE ADDED NODE COORDINATES (NODE NUMBER NPOIN2)
!=======================================================================
!
      NPOIN2 = NPOIN2 + 1
      I1 = IKLE(ISURC,1)
      I2 = IKLE(ISURC,2)
      I3 = IKLE(ISURC,3)
!
      X(NPOIN2) = (X(I1) + X(I2) + X(I3))/3.D0
      Y(NPOIN2) = (Y(I1) + Y(I2) + Y(I3))/3.D0
!
!=======================================================================
!     DEFINE THE COLOUR OF THE ADDED NODE (C'EST CELLE DU NOEUD NON POINT
!     ( = TO THE COLOUR OF THE NEIGHBOURING INTERIOR NODE )
!=======================================================================
!
      IF (COLOR) THEN
        DO IFAC=1,3
          IF(IFABOR(ISURC,IFAC).GT.0) ICOLOR = IFABOR(ISURC,IFAC)
        ENDDO
!
        DO I=1,3
          IF(IKLE(ICOLOR,I).NE.I1.AND.IKLE(ICOLOR,I).NE.I2.AND.
     &       IKLE(ICOLOR,I).NE.I3)
     &       NCOLOR(NPOIN2) = NCOLOR(IKLE(ICOLOR,I))
        ENDDO
      ENDIF
!
!=======================================================================
!     UPDATED IKLE : ELEMENT (1,2,4) KEEPS THE ELEMENT NUMBER  ISURC
!                    ELEMENT (2,3,4) TAKES THE ELEMENT NUMBER NELEM2+1
!                    ELEMENT (3,1,4) TAKES THE ELEMENT NUMBER NELEM2+2
!=======================================================================
!
      IKLE(ISURC,3) = NPOIN2
!
      NELEM2 = NELEM2 + 1
      IKLE(NELEM2,1) = I2
      IKLE(NELEM2,2) = I3
      IKLE(NELEM2,3) = NPOIN2
!
      KELEM = IFABOR(ISURC,2)
      IFABOR(NELEM2,1) = KELEM
      IFABOR(NELEM2,2) = NELEM2+1
      IFABOR(NELEM2,3) = ISURC
      IF (KELEM.GT.0) THEN
        IF (IFABOR(KELEM,1).EQ.ISURC) IFABOR(KELEM,1) = NELEM2
        IF (IFABOR(KELEM,2).EQ.ISURC) IFABOR(KELEM,2) = NELEM2
        IF (IFABOR(KELEM,3).EQ.ISURC) IFABOR(KELEM,3) = NELEM2
      ENDIF
      IFABOR(ISURC,2) = NELEM2
!
      NELEM2 = NELEM2 + 1
      IKLE(NELEM2,1) = I3
      IKLE(NELEM2,2) = I1
      IKLE(NELEM2,3) = NPOIN2
!
      KELEM = IFABOR(ISURC,3)
      IFABOR(NELEM2,1) = IFABOR(ISURC,3)
      IFABOR(NELEM2,2) = ISURC
      IFABOR(NELEM2,3) = NELEM2-1
      IF (KELEM.GT.0) THEN
        IF (IFABOR(KELEM,1).EQ.ISURC) IFABOR(KELEM,1) = NELEM2
        IF (IFABOR(KELEM,2).EQ.ISURC) IFABOR(KELEM,2) = NELEM2
        IF (IFABOR(KELEM,3).EQ.ISURC) IFABOR(KELEM,3) = NELEM2
      ENDIF
      IFABOR(ISURC,3) = NELEM2
!
!=======================================================================
!
      RETURN
      END
