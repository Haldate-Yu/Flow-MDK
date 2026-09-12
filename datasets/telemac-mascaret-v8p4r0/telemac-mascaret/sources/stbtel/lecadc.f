!                       *****************
                        SUBROUTINE LECADC
!                       *****************
!
     &( X , Y , ZF , IKLE , NGEO )
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Reading the geometry file created by ADCIRC
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| X,Y      |-->| Mesh coordinates
!| X1,Y1    |-->| Mesh coordinates read as single precision
!| IKLE     |<->| Connectivity
!| TITRE    |<->| Title of the study
!| MESH     |<--| Mesh
!| NDP      |-->| Number of nodes per element
!| NPOIN    |<--| Total number of nodes in the mesh
!| NELEM    |<--| Total number of element in the mesh
!| NPMAX    |-->| Actual size of the node-based x and y arrays
!|          |   | (npmax = npoin + 0.1*nelem)
!| NELMAX   |-->| Actual size of the element6based arrays
!|          |   | (nelmax = nelem + 0.2*nelem)
!| NRES     |-->| Index refering to the serafin file
!| NGEO     |-->| Index refering to the mesh generator file
!| NLIM     |-->| Index refering to the dynam file
!| NFO1     |-->| Index refering to the triangle trigrid file
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELEM,NPOIN,NELMAX
!
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) :: NGEO
      INTEGER, INTENT(INOUT) :: IKLE(NELMAX,4)
      DOUBLE PRECISION, INTENT(INOUT) :: X(*) , Y(*),ZF(*)
!
      INTEGER I,J,IBID
!
!
!=======================================================================
!     INITIALISATION
!=======================================================================
!
!     REWIND NGEO
!
!
!=======================================================================
!    READING COORDINATES
!=======================================================================
!
      DO I=1,NPOIN
        READ(NGEO,*) J,X(I),Y(I),ZF(I)
        IF(I.NE.J) THEN
          WRITE(LU,*) 'ERROR IN THE LIST OF COORDINATES LINE ',I
          CALL PLANTE(1)
          STOP
        ENDIF
      ENDDO
!
!=======================================================================
!     READING THE CONNECTIVITY ARRAY IKLE
!=======================================================================
!
      DO I=1,NELEM
        READ(NGEO,*) J,IBID,IKLE(I,1),IKLE(I,2),IKLE(I,3)
      ENDDO
!
!=======================================================================
!
      RETURN
      END
