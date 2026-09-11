!                       *****************
                        SUBROUTINE INISIM
!                       *****************
!
     &(NPOIN1,TYPELE,INOP5,NGEO)
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    Count the actual number of nodes and number of elemnts
!+           as well as the length of the array NOP5 in the SIMAIL
!+           mesh generator file
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
      USE DECLARATIONS_STBTEL, ONLY: NELEM,MESH,NDP,NPOIN
!
      IMPLICIT NONE
      !
      INTEGER, INTENT(INOUT) :: NPOIN1,INOP5
      INTEGER, INTENT(IN) :: NGEO
      CHARACTER(LEN=11), INTENT(INOUT) :: TYPELE
!
      INTEGER IA(32),LONG,I,J,NTASD,MESHT,MESHQ
!
!=======================================================================
!     INITIALISATION
!=======================================================================
!
      REWIND NGEO
      NPOIN  = 0
      NPOIN1 = 0
      NELEM  = 0
!
!=======================================================================
!     PARTIALLY READ THE 1ST RECORD
!=======================================================================
!
      READ(NGEO,ERR=110,END=120) LONG,(IA(I),I=1,MIN(LONG,32))
!
!=======================================================================
!     PARTIALLY READ ARRAY NOP0
!     COUNT THE NUMBER OF ASSOCIATED ARRAYS, NTASD
!=======================================================================
!
      READ(NGEO,ERR=110,END=120) LONG,(IA(I),I=1,32)
      NTASD = IA(32)
!
!=======================================================================
!     READ THE ARRAY NOP1 AND ASSOCIATED ARRAYS
!=======================================================================
!
      IF (NTASD.GT.0) THEN
        READ(NGEO,ERR=110,END=120) LONG,(IA(I),I=1,MIN(LONG,32))
        DO I=1,NTASD
          READ(NGEO,ERR=110,END=120) LONG,(IA(J),J=1,MIN(LONG,32))
        ENDDO
      ENDIF
!
!=======================================================================
!     READ THE ARRAY NOP2
!     READ THE NUMBER OF NODES, NUMBER OF ELEMENTS, THE TYPE OF ELEMENTS
!     AND THE LENGTH OF THE ARRAY NOP5 (IKLE)
!     SET THE VALUES READ TO THE RELEVANT VARIABLES
!=======================================================================
!
      READ(NGEO,ERR=110,END=120) LONG,(IA(I),I=1,MIN(LONG,32))
      NPOIN1 = IA(15)
      NELEM  = IA(5)
      MESHT  = IA(8)
      MESHQ  = IA(9)
      INOP5  = IA(26)
!
      NPOIN = NPOIN1
!
!=======================================================================
!     CHANGING THE MESH VALUES TO THE TELEMAC STANDARD
!=======================================================================
!
      IF (MESHQ.NE.0) THEN
        MESH = 2
        NDP  = 4
        TYPELE = 'QUADRANGLES'
      ELSEIF (MESHT.NE.0) THEN
        MESH = 3
        NDP  = 3
        TYPELE = 'TRIANGLES  '
      ELSE
        WRITE(LU,3100)
        CALL PLANTE(1)
        STOP
      ENDIF
!
      GOTO 20
!
 110  CONTINUE
      WRITE(LU,4100)
 120  CONTINUE
      WRITE(LU,4200)
!
20    CONTINUE
!
!=======================================================================
!     ISTING RESULTS
!=======================================================================
!
 3100 FORMAT(/,'*************************************************'
     &      ,/,'INISIM : TELEMAC DOESN''T WORK WITH MESHES MIXING '
     &      ,/,'         TRIANGLES AND QUADRILATERALS',
     &      /,'**************************************************')
 4100 FORMAT(//,'*************************************',/,
     &          'INISIM : ERROR IN READING FILE SIMAIL',/,
     &          '*************************************',//)
 4200 FORMAT(//,'*************************************************',/,
     &          'INISIM : ATTEMPT TO READ AFTER END OF FILE SIMAIL',/,
     &          '*************************************************',//)
!
      RETURN
      END
