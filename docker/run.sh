#! /bin/bash
#
# run.sh:  execute the build-test docker container
#
# Usage: run.sh [cmd]
#
# where cmd is one of:
#  build -- builds package and produces a <pkg>-dist.zip file that contains
#           the package build products
#  test  -- builds and runs unit tests
#  bshell -- builds package, installs it into container, and starts an
#           interactive shell inside the running container
#  shell -- starts an interactive shell inside the running container
#
prog=`basename $0`
execdir=`dirname $0`
[ "$execdir" = "" -o "$execdir" = "." ] && execdir=$PWD
codedir=`(cd $execdir/.. > /dev/null 2>&1; pwd)`

## These are set by default via _run.sh; if necessary, uncomment and customize
#
PACKAGE_NAME=oar-metadata
# 
## list the names of run commands that should start an interactive shell
#
# SHELL_COMMANDS="bshell shell"

. $codedir/oar-build/_run.sh

# set RUN_OPTS and INTERACTIVE
#
setup_run

[ -n "$BUILD_FIRST" ] && build_images

if [ -n "$INTERACTIVE" ]; then
    
    # run command will open an interactive shell
    echo '+' docker run $INTERACTIVE $RUN_OPTS $PACKAGE_NAME/build-test "$@"
    docker run $RUN_OPTS $INTERACTIVE $PACKAGE_NAME/build-test "$@"
    
else
    
    # execute run command and then exit the container; log output
    log_intro    # record start of run into log

    echo '+' docker run $RUN_OPTS $PACKAGE_NAME/build-test "$@" | logit
    docker run $RUN_OPTS $PACKAGE_NAME/build-test "$@" 2>&1  | logit

fi
