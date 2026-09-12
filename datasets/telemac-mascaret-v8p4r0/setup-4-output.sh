#!/bin/bash -ev
###
 # @Author: WangYu
 # @Date: 2023-03-16 09:21:59
 # @LastEditors: WangYu
 # @LastEditTime: 2023-08-09 09:27:44
 # @FilePath: /docker-telemac/docker/setup-2-py.sh
 # @Description: 
 # @copyright: Copyright (c) 2023 by WangYu, All Rights Reserved. 
### 

# debian dependencies + python libs

# 因为不可能再用v7版本，所以先注释
#TELEMAC_MAJOR_VER=$(echo $TELEMAC_MASCARET_VER | cut -c 1-2)
#if [[ $TELEMAC_MAJOR_VER == "v7"  ]]; then
#    PYTHON_PKGS="python python-pip"
#    PIP_PKGS="numpy matplotlib==2.0.2 scipy jupyter"
#    export PYTHON="python"
#
#    sed -i 's/<partel.par>/PARTEL.PAR/' ${TELEMAC_ROOT}/systel.cfg
#else
#    PYTHON_PKGS="python3 python3-pip"
#    PIP_PKGS="pandas mpi4py"
#    export PYTHON="python3"
#    export PYTHON_VERSION=3
#fi

PYTHON_PKGS="python3 python3-pip"
PIP_PKGS="pandas mpi4py"
export PYTHON="python3"
export PYTHON_VERSION=3

export DEBIAN_FRONTEND=noninteractive

${PYTHON} -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple ${PIP_PKGS}

# 更新最新的pip
${PYTHON} -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn

# pyproj 二维结果坐标转换用
${PYTHON} -m pip install pyproj -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn

# python服务 fastApi
${PYTHON} -m pip install fastapi uvicorn[standard] -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn

# 父进程监控
${PYTHON} -m pip install psutil -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn
