T Q(1) Q(2) Q(3) Q(4) Q(5)
s m3/s m3/s m3/s m3/s m3/s
<#list loiBaseDataList as baseItem>
${baseItem.timeStep?c} ${baseItem.dataList[0]?c} ${baseItem.dataList[1]?c} ${baseItem.dataList[2]?c} ${baseItem.dataList[3]?c} ${baseItem.dataList[4]?c}
</#list>
