!                       *****************
                        SUBROUTINE IMPRIM
!                       *****************
!
     &(NPOIN1,NPOIN,TYPELE,NELEM,TITRE,MAILLE,PRECIS)
!
!***********************************************************************
! STBTEL V5P2
!***********************************************************************
!
!brief    General information listing printout
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| NPOIN1     | -->| Number of nodes provided by the mesh generator
!| NPOIN      | -->| Actual number of nodes
!| TYPELE     | -->| Element type
!| NELEM      | -->| Number of elements
!| TITRE      | -->| Title
!| MAILLE     | -->| Name of the mesh generator
!| PRECIS     | -->| Format used to read node coordinates
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
!
      INTEGER, INTENT(IN) :: NPOIN1, NPOIN, NELEM
!
      CHARACTER(LEN=11), INTENT(IN) :: TYPELE
      CHARACTER(LEN=80), INTENT(IN) :: TITRE
      CHARACTER(LEN=9), INTENT(IN) ::  MAILLE
      CHARACTER(LEN=6), INTENT(IN) ::  PRECIS
!
!-----------------------------------------------------------------------
!
      WRITE(LU,3010) MAILLE
!
 3010 FORMAT(/,1X,'MESH GENERATOR : ',A9,/,
     &         1X,'--------------')
!
      IF (MAILLE(1:8).EQ.'SUPERTAB') WRITE(LU,3020) PRECIS
!
 3020 FORMAT(1X,'(COORDINATES OF NODES ARE READ IN ',A6,' PRECISION)',/)
!
      WRITE(LU,3030) TITRE,NPOIN1,NPOIN,NELEM,TYPELE
!
 3030 FORMAT(//,1X,'DATAS READ IN THE UNIVERSAL FILE',
     &        /,1X,'---------------------------------',/
     &        /,1X,'TITLE OF THE MESH                 : ',A72,
     &        /,1X,'REAL NUMBER OF POINTS             : ',I11,
     &        /,1X,'MAX. NUMBER GIVEN BY THE MESH GENERATOR: ',I11,
     &        /,1X,'TOTAL NUMBER OF ELEMENTS           : ',I11,
     &        /,1X,'TYPE OF ELEMENTS                   :      ',A11)
!
      RETURN
      END
