!                       *****************
                        SUBROUTINE INISTB
!                       *****************
!
     &(NPOIN1,TYPELE,MAILLE,PRECIS,NGEO,NSEC2,NSEC11,NSEC12)
!
!***********************************************************************
!   STBTEL V5P1
!***********************************************************************
!
!brief    Count the actual number of nodes and elemnts of a
!+           SUPERTAB universal file
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| NPOIN1      |<--| Actual number of nodes in the mesh
!|             |   | (npoin is the max node index because supertab
!|             |   |  keeps holes in its node numbering
!| TYPELE      |-->| Element types
!| MESH        |<--| Mesh
!| NDP         |-->| Number of nodes per element
!| NPOIN       |<--| Total number of nodes in the mesh
!| NELEM       |<--| Total number of element in the mesh
!| NPMAX       |-->| Actual size of the node-based x and y arrays
!|             |   | (npmax = npoin + 0.1*nelem)
!| NELMAX      |-->| Actual size of the element6based arrays
!|             |   | (nelmax = nelem + 0.2*nelem)
!| NRES        |-->| Index refering to the serafin file
!| NGEO        |-->| Index refering to the mesh generator file
!| NLIM        |-->| Index refering to the dynam file
!| NFO1        |-->| Index refering to the triangle trigrid file
!| NSEC11      |-->| Index refering to the area including the nodes
!|             |   |  (simple precision)
!| NSEC12      |-->| Index refering to the area including the nodes
!|             |   |  (double precision)
!| NSEC2       |-->| Index refering to the area including elements
!| NSEC3       |-->| Index refering to the area including the title
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELEM,MESH,NDP,NPOIN
      IMPLICIT NONE
!
      INTEGER, INTENT(INOUT) :: NPOIN1
      CHARACTER(LEN=11), INTENT(INOUT) :: TYPELE
      CHARACTER(LEN=9), INTENT(IN) ::  MAILLE
      CHARACTER(LEN=6), INTENT(INOUT) ::  PRECIS
      INTEGER, INTENT(IN) :: NSEC11 , NSEC12 , NGEO, NSEC2
!
      DOUBLE PRECISION X1
      INTEGER NPOIN2
      INTEGER N1, NSEC
      INTEGER N2
      INTEGER INDI11 , INDI12 , INDIC2
!
      CHARACTER(LEN=2)  MOINS1
      CHARACTER(LEN=4)  BLANC*4
!
!=======================================================================
!     INITIALISATION
!=======================================================================
!
      REWIND NGEO
      NPOIN1  = 0
      NPOIN2  = 0
      NELEM   = 0
      INDI11  = 0
      INDI12  = 0
      INDIC2  = 0
!
!=======================================================================
!     READING THE FILE AND LOOKING FOR THE NUMBERS NSEC1 AND NSEC2
!=======================================================================
!
 10   READ(NGEO,1000,ERR=110,END=120) BLANC,MOINS1
      IF (MOINS1.NE.'-1'.OR.BLANC.NE.'    ') GOTO 10
 1000 FORMAT(A4,A2)
!
 20   READ(NGEO,2000,ERR=110,END=120) NSEC
      IF (NSEC.EQ.-1) THEN
        GOTO 20
!
!=======================================================================
!     NUMBER OF NODES
!=======================================================================
!
!     READING IN SINGLE PRECISION
!
      ELSE IF (NSEC.EQ.NSEC11) THEN
        INDI11 = 1
!
 30     CONTINUE
        READ(NGEO,2000,ERR=110,END=120) NSEC
!
        IF (NSEC.NE.-1) THEN
          NPOIN1 = NPOIN1+1
          NPOIN2 = MAX0(NSEC,NPOIN1)
          GOTO 30
        ELSE
          GOTO 50
        ENDIF
!
!     READING IN DOUBLE PRECISION
!
      ELSE IF (NSEC.EQ.NSEC12) THEN
        INDI12 = 1
!
 31     CONTINUE
        READ(NGEO,2000,ERR=110,END=120) NSEC
!
        IF (NSEC.NE.-1) THEN
          NPOIN1 = NPOIN1+1
          NPOIN2 = MAX0(NSEC,NPOIN1)
        ELSE
          GOTO 50
        ENDIF
!
        READ(NGEO,4000,ERR=110,END=120) X1
!
        GOTO 31
!
!=======================================================================
!     NUMBER AND TYPE OF ELEMENTS
!=======================================================================
!
      ELSE IF (NSEC.EQ.NSEC2) THEN
        INDIC2 = 1
        IF (MAILLE.EQ.'SUPERTAB4') THEN
!     FORMAT SUPERTAB VERSION 4
          READ(NGEO,3000,ERR=110,END=120) N1,N2,MESH
        ELSE
!     FORMAT SUPERTAB VERSION 6
          READ(NGEO,3000,ERR=110,END=120) N1,MESH,N2
        ENDIF
        NELEM = 1
 40     READ(NGEO,2000,ERR=110,END=120) NSEC
        IF (NSEC.NE.-1) THEN
          NELEM = NELEM+1
          GOTO 40
        ELSE
          GOTO 50
        ENDIF
      ENDIF
!
 50   IF ((INDI11.EQ.1.OR.INDI12.EQ.1).AND.INDIC2.EQ.1) THEN
        GOTO 60
      ELSE
        GOTO 10
      ENDIF
!
 110  CONTINUE
      WRITE(LU,4100)
      CALL PLANTE(1)
      STOP
!
 120  CONTINUE
      IF (INDI11.NE.1.AND.INDI12.NE.1) WRITE(LU,4200)
      IF (INDI12.NE.1) WRITE(LU,4300)
      STOP
!
 60   CONTINUE
!
!=======================================================================
!     SETTING VALUES READ TO RELEVANT VARIABLES
!=======================================================================
!
      IF (INDI11.EQ.1) PRECIS='SIMPLE'
      IF (INDI12.EQ.1) PRECIS='DOUBLE'
!
      NELEM =NELEM / 2
!
      NPOIN = NPOIN2
!
!=======================================================================
!     SETTING MESH VARIABLES TO THE TELEMAC STANDARD
!=======================================================================
!
      IF (MESH.EQ.94) THEN
        MESH = 2
        NDP  = 4
        TYPELE = 'QUADRANGLES'
      ELSEIF (MESH.EQ.91) THEN
        MESH = 3
        NDP  = 3
        TYPELE = 'TRIANGLES  '
      ELSE
        WRITE(LU,3140) MESH
 3140   FORMAT(' INISTB : TYPE OF MESH NOT AVAILABLE IN TELEMAC,
     &           MESH = ',I4)
      ENDIF
!
!=======================================================================
!     LISTING RESULTS
!=======================================================================
!
 4100 FORMAT(//,'****************************************',/,
     &          'ERROR IN READING UNIVERSAL FILE (INISTB)',/,
     &          '****************************************')
 4200 FORMAT(//,'********************************************',/,
     &          'END OF THE UNIVERSAL FILE : NO NODE (INISTB)',/,
     &          '********************************************')
 4300 FORMAT(//,'***********************************************',/,
     &          'END OF THE UNIVERSAL FILE : NO ELEMENT (INISTB)',/,
     &          '***********************************************')
 2000 FORMAT(I10)
 3000 FORMAT(3I10)
 4000 FORMAT(D25.16)
!
      RETURN
      END
