#!/usr/bin/python3

import argparse
import csv
import json
import logging
import os
import socket
import time
import sys
import traceback

import paramiko
import requests

retry = 3
delay = 1
timeout = 2

def send_telegram_message(token, chatid, message):
    send_text = 'https://api.telegram.org/bot{}/sendMessage?chat_id={}&parse_mode=Markdown&text={}'.format(token, chatid, message)
    response = requests.get(send_text)
    return response.json()

def execute_action(action, host=None, user=None, password=None):
    if action.startswith('#'):
        log.warning('ignoring action {}'.format(action))
    elif action.startswith('http:'):
        response = requests.get(action)
        log.debug(response.json())
    elif action.startswith('ssh:'):
        ssh_execute(host, user, password, action[4:])
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
        (e_type, e_value, e_tb) = sys.exc_info()
        log.error('port {} check on {} failed\nexception {}: {}\n{}'.format(
            port, ip, e_type, e_value, traceback.format_tb(e_tb)[0]))
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

def ssh_execute(host, user, password, cmd='hostname'):
    result = False
    try:
        ssh = paramiko.SSHClient()
        ssh.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        ssh.connect(host, username=user, password=password)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        for line in stdout:
            log.debug(line.strip(os.linesep))
        result = True
    except:
        log.error('{} ssh connection failed'.format(host))
    return result

def write_node_exporter(metrics, file_name='/var/lib/node_exporter/textfile_collector/watchdog.prom'):
    if len(metrics) == 0:
        return
    with open(file_name + '.tmp', 'w') as f:
        for m, v in metrics.items():
            f.write('{} {}\n'.format(m, v))
    os.system('mv {}.tmp {}'.format(file_name, file_name))

parser = argparse.ArgumentParser(description='')
parser.add_argument('-c', '--config', default='watchdog.json', help='config file')
parser.add_argument('-d', '--debug', action='store_true', help='debug execution')
parser.add_argument('-n', '--dryrun', action='store_true', help='dry-run, just detect, do not execute actions')
parser.add_argument('files', nargs='+', help='host/service definition list (CSV format)')
args = parser.parse_args(sys.argv[1:])

self = os.path.basename(sys.argv[0])
myName = os.path.splitext(self)[0]
log = logging.getLogger(myName)
if args.dryrun:
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
else:
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename='/var/log/watchdog.log')
if args.debug:
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)

config = {}
if os.path.exists(args.config):
    config = read_config(args.config)

host_state = {}
node_exporter_metrics = {}

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
        log.warning('host {} DOWN, skipping further checks'.format(host, entry['service']))
        continue
    service_state = check_service(host, entry['port'])
    if entry['service'] == 'ssh' and service_state:
        # additionally try to log in
        service_state = ssh_execute(host, config['ssh_user'], config['ssh_password'])
    if not host in host_state.keys():
        host_state[host] = service_state
    host_state[host + '-' + entry['service']] = service_state
    node_exp_id = 'service_state{{host="{}",service="{}",port="{}"}}'.format(host, entry['service'], entry['port'])
    if service_state:
        msg += 'UP'
        node_exporter_metrics[node_exp_id] = 1
    else:
        msg += 'DOWN'
        node_exporter_metrics[node_exp_id] = 0
    log.info(msg)
    if not args.dryrun and not service_state:
        send_telegram_message(config['telegram_token'], config['telegram_chatid'], msg)
    if service_state or not entry['action']:
        continue
    log.debug('action ' + entry['action'])
    (off_cmd, on_cmd) = entry['action'].split(',')
    log.debug('OFF ' + off_cmd)
    if not args.dryrun:
        execute_action(off_cmd, host, config['ssh_user'], config['ssh_password'])
    if not args.dryrun and on_cmd:
        time.sleep(5)
        log.debug('ON ' + on_cmd)
        execute_action(on_cmd, host, config['ssh_user'], config['ssh_password'])

write_node_exporter(node_exporter_metrics)
