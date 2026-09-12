#!/bin/bash -ev
###
 # @Author: WangYu
 # @Date: 2023-03-16 09:21:59
 # @LastEditors: WangYu
 # @LastEditTime: 2023-08-09 17:15:37
 # @FilePath: /docker-telemac/docker/setenv.sh
 # @Description: 
 # @copyright: Copyright (c) 2023 by WangYu, All Rights Reserved. 
###

#原版有一个代理，不知道有什么用，暂时先注释，这个会导致镜像构建完后后python无法安装依赖库
#export https_proxy=http://10.8.40.234:7890 http_proxy=http://10.8.40.234:7890 all_proxy=socks5://10.8.40.234:7890

export HOMETEL="${TELEMAC_ROOT}/${TELEMAC_MASCARET_VER}"
export SYSTELCFG="${TELEMAC_ROOT}/systel.cfg"
export USETELCFG="${TELEMAC_TARGET}"
export PYTHONUNBUFFERED="true"
## 这里修改了一下wrap_api/lib里面的动态库不全增加/lib
export PYTHONPATH="${HOMETEL}/builds/${USETELCFG}/wrap_api/lib:${HOMETEL}/builds/${USETELCFG}/lib:$PYTHONPATH"

VENDOR_HOME="${TELEMAC_ROOT}/vendor"

export HDF5HOME="${VENDOR_HOME}/hdf5"
export MEDHOME="${VENDOR_HOME}/med"
export METISHOME="${VENDOR_HOME}/metis"

export PATH="${HDF5HOME}/bin:${MEDHOME}/bin:${METISHOME}/bin:${PATH}"
## 这里修改了一下wrap_api/lib里面的动态库不全增加/lib
export LD_LIBRARY_PATH="${HOMETEL}/builds/${USETELCFG}/wrap_api/lib:${HDF5HOME}/lib:${MEDHOME}/lib:${LD_LIBRARY_PATH}:${HOMETEL}/builds/${USETELCFG}/lib:"

TELEMAC_MAJOR_VER=$(echo $TELEMAC_MASCARET_VER | cut -c 1-2)
if [[ $TELEMAC_MAJOR_VER == "v7"  ]]; then
    export PATH="${HOMETEL}/scripts/python27:${PATH}"
    export PYTHONPATH="${HOMETEL}/scripts/python27:${PYTHONPATH}"
else
    export PATH="${HOMETEL}/scripts/python3:${PATH}"
    export PYTHONPATH="${HOMETEL}/scripts/python3:${PYTHONPATH}"
fi
