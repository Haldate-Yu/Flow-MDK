# upstream_Q_Z
# Temps (s) Cote Debit
         S
<#list loiBaseDataList as baseItem>
${baseItem.timeStep?c} 505 ${baseItem.waterFlow?c}
</#list>