!                       *****************
                        SUBROUTINE LECFAS
!                       *****************
!
     & (X, Y, IKLE, NCOLOR, TFAST1, TFAST2, ADDFAS,
     &  NGEO , NFO1)
!
!***********************************************************************
!     STBTEL V5P2
!***********************************************************************
!
!brief    Reading revlevant information from file created by the
!+           FASTTABS mesh generator
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| X,Y           |-->| Mesh coordinates
!| IKLE          |<->| Connectivity
!| NCOLOR        |<--| Array of node colours for the boundary conditions
!| TFAST1,2      |-->| Working array (fasttabs)
!| ADDFAS        |-->| Use of boundary conditions (fasttabs)
!| NGEO          |-->| Index refering to the mesh generator file
!| NFO1          |-->| Index refering to the triangle trigrid file
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      USE DECLARATIONS_STBTEL, ONLY: NELEM,NPOIN,NELMAX
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) :: NGEO, NFO1
      INTEGER, INTENT(INOUT) :: IKLE(NELMAX,4)
      INTEGER, INTENT(INOUT) :: NCOLOR(*)
      INTEGER, INTENT(INOUT) :: TFAST1(*),TFAST2(*)
      LOGICAL, INTENT(IN) :: ADDFAS
      DOUBLE PRECISION, INTENT(INOUT) :: X(*), Y(*)
!
!     LOCAL VARIABLES
      INTEGER ITYPND,IPOIN,IELEM,IP,IE, IGC,I,J
      INTEGER ELMLOC(8)
      REAL    U,V
      CHARACTER(LEN=80) LIGNE
!
      IPOIN=0
      IELEM=0
      DO I=1,NPOIN
        TFAST1(I)=  -1
      ENDDO
!
!     PROCESSING GEOMERTY
!     FIRST PASS, DEALING WITH ELEMENTS
!
      REWIND (NGEO)
 10   READ (NGEO, '(A)',ERR=8000, END=1000) LIGNE
      IF (LIGNE(1:2).EQ.'GE') THEN
        IELEM=IELEM+1
        READ(LIGNE(4:80),*,ERR=8000,END=9000) IE, (ELMLOC(J),J=1,8)
!
!     PROCESSING DEPENDING ON THE ELEMENT TYPE
!
!
        IF (ELMLOC(8).NE.0) THEN
!
!       QUADRANGLE QUADRATIQUE
!-      REQUIRES A SPLIT OF ELEMENTS
!-      REMOVES NODES
!
! -     1ST ELEMENT
!
          IKLE(IELEM,1)=ELMLOC(1)
          IKLE(IELEM,2)=ELMLOC(3)
          IKLE(IELEM,3)=ELMLOC(5)
!
! -     2ND ELEMENT
!
          IELEM=IELEM+1
          IKLE(IELEM,1)=ELMLOC(5)
          IKLE(IELEM,2)=ELMLOC(7)
          IKLE(IELEM,3)=ELMLOC(1)
        ELSEIF (ELMLOC(6).NE.0) THEN
!
!       TRIANGLE QUADRATIQUE
!-      REMOVES NODES
!
          IKLE(IELEM,1)=ELMLOC(1)
          IKLE(IELEM,2)=ELMLOC(3)
          IKLE(IELEM,3)=ELMLOC(5)
        ELSEIF (ELMLOC(4).NE.0) THEN
!
!       QUADRANGLE LINEAIRE
!-      REQUIRES A SPLIT OF ELEMENTS
!
! -     1ST ELEMENT
!
          IKLE(IELEM,1)=ELMLOC(1)
          IKLE(IELEM,2)=ELMLOC(2)
          IKLE(IELEM,3)=ELMLOC(3)
!
! -     2ND ELEMENT
!
          IELEM=IELEM+1
          IKLE(IELEM,1)=ELMLOC(3)
          IKLE(IELEM,2)=ELMLOC(4)
          IKLE(IELEM,3)=ELMLOC(1)
        ELSE
!
!       TRIANGLE LINEAIRE
!
          DO I=1,3
            IKLE(IELEM,I)=ELMLOC(I)
          ENDDO
        ENDIF
!
      ENDIF
      GO TO 10
!
!     PROCESSING THE GEOMETRY
!     SECOND PASS, DEALING WITH NODES
!
 1000 CONTINUE
      REWIND (NGEO)
 20   READ (NGEO, '(A)',ERR=8000, END=1010) LIGNE
      IF (LIGNE(1:3).EQ.'GNN') THEN
        IPOIN=IPOIN+1
        READ(LIGNE(4:70),*,ERR=8000,END=9000)IP,X(IPOIN),Y(IPOIN)
        TFAST1(IP)=IPOIN
      ENDIF
      GO TO 20
 1010 CONTINUE
