!                     ***********************
                      SUBROUTINE POINT_STBTEL
!                     ***********************
!
!***********************************************************************
!   STBTEL V5P1
!***********************************************************************
!
!brief    Use to building array pointers and larger array A and IA
!+        Dynamic memory allocation changed it all to just sizing.
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL
      IMPLICIT NONE
!
!=======================================================================
!     PLANING AHEAD FOR THE REMOVAL OF OVER-CONSTRAINED TRIANGLES,
!       NPOIN AND NELEM2 ARE OVER-SIZED
!=======================================================================
!
      NPMAX  = NPOIN +   INT(0.1*NELEM)
      NELMAX = NELEM + 2*INT(0.1*NELEM)
      IF(DIV4) NPMAX  = NPMAX  + 3*NELEM
      IF(DIV4) NELMAX = NELMAX + 3*NELEM
!
      RETURN
      END
