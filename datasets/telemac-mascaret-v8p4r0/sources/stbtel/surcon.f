!                       *****************
                        SUBROUTINE SURCON
!                       *****************
!
     &(X,Y,IKLE,IPO,NBOR,NPTFR,NCOLOR,IFABOR,COLOR)
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Splitting over-constrained triangles
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| X,Y       |<--| Node coordinates
!| IKLE      |<->| Connectivity
!| TRAV1     |<->| Working array
!| NBOR      |-->| Boundary node number
!| NPTFR     |-->| Array of boundary nodes
!| NCOLOR    |<--| Array of node colours
!| IFABOR    |<->| Array of neighbouring elements for each side
!| MESH      |-->| Mesh
!| NDP       |-->| Number of nodes per element
!| NPOIN     |-->| Total number of nodes in the mesh
!| NELEM     |-->| Total number of elements in the mesh
!| NPMAX     |-->| Actual size of the node-based x and y arrays
!|           |   | (npmax = npoin + 0.1*nelem)
!| NELMAX    |-->| Actual size of the element6based arrays
!|           |   | (nelmax = nelem + 0.2*nelem)
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELEM,NPOIN,NELMAX,NPMAX
      USE INTERFACE_STBTEL, EX_SURCON => SURCON
      IMPLICIT NONE
!
      DOUBLE PRECISION, INTENT(INOUT) :: X(*) , Y(*)
      INTEGER, INTENT(INOUT) :: NBOR(*) , IKLE(NELMAX,4) , NCOLOR(*)
      INTEGER, INTENT(INOUT) :: IFABOR(NELMAX,*) , IPO(*)
      LOGICAL, INTENT(INOUT) :: COLOR
      INTEGER, INTENT(IN) :: NPTFR
!
      INTEGER NPOIN2 , NELEM2
      INTEGER ITEST , IELEM , KELEM , ISWAP , KSWAP
      INTEGER I , J , K
      INTEGER :: IP(3) , KP , ISUI(3)
!
      PARAMETER ( ISUI = (/ 2 , 3 , 1 /) )
!
!=======================================================================
!
      WRITE(LU,4050)
!
      NPOIN2 = NPOIN
      NELEM2 = NELEM
      ITEST  = 0
!
!=======================================================================
!     LOOKING FOR OVER-CONSTRAINED TRIANGLES
!=======================================================================
!
      DO K = 1 , NPMAX
        IPO(K) = 0
      ENDDO
!
      DO K = 1 , NPTFR
        IPO(NBOR(K)) = 1
      ENDDO

      DO K = 1 , NELEM
        IF (IPO(IKLE(K,1))+IPO(IKLE(K,2))+IPO(IKLE(K,3)).EQ.3) THEN
!
!     SPLIT TRIANGLE IN 3 OTHERS IF OVER-CONSTRAINED
!
          ITEST  = ITEST + 1
          IF (ITEST.GT.INT(0.1*NELMAX)) THEN
            WRITE(LU,4000) INT(0.1*NELMAX)
            CALL PLANTE(1)
            STOP
          ENDIF
!
          WRITE(LU,4070) X(IKLE(K,1)),Y(IKLE(K,1)),
     &       X(IKLE(K,2)),Y(IKLE(K,2)),X(IKLE(K,3)),Y(IKLE(K,3))
!
          CALL DECOUP (K,X,Y,IKLE,NCOLOR,IFABOR,
     &                 NELEM2,NPOIN2,COLOR)
!
        ENDIF
      ENDDO !K
!
!=======================================================================
!     UPDATE OF NPOIN AND NELEM
!=======================================================================
!
      NPOIN = NPOIN2
      NELEM = NELEM2
