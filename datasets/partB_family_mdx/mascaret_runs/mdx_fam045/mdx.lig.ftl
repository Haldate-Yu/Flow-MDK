RESULTATS CALCUL,DATE :  8/7/24 11:26 AM
FICHIER RESULTAT MASCARET                                               
----------------------------------------------------------------------- 
 IMAX  =  ${ligBaseDataNum} NBBIEF=    1
 I1,I2 =    1  ${ligBaseDataNum}
 X
<#list ligBaseDataList as data>
    ${data.x1!""}     ${data.x2!""}     ${data.x3!""}     ${data.x4!""}     ${data.x5!""}
</#list>
 Z
<#list ligBaseDataList as data>
    ${data.z1!""}     ${data.z2!""}     ${data.z3!""}     ${data.z4!""}     ${data.z5!""}
</#list>
 Q
<#list ligBaseDataList as data>
    ${data.q1!""}     ${data.q2!""}     ${data.q3!""}     ${data.q4!""}     ${data.q5!""}
</#list>
 FIN
