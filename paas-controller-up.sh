#!/bin/bash
export PATH=/sbin:/usr/sbin:/usr/local/sbin:/usr/local/bin:/usr/bin:/bin

export WORKDIR=$( cd ` dirname $0 ` && pwd )
cd "$WORKDIR" || exit 1

pull_imgs(){
    docker pull $img > /dev/null
}

rm_old_contains(){
    containers=`docker ps -a | egrep "${paas_controller_cname}" | awk '{print $1}'`
    for c in $containers; do 
        echo "removing container: $c"
        docker rm -vf $c > /dev/null
    done
}


get_repo()
{
    if (( $# != 1 )); then
        echo "usage:    $0 repo(1:mainland, 2:oversea)"
        echo "e.g:      $0 mainland"
        exit 0
    fi

    repo=idevopscloud

    if [[ "$1" == "1" ]]; then
        repo=index.idevopscloud.com:5000/idevops
    elif [[ "$1" == "2" ]]; then
        repo=idevopscloud
    else
        echo "error repo type"
        exit 1
    fi
}

get_repo $*
img=${repo}/paas-controller:1.1
paas_controller_cname=ido-paas-controller
persist_dir=/mnt/master-pd/docker/paas-controller/log

pull_imgs
rm_old_contains

docker run -d \
	--env PAAS_API_SERVER=http://10.141.10.36:12306 \
	--env K8S_API_SERVER=http://10.141.10.36:8080/api/v1 \
	--env ETCD_SERVER=10.141.10.36 \
	-v $persist_dir:/var/log/ido/ \
	--name=${paas_controller_cname} $img

