#
#  DEBIT A L'ENTREE ET SURFACE LIBRE A LA SORTIE
#
T       Q(2) Z(1)
s       m3/s m
<#list loiBaseDataList as baseItem>
${baseItem.timeStep?c} ${baseItem.waterFlow?c} ${baseItem.waterLevel?c}
</#list>
