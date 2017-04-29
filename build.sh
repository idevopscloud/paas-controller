#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

usage()
{
    echo "build.sh VERSION"
}

OPTS=`getopt -o "h" -- "$@"`
if [ $# != 1 ]; then
    usage
    exit 1
fi
eval set -- "$OPTS"

outdir=$DIR/target

while true ; do
    case "$1" in
        -h) usage; exit 0;;
        --) shift; break;;
    esac
done

version=$1

mkdir -p $outdir 2>&1>/dev/null
rm -rf $outdir/* 2>&1>/dev/null
cp -r src $outdir && mv $outdir/src $outdir/paas-controller
cd $outdir
python -m compileall paas-controller
rm paas-controller/*.py
tar czvf $outdir/paas-controller.tar paas-controller
rm -r $outdir/paas-controller

cd $DIR
cp -r dfile $outdir
cp $outdir/paas-controller.tar $outdir/dfile
cd $outdir/dfile
./build.sh $version
