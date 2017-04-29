#!/bin/bash

check_env_vars()
{
    if [ "$PAAS_API_SERVER" == "" ]; then
        echo "[ERROR] PAAS_API_SERVER is not specified"
        return 1
    fi
    if [ "$K8S_API_SERVER" == "" ]; then
        echo "[ERROR] K8S_API_SERVER is not specified"
        return 1
    fi
    if [ "$ETCD_SERVER" == "" ]; then
        echo "[ERROR] ETCD_SERVER is not specified"
        return 1
    fi
}

update_config_file()
{
    config_file="/ido/paas-controller/config.py"
    echo "PAAS_API_SERVER='$PAAS_API_SERVER'" >> $config_file

    if [ "$K8S_API_SERVER" != "" ]; then
        echo "K8S_API_SERVER='$K8S_API_SERVER'" >> $config_file
    fi
    if [ "$ETCD_SERVER" != "" ]; then
        echo "ETCD_SERVER='$ETCD_SERVER'" >> $config_file
    fi
    if [ "$ETCD_PORT" != "" ]; then
        echo "ETCD_PORT='$ETCD_PORT'" >> $config_file
    fi
    if [ "$MAX_LOG_SIZE" != "" ]; then
        echo "MAX_LOG_SIZE='$MAX_LOG_SIZE'" >> $config_file
    fi
    if [ "$MAX_LOG_COUNT" != "" ]; then
        echo "MAX_LOG_COUNT='$MAX_LOG_COUNT'" >> $config_file
    fi
    if [ "$LOG_PATH" != "" ]; then
        echo "LOG_PATH='$LOG_PATH'" >> $config_file
    fi
}

if ! (check_env_vars); then
    exit 1
fi

update_config_file
cd /ido/paas-controller && python paas-controller.pyc

