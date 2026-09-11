!                       ****************
                        SUBROUTINE RENUM
!                       ****************
!
     &(X,Y,W,IKLE,NBOR,TRAV1,TRAV2,TAB,NCOLOR,COLOR,NPTFR)
!
!***********************************************************************
! STBTEL  V5P2
!***********************************************************************
!
!brief    Splitting over-constrained triangles in 3 trinagles
!+           adding a node at its barycentre location
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| X,Y       |-->| Mesh coordinates
!| IKLE      |<->| Connectivity
!| TRAV1,2   |<->| Working arrays
!| TAB       |<->| Working arrays
!| NCOLOR    |<--| Array of node colours
!| COLOR     |<->| Whether node colours are stored within the geo
!| NPOIN     |<--| Total number of nodes in the mesh
!| NELEM     |<--| Total number of element in the mesh
!| NPMAX     |-->| Actual size of the node-based x and y arrays
!|           |   | (npmax = npoin + 0.2*nelem)
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELEM,NPOIN,NELMAX
      IMPLICIT NONE
!
      DOUBLE PRECISION, INTENT(INOUT) :: X(*) , Y(*) , W(*)
      INTEGER, INTENT(INOUT) :: TRAV1(*) , TRAV2(*)
      INTEGER, INTENT(INOUT) :: IKLE(NELMAX,3) , NCOLOR(*) , NBOR(*)
      INTEGER, INTENT(INOUT) :: TAB(*)
      LOGICAL, INTENT(IN) :: COLOR
      INTEGER, INTENT(IN) :: NPTFR
!
      INTEGER IPOIN , IELEM , IPTFR , I1 , I2 , TABMAX
!
!
!
!=======================================================================
!     COMPUTE THE NUMBER OF NEIGHBOURING NODES AND ELEMENTS
!=======================================================================
!
      DO IPOIN = 1,NPOIN
        TRAV1(IPOIN) = 0
      ENDDO
!
      DO IELEM = 1,NELEM
        TRAV1(IKLE(IELEM,1)) = TRAV1(IKLE(IELEM,1)) + 2
        TRAV1(IKLE(IELEM,2)) = TRAV1(IKLE(IELEM,2)) + 2
        TRAV1(IKLE(IELEM,3)) = TRAV1(IKLE(IELEM,3)) + 2
      ENDDO
!
      DO IPTFR = 1,NPTFR
        TRAV1(NBOR(IPTFR)) = TRAV1(NBOR(IPTFR)) + 1
      ENDDO
!
!=======================================================================
!     RENUMBER NODES FOLLOWING THE INCREASING ORDER OF ITS NEIGHBOURS
!=======================================================================
!
      TABMAX = 0
!
      DO IPOIN = 1,NPOIN
!
        I1 = TRAV1(IPOIN)
!
        IF (I1.GT.TABMAX) THEN
          DO I2 = TABMAX+1,I1
            TAB(I2) = IPOIN - 1
          ENDDO
          TABMAX = I1
        ELSEIF (I1.LT.TABMAX) THEN
          DO I2 = TABMAX,I1+1,-1
            TAB(I2) = TAB(I2) + 1
            TRAV2(TAB(I2)) = TRAV2(TAB(I2-1)+1)
          ENDDO
        ENDIF
!
        TAB(I1) = TAB(I1) + 1
        TRAV2(TAB(I1)) = IPOIN
!
      ENDDO
!
      DO I1 = 1,TABMAX
        WRITE(LU,*)'TAB(',I1,')=',TAB(I1)
      ENDDO
!
!=======================================================================
!     ASSOCIATED MODIFICATIONS TO VARIOUS VARIABLES
!=======================================================================
!
      DO IPOIN = 1,NPOIN
        TRAV1(TRAV2(IPOIN)) = IPOIN
      ENDDO
!
      DO IELEM = 1,NELEM
        IKLE(IELEM,1) = TRAV1(IKLE(IELEM,1))
        IKLE(IELEM,2) = TRAV1(IKLE(IELEM,2))
        IKLE(IELEM,3) = TRAV1(IKLE(IELEM,3))
      ENDDO
!
      DO IPTFR = 1,NPTFR
        NBOR(IPTFR) = TRAV1(NBOR(IPTFR))
        NBOR(NPTFR+IPTFR) = TRAV1(NBOR(NPTFR+IPTFR))
      ENDDO
!
      DO IPOIN = 1,NPOIN
        W(IPOIN) = X(TRAV2(IPOIN))
      ENDDO
      DO IPOIN = 1,NPOIN
        X(IPOIN) = W(IPOIN)
      ENDDO
!
      DO IPOIN = 1,NPOIN
        W(IPOIN) = Y(TRAV2(IPOIN))
      ENDDO
      DO IPOIN = 1,NPOIN
        Y(IPOIN) = W(IPOIN)
      ENDDO
!
      IF (COLOR) THEN
!
        DO IPOIN = 1,NPOIN
          TRAV1(IPOIN) = NCOLOR(TRAV2(IPOIN))
        ENDDO
        DO IPOIN = 1,NPOIN
          NCOLOR(IPOIN) = TRAV1(IPOIN)
        ENDDO
!
      ENDIF
!
!=======================================================================
!
      RETURN
      END
