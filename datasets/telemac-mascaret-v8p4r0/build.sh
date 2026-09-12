#!/bin/bash -ev
###
 # @Author: WangYu
 # @Date: 2023-03-16 09:21:59
 # @LastEditors: WangYu
 # @LastEditTime: 2023-08-09 14:53:37
 # @FilePath: /docker-telemac/docker/build.sh
 # @Description: 
 # @copyright: Copyright (c) 2023 by WangYu, All Rights Reserved. 
### 

echo "Building TELEMAC-MASCARET..."

source ${TELEMAC_ROOT}/setenv.sh

echo ${PATH}
config.py

if [[ $TELEMAC_MAJOR_VER == "v7"  ]]; then
    compileTELEMAC.py
else
    compile_telemac.py
fi

echo "Cleaning object files..."

rm -rf ${HOMETELE}/builds/obj/*

echo "Finished $0"