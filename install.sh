#!/bin/bash

IMAGE=watchdog-docker-pi
LOGFILE=/var/log/watchdog.log

function do_build {
    docker build -t ${IMAGE} .
}

function do_run {
    if [ ! -f ${LOGFILE} ]
    then
        sudo touch ${LOGFILE}
    fi
    # run on RancherOS every 5 minutes (container-cron service has to enabled)
    docker run -d -it -e HOSTNAME=raspi3 --label=cron.schedule="*/5 * * * * ?" --name watchdog -v $HOME/.ssh:/root/.ssh -v ${PWD}:/home -v ${LOGFILE}:${LOGFILE} ${IMAGE} python3 watchdog.py hosts.csv
}

task=$1
shift
do_$task $*
