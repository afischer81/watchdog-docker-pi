#!/bin/bash

IMAGE=watchdog-docker-pi

function do_build {
    docker build -t ${IMAGE} .
}

function do_run {
    docker run --rm -it -e PYTHONPATH=/usr/lib/python3/dist-packages -v $HOME/.ssh:/root/.ssh -v ${PWD}:/home -w /home ${IMAGE} python3 watchdog.py hosts.csv
}

task=$1
shift
do_$task $*
