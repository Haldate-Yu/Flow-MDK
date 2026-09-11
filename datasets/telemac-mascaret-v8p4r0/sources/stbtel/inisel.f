!                       *****************
                        SUBROUTINE INISEL
!                       *****************
!
     &(NPOIN1,TYPELE,STD,NSFOND,FUSION,IHAUT,NGEO,NFO1)
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Count the actual number of nodes and elemnts of a
!+           SELAFIN file
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| NPOIN1        |<--| Actual number of nodes in the mesh
!|               |   | (npoin is the max node index because supertab
!|               |   |  keeps holes in its node numbering
!| TYPELE        |-->| Element types
!| MESH          |<--| Mesh
!| NDP           |-->| Number of nodes per element
!| NPOIN         |<--| Total number of nodes in the mesh
!| NELEM         |<--| Total number of element in the mesh
!| NPMAX         |-->| Actual size of the node-based x and y arrays
!|               |   | (NPMAX = NPOIN + 0.1*NELEM)
!| NELMAX        |-->| Actual size of the element6based arrays
!|               |   | (NELMAX = NELEM + 0.2*NELEM)
!| NRES          |-->| Index refering to the serafin file
!| NGEO          |-->| Index refering to the mesh generator file
!| NLIM          |-->| Index refering to the dynam file
!| NFO1          |-->| Index refering to the triangle trigrid file
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELEM,MESH,NDP,NPOIN,
     &                TYP_ELEM,TYP_BND_ELEM,NPTIR,FFORMAT
      USE INTERFACE_STBTEL, EX_INISEL => INISEL
      USE INTERFACE_HERMES
      IMPLICIT NONE
!
      INTEGER, INTENT(INOUT) :: NPOIN1,NSFOND
      CHARACTER(LEN=11), INTENT(INOUT) :: TYPELE
      CHARACTER(LEN=3), INTENT(IN) :: STD
      LOGICAL, INTENT(IN) :: FUSION
      INTEGER, INTENT(INOUT) :: IHAUT
      INTEGER, INTENT(IN) :: NGEO , NFO1
!
      INTEGER NVAR , I , IB(10)
!
!
      CHARACTER(LEN=16), ALLOCATABLE :: VARUNIT(:), VARNAME(:)
      INTEGER :: IERR
!
!
!=======================================================================
!     LOAD THE FILE AND GO TO 5TH RECORD, SEQUENTIALLY
!=======================================================================
!
      CALL GET_DATA_NVAR(FFORMAT, NGEO, NVAR, IERR)
      CALL CHECK_CALL(IERR, 'INISEL:GET_DATA_NVAR')

      ALLOCATE(VARUNIT(NVAR))
      ALLOCATE(VARNAME(NVAR))
      CALL GET_DATA_VAR_LIST(FFORMAT,NGEO,NVAR,VARNAME,VARUNIT,IERR)
      CALL CHECK_CALL(IERR, 'INISEL:GET_DATA_VAR_LIST')

      DO I=1,NVAR
        IF( VARNAME(I) .EQ. 'FOND            ' .OR.
     &      VARNAME(I) .EQ. 'BOTTOM          ' ) NSFOND = I
        IF( VARNAME(I) .EQ. 'HAUTEUR D''EAU   ' .OR.
     &      VARNAME(I) .EQ. 'WATER DEPTH     ' ) IHAUT = I
      ENDDO

      DEALLOCATE(VARUNIT)
      DEALLOCATE(VARNAME)
!
!=======================================================================
!     SETTING VARIABLES
!=======================================================================
!
!     TEST FOR TRIANGLE
      TYP_ELEM = TRIANGLE_ELT_TYPE
      CALL GET_MESH_NELEM(FFORMAT,NGEO,TYP_ELEM,NELEM,IERR)
      CALL CHECK_CALL(IERR,'inisel:GET_MESH_NELEM:TRIANGLE')
      NDP = 3
      IF(NELEM.EQ.0) THEN
!      TEST FOR QUADRANGLE
        TYP_ELEM = QUADRANGLE_ELT_TYPE
        CALL GET_MESH_NELEM(FFORMAT,NGEO,TYP_ELEM,NELEM,IERR)
        CALL CHECK_CALL(IERR, 'INISEL:GET_MESH_NELEM:QUADRANGLE')
        NDP = 4
        IF(NELEM.EQ.0) THEN
          WRITE(LU,*) 'NO 2D ELEMENTS IN A 2D MESH'
          CALL PLANTE(1)
        ENDIF
      ENDIF
      TYP_BND_ELEM = POINT_BND_ELT_TYPE

      CALL GET_MESH_NPOIN(FFORMAT,NGEO,TYP_ELEM,NPOIN,IERR)
      CALL CHECK_CALL(IERR, 'GET_MESH_NPOIN:TRIA')

      CALL GET_MESH_NPTIR(FFORMAT,NGEO,NPTIR,IERR)

      NPOIN1= NPOIN
!
!=======================================================================
!     READING THE SECOND FILE IN CASE OF FUSION, SEQUENTIALLY
!=======================================================================
!
      IF (FUSION) THEN
!
        CALL GET_MESH_NELEM(FFORMAT,NFO1,TYP_ELEM,IB(1),IERR)
        CALL CHECK_CALL(IERR,'INISEL:GET_MESH_NELEM:TRIANGLE')

        CALL GET_MESH_NPOIN(FFORMAT,NFO1,TYP_ELEM,IB(2),IERR)
        CALL CHECK_CALL(IERR, 'GET_MESH_NPOIN:TRIA')

        CALL GET_MESH_NPOIN_PER_ELEMENT(FFORMAT,NFO1,TYP_ELEM,
     &                                  IB(3),IERR)
!
        NELEM = NELEM + IB(1)
        NPOIN = NPOIN + IB(2)
!
        IF (NDP.NE.IB(3)) THEN
          WRITE(LU,3130)
 3130     FORMAT(' INISEL : TYPES OF MESH INHOMOGENEOUS')
          CALL PLANTE(1)
          STOP
        ENDIF
!
      ENDIF
!
!=======================================================================
!     SET VALUES OF THE MESH THE TELEMAC STANDARD
!=======================================================================
!
      IF (NDP.EQ.4) THEN
        MESH = 2
        TYPELE = 'QUADRANGLES'
      ELSEIF (NDP.EQ.3) THEN
        MESH = 3
        TYPELE = 'TRIANGLES  '
      ELSE
        WRITE(LU,3140) MESH
 3140   FORMAT(' INISEL : TYPE OF MESH NOT AVAILABLE IN TELEMAC,
     &           MESH = ',I4)
        CALL PLANTE(1)
        STOP
      ENDIF
!
      RETURN
      END
