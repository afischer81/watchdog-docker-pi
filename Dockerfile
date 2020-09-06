FROM python:3.7-slim

RUN apt update && \
    apt upgrade && \
    apt install -y python3-paramiko python3-requests && \
    mkdir /home

ENV PYTHONPATH /usr/lib/python3/dist-packages

WORKDIR /home
