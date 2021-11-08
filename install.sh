#!/bin/bash

HOST=$(hostname -s)
IMAGE=watchdog-docker-pi
LOGFILE=/var/log/watchdog.log
BACKUP_DIR=/backup/${HOST}

function do_build {
    docker build -t ${IMAGE} .
}

function do_init {
    if [ ! -f ${LOGFILE} ]
    then
        sudo touch ${LOGFILE}
        chown pi.pi ${LOGFILE}
    fi
}
function do_run {
    do_init
    # run on RancherOS every 5 minutes (container-cron service has to enabled)
    #docker run -d -it -e HOSTNAME=raspi3 --label=cron.schedule="0 */5 * ? * *" --name watchdog -v $HOME/.ssh:/root/.ssh -v ${PWD}:/home -v ${LOGFILE}:${LOGFILE} ${IMAGE} python3 watchdog.py hosts.csv
    # normal run, schedule via crontab on regular OS
    docker run --rm -i -e HOSTNAME=${HOST} --name watchdog -v $HOME/.ssh:/root/.ssh -v ${PWD}:/home -v ${LOGFILE}:${LOGFILE} -v /var/lib/node_exporter/textfile_collector:/var/lib/node_exporter/textfile_collector ${IMAGE} python3 watchdog.py hosts.csv
}

function do_test {
    do_init
    docker run --rm -i -e HOSTNAME=${HOST} --net=host --name watchdog -v $HOME/.ssh:/root/.ssh -v ${PWD}:/home -v /var/lib/node_exporter/textfile_collector:/var/lib/node_exporter/textfile_collector -v ${LOGFILE}:${LOGFILE} ${IMAGE} python3 watchdog.py -d -n hosts.csv
}

function do_restart {
    do_stop
    sleep 5
    do_run
}

function do_stop {
    docker rm -f watchdog
}

function do_backup {
    filename=$(date +'%Y-%m-%d_%H%M')_watchdog.tar.xz
    tar -c -f ${filename} -J *.csv *.json *.py
    sudo mv ${filename} ${BACKUP_DIR}
}

task=$1
shift
do_$task $*
