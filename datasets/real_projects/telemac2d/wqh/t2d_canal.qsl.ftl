#
#  DEBIT A L'ENTREE ET SURFACE LIBRE A LA SORTIE
#
T       Q(1)    
s       m3/s
<#list loiBaseDataList as baseItem>
${baseItem.timeStep?c} ${baseItem.waterFlow?c}
</#list>
