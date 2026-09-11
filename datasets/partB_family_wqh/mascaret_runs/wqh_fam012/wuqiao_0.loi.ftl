# upstream_Q_Z
# Temps (s) Cote Debit
         S
<#list loiBaseDataList as baseItem>
${baseItem.timeStep?c} ${baseItem.waterLevel?c} ${baseItem.waterFlow?c}
</#list>
