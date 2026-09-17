# inflow_1
# Temps (s) Debit
         S
<#list loiBaseDataList as baseItem>
${baseItem.timeStep?c} ${baseItem.waterFlow?c}
</#list>
