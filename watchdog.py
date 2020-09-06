#!/usr/bin/python3

import argparse
import csv
import json
import logging
import os
import socket
import time
import sys

import paramiko
import requests

retry = 3
delay = 1
timeout = 2

def send_telegram_message(token, chatid, message):
    send_text = 'https://api.telegram.org/bot{}/sendMessage?chat_id={}&parse_mode=Markdown&text={}'.format(token, chatid, message)
    response = requests.get(send_text)
    return response.json()

def execute_action(action):
    if action.startswith('http:'):
        response = requests.get(action)
        log.debug(response.json())
    else:
        log.error('unknown action type {}'.format(action))


def is_port_open(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, int(port)))
        s.shutdown(socket.SHUT_RDWR)
        return True
    except:
        return False
    finally:
        s.close()

def check_service(ip, port):
    ipup = False
    for i in range(retry):
        if is_port_open(ip, port):
            ipup = True
            break
        else:
            time.sleep(delay)
    return ipup

def read_hosts(file_name):
    result = []
    with open(file_name, newline='') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            result.append(row)
    return result

def read_config(file_name):
    config = {}
    with open(args.config) as f:
        config = json.load(f)
    return config

def check_ssh_login(host, user, password):
    result = False
    ssh = paramiko.SSHClient()
    ssh.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
    ssh.connect(host, username=user, password=password)
    stdin, stdout, stderr = ssh.exec_command('hostname')
    for line in stdout:
        log.debug(line.strip(os.linesep))
    result = True
    return result

parser = argparse.ArgumentParser(description='')
parser.add_argument('-c', '--config', default='watchdog.json', help='config file')
parser.add_argument('-d', '--debug', action='store_true', help='debug execution')
parser.add_argument('files', nargs='+', help='host/service definition list (CSV format)')
args = parser.parse_args(sys.argv[1:])

self = os.path.basename(sys.argv[0])
myName = os.path.splitext(self)[0]
log = logging.getLogger(myName)
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename='/var/log/watchdog.log')
if args.debug:
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)

config = {}
if os.path.exists(args.config):
    config = read_config(args.config)

host_state = {}

log.info('host/service definitions from {}'.format(args.files[0]))
hosts = read_hosts(args.files[0])
for entry in hosts:
    host = entry['host']
    if host.startswith('#'):
        continue
    msg = '{}:{} {} '.format(host, entry['port'], entry['service'])
    log.debug('checking ' + msg)
    service_state = False
    # do not check further, if the host already known to be down
    if host in host_state.keys() and not host_state[host]:
        send_telegram_message(config['telegram_token'], config['telegram_chatid'], 'host {} DOWN'.format(host, entry['service']))
        log.warning('host {} DOWN, skipping further checks'.format(host, entry['service']))
        continue
    service_state = check_service(host, entry['port'])
    if entry['service'] == 'ssh' and service_state:
        # additionally try to log in
        service_state = check_ssh_login(host, config['ssh_user'], config['ssh_password'])
    if not host in host_state.keys():
        host_state[host] = service_state
    host_state[host + '-' + entry['service']] = service_state
    if service_state:
        msg += 'UP'
    else:
        msg += 'DOWN'
    log.info(msg)
    if service_state or not entry['action']:
        continue
    log.debug('action ' + entry['action'])
    (off_cmd, on_cmd) = entry['action'].split(',')
    log.debug('OFF ' + off_cmd)
    execute_action(off_cmd)
    time.sleep(5)
    log.debug('ON ' + on_cmd)
    execute_action(on_cmd)
