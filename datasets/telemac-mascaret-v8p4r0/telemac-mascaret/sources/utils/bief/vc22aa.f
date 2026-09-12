!                   *****************
                    SUBROUTINE VC22AA
!                   *****************
!
     &(XMUL,SF,SU,SV,F,U,V,XEL,YEL,SURFAC,
     & IKLE1,IKLE2,IKLE3,NELEM,NELMAX,W1,W2,W3)
!
!***********************************************************************
! BIEF   V8P5
!***********************************************************************
!
!brief    COMPUTES THE FOLLOWING VECTOR IN FINITE ELEMENTS:
!code
!+
!+                  /      DPSI     DPSI         DF      DF
!+      V  = XMUL  /   ( U ---- + V ---- ) * ( U --  + V -- ) D(OMEGA)
!+       I        /OMEGA    DX       DY          DX      DY
!+
!+    PSI(I) IS A BASE OF TYPE P1 TRIANGLE
!+
!+    F, U AND V ARE VECTORS
!
!warning  THE JACOBIAN MUST BE POSITIVE
!warning  THE RESULT IS IN W IN NOT ASSEMBLED FORM
!
!history  C.-T. PHAM , A. MANSAR (LNHE)
!+        19/04/21
!+        V8P3
!+        Creation from VC03AA
!
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!| F              |-->| FUNCTION USED IN THE VECTOR FORMULA
!| IKLE1          |-->| FIRST POINT OF TRIANGLES
!| IKLE2          |-->| SECOND POINT OF TRIANGLES
!| IKLE3          |-->| THIRD POINT OF TRIANGLES
!| NELEM          |-->| NUMBER OF ELEMENTS
!| NELMAX         |-->| MAXIMUM NUMBER OF ELEMENTS
!| SF             |-->| BIEF_OBJ STRUCTURE OF F
!| SU             |-->| BIEF_OBJ STRUCTURE OF U
!| SV             |-->| BIEF_OBJ STRUCTURE OF V
!| SURFAC         |-->| AREA OF TRIANGLES
!| U              |-->| FUNCTION USED IN THE VECTOR FORMULA
!| V              |-->| FUNCTION USED IN THE VECTOR FORMULA
!| W1             |<--| RESULT IN NON ASSEMBLED FORM
!| W2             |<--| RESULT IN NON ASSEMBLED FORM
!| W3             |<--| RESULT IN NON ASSEMBLED FORM
!| XEL            |-->| ABSCISSAE OF POINTS IN THE MESH, PER ELEMENT
!| XMUL           |-->| MULTIPLICATION COEFFICIENT
!| YEL            |-->| ORDINATES OF POINTS IN THE MESH, PER ELEMENT
!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
!
      USE BIEF, EX_VC22AA => VC22AA
!
      USE DECLARATIONS_SPECIAL
      IMPLICIT NONE
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER, INTENT(IN) :: NELEM,NELMAX
      INTEGER, INTENT(IN) :: IKLE1(NELMAX),IKLE2(NELMAX),IKLE3(NELMAX)
!
      DOUBLE PRECISION, INTENT(IN)   :: XEL(NELMAX,*),YEL(NELMAX,*)
      DOUBLE PRECISION, INTENT(INOUT):: W1(NELMAX),W2(NELMAX),W3(NELMAX)
      DOUBLE PRECISION, INTENT(IN)   :: SURFAC(NELMAX)
      DOUBLE PRECISION, INTENT(IN)   :: XMUL
!
!     STRUCTURES OF F, U, V AND REAL DATA
!
      TYPE(BIEF_OBJ), INTENT(IN) :: SF,SU,SV
      DOUBLE PRECISION, INTENT(IN) :: F(*),U(*),V(*)
!
!+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
!
      INTEGER IELEM,IELMF,IELMU,IELMV
      DOUBLE PRECISION X2,Y2,X3,Y3,F1,F2,F3,U1,U2,U3,V1,V2,V3,U123,V123
      DOUBLE PRECISION XSUR48,COEF
      DOUBLE PRECISION UU123,VV123,UV123,GRADFX,GRADFY
!
!-----------------------------------------------------------------------
!
      XSUR48 = XMUL / 48.D0
!
!-----------------------------------------------------------------------
!
      IELMF=SF%ELM
      IELMU=SU%ELM
      IELMV=SV%ELM
!
!-----------------------------------------------------------------------
!
!     F, U, V ARE LINEAR
!
      IF(IELMF.EQ.11.AND.IELMU.EQ.11.AND.IELMV.EQ.11) THEN
!
        DO IELEM = 1 , NELEM
!
          X2 = XEL(IELEM,2)
          X3 = XEL(IELEM,3)
          Y2 = YEL(IELEM,2)
          Y3 = YEL(IELEM,3)
!
          F1 = F(IKLE1(IELEM))
          F2 = F(IKLE2(IELEM)) - F1
          F3 = F(IKLE3(IELEM)) - F1
!
          U1 = U(IKLE1(IELEM))
          U2 = U(IKLE2(IELEM))
          U3 = U(IKLE3(IELEM))
          V1 = V(IKLE1(IELEM))
          V2 = V(IKLE2(IELEM))
          V3 = V(IKLE3(IELEM))
!
          U123  = U1+U2+U3
          V123  = V1+V2+V3
          UU123 = U1**2+U2**2+U3**2
          VV123 = V1**2+V2**2+V3**2
          UV123 = U1*V1+U2*V2+U3*V3
!
          GRADFX =  F2*Y3-F3*Y2
          GRADFY = -F2*X3+F3*X2
!
          COEF = XSUR48 / SURFAC(IELEM)
!
          W2(IELEM) = ( Y3*GRADFX*(U123**2+UU123)
     &                 -X3*GRADFY*(V123**2+VV123)
     &                 +(-X3*GRADFX+Y3*GRADFY)*(U123*V123+UV123))*COEF
          W3(IELEM) = (-Y2*GRADFX*(U123**2+UU123)
     &                 +X2*GRADFY*(V123**2+VV123)
     &                 +( X2*GRADFX-Y2*GRADFY)*(U123*V123+UV123))*COEF
          W1(IELEM) = -W2(IELEM)-W3(IELEM)
!
        ENDDO ! IELEM
!
!-----------------------------------------------------------------------
!
      ELSE
!
!-----------------------------------------------------------------------
!
        WRITE(LU,101) IELMF,SF%NAME
        WRITE(LU,201) IELMU,SU%NAME
        WRITE(LU,301)
101     FORMAT(1X,'VC22AA (BIEF) :',/,
     &         1X,'DISCRETIZATION OF F:',1I6,
     &         1X,'REAL NAME: ',A6)
201     FORMAT(1X,'DISCRETIZATION OF U:',1I6,
     &         1X,'REAL NAME: ',A6)
301     FORMAT(1X,'CASE NOT IMPLEMENTED')
        CALL PLANTE(0)
        STOP
!
      ENDIF
!
!-----------------------------------------------------------------------
!
      RETURN
      END
