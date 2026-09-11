!                       *****************
                        SUBROUTINE INIFAS
!                       *****************
!
     &(TYPELE,NGEO)
!
!***********************************************************************
!   STBTEL V5P2
!***********************************************************************
!
!brief    Initialisation of variables in the case of FASTAB
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| TYPELE        | <->| Type of elements (triangles)
!| NGEO          |<-->| Unit number of the mesh generator file
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELEM,MESH,NDP,NPOIN
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) ::       NGEO
      CHARACTER(LEN=*), INTENT(INOUT) :: TYPELE
!
      CHARACTER(LEN=80)  LIGNE
      INTEGER       IE,J
      INTEGER       ELMLOC(8)
!
! - INITIALISATION
!
      REWIND (NGEO)
      NPOIN = 0
      NELEM = 0
!
!  - LOOP OVER THE FILE RECORDS AS LONG AS END NOT REACHED
!
 1    CONTINUE
        READ (NGEO, '(A80)', END=9000, ERR=8000) LIGNE
!
! - THE LINE START WITH "GNN" - NODE DEFINITION
!
        IF (LIGNE(1:3).EQ.'GNN') THEN
          NPOIN = NPOIN + 1
        ENDIF
!
! - THE LINE START WITH "GE" - ELEMENT DEFINITION
!
        IF (LIGNE(1:2).EQ.'GE') THEN
          NELEM = NELEM + 1
          READ(LIGNE(4:80),*,ERR=8000,END=9000) IE,
     &     (ELMLOC(J),J=1,8)
          IF (ELMLOC(8).NE.0.OR.
     &         (ELMLOC(4).NE.0.AND.ELMLOC(6).EQ.0) ) THEN
!
! - ADDING ELEMENTS
!
            NELEM = NELEM + 1
          ENDIF
        ENDIF
      GOTO 1
!
 9000 CONTINUE
      TYPELE = 'TRIANGLES  '
      NDP = 3
      MESH = 3
!
      RETURN
!
! - PROCESSING FILE ERRORS
!
 8000 CONTINUE
      WRITE (LU,4001)
 4001 FORMAT (//,1X,'****************************'
     &        ,/,1X,'SUBROUTINE INIFAS :'
     &        ,/,1X,'ERROR READING FASTTABS FILE.'
     &        ,/,1X,'****************************')
      CALL PLANTE(1)
      STOP
      END