!
! -   CONVERT NODE AND ELEEMNT NUMBERS
!
      DO I=1,NELEM
        DO J=1,3
          IKLE(I,J)=TFAST1(IKLE(I,J))
        ENDDO
      ENDDO
!
!     PROCESSING BOUNDARY CONDITIONS IF REQUIRED
!
      IF (.NOT.ADDFAS) THEN
        RETURN
!       ------
      ENDIF
! -------------------
      DO I=1,NPOIN
        TFAST1(I)=  0
      ENDDO
      REWIND (NFO1)
 30   READ (NFO1, '(A)',ERR=8010, END=2000) LIGNE
      IF (LIGNE(1:3).EQ.'BCN') THEN
!
!     SECTION BCN : NODAL BOUNDARY CONDITION
!
        READ(LIGNE(4:70),*,ERR=8010,END=9010)ITYPND
        IF (ITYPND.EQ.200) THEN
!
!       FASTTABS BOUNDARY CONDITION = EXIT HEAD
!
          NCOLOR(IP)=1
        ELSEIF (ITYPND.EQ.1200) THEN
!
!       FASTTABS BOUNDARY CONDITION = SLIP EXIT HEAD
!
          NCOLOR(IP)=11
        ELSEIF (ITYPND.EQ.1100) THEN
!
!       FASTTABS BOUNDARY CONDITION = VELOCITY
!
          NCOLOR(IP)=9
        ENDIF
      ELSEIF (LIGNE(1:3).EQ.'BQL') THEN
!
!     SECTION BQL : NODAL BOUNDARY CONDITION
!
        READ(LIGNE(4:70),*,ERR=8010,END=9010) IGC, U, V
        TFAST1(IGC)=8
      ELSEIF (LIGNE(1:3).EQ.'BHL') THEN
!
!     SECTION BHL : NODAL BOUNDARY CONDITION
!
        READ(LIGNE(4:70),*,ERR=8010,END=9010) IGC, U
        TFAST2(IGC)=1
      ENDIF
      GO TO 30
 2000 CONTINUE
!
!     READING THE NFO1 (BC) FILE ONCE MORE TO GET TO SECTIONS GC
!
      IGC=0
      REWIND (NFO1)
 40   READ (NFO1, '(A)',ERR=8010, END=3000) LIGNE
      IF (LIGNE(1:3).EQ.'GC') THEN
        IGC=IGC+1
        READ(LIGNE(4:70),*,ERR=8010,END=9010)IE,
     &                (TFAST2(I),I=1,IE)
        DO I=1,IE
          NCOLOR(TFAST2(I))=TFAST1(IGC)
        ENDDO
      ENDIF
      GO TO 40
 3000 RETURN
 8000 CONTINUE
      WRITE (LU,4001)
 4001 FORMAT (//,1X,'****************************'
     &        ,/,1X,'SUBROUTINE LECFAS :'
     &        ,/,1X,'ERROR READING FASTTABS FILE.'
     &        ,/,1X,'****************************')
      CALL PLANTE(1)
      STOP
 9000 CONTINUE
      WRITE (LU,4011)
 4011 FORMAT (//,1X,'***************************************'
     &        ,/,1X,'SUBROUTINE LECFAS : UNEXPECTED END OF'
     &        ,/,1X,'FASTTABS FILE ENCOUNTERED'
     &        ,/,1X,'***************************************')
      CALL PLANTE(1)
      STOP
 8010 CONTINUE
      WRITE (LU,4021)
 4021 FORMAT (//,1X,'***************************************'
     &        ,/,1X,'SUBROUTINE LECFAS : ERROR READING'
     &        ,/,1X,'FASTTABS BOUNDARY CONDITION FILE'
     &        ,/,1X,'***************************************')
      CALL PLANTE(1)
      STOP
 9010 CONTINUE
      WRITE (LU,4031)
 4031 FORMAT (//,1X,'***************************************'
     &        ,/,1X,'SUBROUTINE LECFAS : END OF'
     &        ,/,1X,'FASTTABS BOUNDARY CONDITION FILE ENCOUNTERED'
     &        ,/,1X,'***************************************')
      CALL PLANTE(1)
      STOP
      END
