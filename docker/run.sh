#! /bin/bash
#
prog=`basename $0`
execdir=`dirname $0`
[ "$execdir" = "" -o "$execdir" = "." ] && execdir=$PWD
codedir=`(cd $execdir/.. > /dev/null 2>&1; pwd)`

set -e

$execdir/buildall.sh

ti="-ti"
[ "$1" == "testall" ] && ti=

echo docker run $ti --rm -v $codedir:/dev/oar-metadata oarmeta/mdtests "$@"
exec docker run $ti --rm -v $codedir:/dev/oar-metadata oarmeta/mdtests "$@"