!
!=======================================================================
!     SWAP BOUNDARY SEGMENTS THAT HAVE 2 BOUNDARY NODES DE BORD BUT ARE
!     NOT BOUNDARY SEGMENT
!
!     NOTE : IFABOR IS NOT MODIFIED IN WHAT FOLLOWS BECAUSE
!            THE ARRAY WILL NOT BE USED ANYMORE
!=======================================================================
!
      ISWAP = 0
      KSWAP = 0
      DO IELEM = 1,NELEM
        IP(1) = IKLE(IELEM,1)
        IP(2) = IKLE(IELEM,2)
        IP(3) = IKLE(IELEM,3)
        DO I = 1,3
          J = ISUI(I)
          IF(IFABOR(IELEM,I).GT.0.AND.IPO(IP(I))+IPO(IP(J)).EQ.2) THEN
            KELEM = IFABOR(IELEM,I)
!
!     WE CAN BE SURE AT THIS POINT THAT ALL TRIANGLES INCLUDE AT LEAT
!     ONE INTERNAL NODE AND IN THIS CASE ONLY ONE.
!     FOR SURE, K IS NOT EMPTY
!
            IF (IPO(IKLE(KELEM,1)).EQ.0) K=1
            IF (IPO(IKLE(KELEM,2)).EQ.0) K=2
            IF (IPO(IKLE(KELEM,3)).EQ.0) K=3
            KP = IKLE(KELEM,K)
!
            IF ((X(KP)-X(IP(I)))*(Y(IP(ISUI(J)))-Y(IP(I))).GT.
     &          (Y(KP)-Y(IP(I)))*(X(IP(ISUI(J)))-X(IP(I))).AND.
     &          (X(KP)-X(IP(J)))*(Y(IP(ISUI(J)))-Y(IP(J))).LT.
     &          (Y(KP)-Y(IP(J)))*(X(IP(ISUI(J)))-X(IP(J)))) THEN
!
              ISWAP = ISWAP + 1
              IKLE(IELEM,I) = KP
              IKLE(KELEM,ISUI(K)) = IP(ISUI(J))
!
              WRITE(LU,4080) X(IP(I)),Y(IP(I)),
     &                       X(IP(J)),Y(IP(J))
!
            ELSE
!
              KSWAP = KSWAP + 1
!
            ENDIF
          ENDIF
        ENDDO
      ENDDO
!
!=======================================================================
!
      WRITE(LU,4100) ITEST,NPOIN,NELEM,ISWAP
!
      IF (KSWAP.NE.0) THEN
        WRITE(LU,4200) KSWAP
      ENDIF
!
 4000 FORMAT(//,1X,'**************************************************',
     &        /,1X,'THE MAXIMUM NUMBER OF OVERSTRESSED TRIANGLES   ',
     &        /,1X,'IS',I5,' : IT IS GREATER IN YOUR CASE ||',
     &        /,1X,'**************************************************')
 4050 FORMAT(//,1X,'OVERSTRESSED ELEMENTS ARE CANCELLED',/,
     &          1X,'-----------------------------------',/)
 4070 FORMAT   (1X,'ADDITIONAL NODE AT CENTRE OF TRIANGLE :',/,
     &          1X,'(',D9.3,',',D9.3,'),(',D9.3,',',D9.3,'),',
     &             '(',D9.3,',',D9.3,')')
 4080 FORMAT   (1X,'SWAP OF FACE :',/,
     &          1X,'(',D9.3,',',D9.3,'),(',D9.3,',',D9.3,')')
 4100 FORMAT (/,1X,'NUMBER OF CANCELLED ELEMENTS : ',I5,/,
     &          1X,'AFTER BEING CANCELLED :',/,
     &          1X,'          NUMBER OF POINTS      : ',I5,/,
     &          1X,'          NUMBER OF ELEMENTS    : ',I5,//,
     &          1X,'MOREOVER,',I4,' TRIANGLES HAVE BEEN SWAPPED',//)
 4200 FORMAT   (1X,'      BUT',I4,' COULD NOT BE',//)
!
      RETURN
      END
