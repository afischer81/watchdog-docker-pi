FROM python:3.7-slim

RUN apt update -y && \
    apt upgrade -y && \
    apt install -y python3-paramiko python3-requests && \
    mkdir -p /home

ENV PYTHONPATH /usr/lib/python3/dist-packages

WORKDIR /home
