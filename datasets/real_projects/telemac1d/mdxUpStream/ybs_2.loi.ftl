# upstream-Q-Z
# Temps (s) Cote Debit
         S
<#list loiBaseDataList as baseItem>
${baseItem.timeStep?c} 500 ${baseItem.waterFlow?c}
</#list>
