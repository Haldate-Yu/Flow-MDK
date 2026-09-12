!                       *****************
                        SUBROUTINE INTERP
!                       *****************
!
     &(XINIT , YINIT , IKINIT , NPINIT , NEINIT ,
     & X , Y , NPOIN , NPMAX , SHP , ELT)
!
!***********************************************************************
! STBTEL  V5P2
!***********************************************************************
!
!brief    Interpolating bathymetry onto the mesh
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| X,Y         | -->| Mesh coordinates
!| ZF          |<-- | Bottom values
!| XRELV,YRELV | -->| Bathymetric coordinates
!| ZRELV       | -->| Bathymetric values
!| NBAT        | -->| Number of bathymetric values
!| NBOR        | -->| Numbering of the boundary nodes
!| NPTFR       | -->| Number of boundary nodes
!| NFOND       | -->| Logical units of bathymetric files
!| NBFOND      | -->| Number of bathymetric files (5 maxi)
!| FOND        | -->| Names of the bathymetric files
!| DM          | -->| Minimum distance to the doamin border for
!|             |    | The bathymetric interpolation
!| FONTRI      | -->| Whether bathymetric values are in trigrid
!| CORTRI      | -->| Correction of bathymetric value for trigrid
!| MESH        | -->| Mesh
!| NDP         | -->| Number of node per element
!| NPOIN       | -->| Total number of nodes in the mesh
!| NELEM       | -->| Total number of elements in the mesh
!| NPMAX       | -->| Actual siwe of the x and y arrays
!|             |    | (npmax = npoin + 0.1*nelem)
!| NELMAX      | -->| Actual size of the arrays to do with elements
!|             |    | (nelmax = nelem + 0.2*nelem)
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) :: NPINIT, NEINIT, NPOIN,NPMAX
      DOUBLE PRECISION, INTENT(IN) :: XINIT(NPINIT) , YINIT(NPINIT)
      INTEGER, INTENT(IN) :: IKINIT(NEINIT,3)
      INTEGER, INTENT(INOUT) :: ELT(NPMAX)
      DOUBLE PRECISION, INTENT(IN) :: X(NPMAX) , Y(NPMAX)
      DOUBLE PRECISION, INTENT(INOUT) :: SHP(NPMAX,3)
!
      INTEGER IELEM , JELEM , IPOIN
      DOUBLE PRECISION XP,YP,A1,A2,A3,C1,C2,X1,X2,X3,Y1,Y2,Y3
!
!=======================================================================
!
      WRITE(LU,4)
!
4     FORMAT(//,1X,'DATA INTERPOLATION',/,
     &          1X,'------------------',/)
!
      DO IPOIN = 1,NPOIN
!
        XP = X(IPOIN)
        YP = Y(IPOIN)
        C1 = -999999.D0
!
        DO IELEM = 1,NEINIT
          X1 = XINIT(IKINIT(IELEM,1))
          X2 = XINIT(IKINIT(IELEM,2))
          X3 = XINIT(IKINIT(IELEM,3))
          Y1 = YINIT(IKINIT(IELEM,1))
          Y2 = YINIT(IKINIT(IELEM,2))
          Y3 = YINIT(IKINIT(IELEM,3))
          A1 = (X3-X2)*(YP-Y2) - (Y3-Y2)*(XP-X2)
          A2 = (X1-X3)*(YP-Y3) - (Y1-Y3)*(XP-X3)
          A3 = (X2-X1)*(YP-Y1) - (Y2-Y1)*(XP-X1)
          IF (A1.GE.0.AND.A2.GE.0.AND.A3.GE.0) GOTO 30
          C2 = MIN(A1,A2,A3) / ((X3-X2)*(Y1-Y2)-(Y3-Y2)*(X1-X2))
          IF (C2.GT.C1) THEN
            C1 = C2
            JELEM = IELEM
          ENDIF
        ENDDO
!
        WRITE(LU,*) 'EXTRAPOLATION REQUIRED FOR ',
     &              'THE NODE :',IPOIN
        IELEM = JELEM
        X1 = XINIT(IKINIT(IELEM,1))
        X2 = XINIT(IKINIT(IELEM,2))
        X3 = XINIT(IKINIT(IELEM,3))
        Y1 = YINIT(IKINIT(IELEM,1))
        Y2 = YINIT(IKINIT(IELEM,2))
        Y3 = YINIT(IKINIT(IELEM,3))
        A1 = (X3-X2)*(YP-Y2) - (Y3-Y2)*(XP-X2)
        A2 = (X1-X3)*(YP-Y3) - (Y1-Y3)*(XP-X3)
        A3 = (X2-X1)*(YP-Y1) - (Y2-Y1)*(XP-X1)
!
30      CONTINUE
        C1 = (X3-X2)*(Y1-Y2)-(Y3-Y2)*(X1-X2)
        SHP(IPOIN,1) = A1/C1
        SHP(IPOIN,2) = A2/C1
        SHP(IPOIN,3) = A3/C1
        ELT(IPOIN) = IELEM
!
      ENDDO
!
!-----------------------------------------------------------------------
!
      RETURN
      END
