!                       *****************
                        SUBROUTINE SHUFLE
!                       *****************
!
     &(IKLE,X)
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Renumbering of the elements
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| IKLE      |<->| Connectivity
!| X         |-->| Meworking array
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL
      USE INTERFACE_STBTEL, EX_SHUFLE => SHUFLE
      IMPLICIT NONE
!
      INTEGER, INTENT(INOUT) :: IKLE(NELMAX,4)
      DOUBLE PRECISION, INTENT(IN) :: X(*)
!
      INTEGER IELEM , I1 , I2 , I3 , I4 , I
!
      DOUBLE PRECISION XA
!
!
!=======================================================================
!
      DO I = 1 , (NELEM-4)/2 , 2
        CALL ECHELE (IKLE,I,NELEM-I+1)
      ENDDO
!
!=======================================================================
!
      IF(NDP.EQ.4) THEN
!
        DO IELEM = 1 , NELEM
!
          I1 = IKLE(IELEM,1)
          I2 = IKLE(IELEM,2)
          I3 = IKLE(IELEM,3)
          I4 = IKLE(IELEM,4)
          XA = X(I1)
          IF(XA.LT.X(I2)) THEN
            XA = X(I2)
            IKLE(IELEM,1) = I2
            IKLE(IELEM,2) = I3
            IKLE(IELEM,3) = I4
            IKLE(IELEM,4) = I1
          ENDIF
          IF(XA.LT.X(I3)) THEN
            XA = X(I3)
            IKLE(IELEM,1) = I3
            IKLE(IELEM,2) = I4
            IKLE(IELEM,3) = I1
            IKLE(IELEM,4) = I2
          ENDIF
          IF(XA.LT.X(I4)) THEN
            IKLE(IELEM,1) = I4
            IKLE(IELEM,2) = I1
            IKLE(IELEM,3) = I2
            IKLE(IELEM,4) = I3
          ENDIF
!
        ENDDO
!
      ELSEIF(NDP.EQ.3) THEN
!
        DO IELEM = 1 , NELEM
!
          I1 = IKLE(IELEM,1)
          I2 = IKLE(IELEM,2)
          I3 = IKLE(IELEM,3)
          XA = X(I1)
          IF(XA.LT.X(I2)) THEN
            XA = X(I2)
            IKLE(IELEM,1) = I2
            IKLE(IELEM,2) = I3
            IKLE(IELEM,3) = I1
          ENDIF
          IF(XA.LT.X(I3)) THEN
            IKLE(IELEM,1) = I3
            IKLE(IELEM,2) = I1
            IKLE(IELEM,3) = I2
          ENDIF
!
        ENDDO
!
      ELSE
!
        WRITE(LU,*) 'UNKNOWN MESH IN SHUFLE'
        CALL PLANTE(1)
        STOP
!
      ENDIF
!
      RETURN
      END
