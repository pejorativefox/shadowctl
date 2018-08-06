#!/usr/bin/python3
"""
Shadowctl allows for the control of a shadowsocks local proxy via
a single config file.

Usage:
    shadowctl status [--json]
    shadowctl list [--json]
    shadowctl start <server>
    shadowctl stop

Options:
  -h --help     Show this screen.
  --json        Print json output for parsing"""


import subprocess
import os
import sys
import json
import logging
import tempfile
import shlex
import argparse


# There are 2 versions: xdg and pyxdg
# try both and get the values we need
try:
    from xdg import XDG_CONFIG_HOME, XDG_RUNTIME_DIR
except ImportError:
    from xdg.BaseDirectory import get_runtime_dir, xdg_config_home
    XDG_CONFIG_HOME = xdg_config_home
    XDG_RUNTIME_DIR = get_runtime_dir()


# See if we have a notification module
try:
    import notify2
except ImportError:
    pass


def string_from_file(filename):
    """Shortcut to load a file."""
    with open(filename, 'r') as open_file:
        file_buffer = open_file.read()
    return file_buffer


def check_pid(pid):
    """ Check For the existence of a unix pid.
    TODO: Does not work on windows!"""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def notify(msg):
    """Check and see if we can notify via dbus if not discard."""
    if 'notify2' in sys.modules:
        notify2.init('shadowctl')
        n = notify2.Notification("shadowctl", msg, "network-vpn")
        n.show()


class ShadowsocksControl(object):
    def __init__(self):
        self.load_config()

    def load_config(self):
        config_path = '{}/shadowctl/config.json'.format(XDG_CONFIG_HOME)
        if not os.path.exists(config_path):
            print('Configuration: {} missing!'.format(config_path))
            exit()

        config_buffer = string_from_file(config_path)
        config = json.loads(config_buffer)
        self.pid_file = '{}/shadowsocks.pid'.format(XDG_RUNTIME_DIR)
        self.log_file = config['log_file']
        self.servers = config['servers']

    @property
    def has_pid_file(self):
        if not os.path.exists(self.pid_file):
            return False
        else:
            return True

    @property
    def pid(self):
        return int(string_from_file(self.pid_file))

    @property
    def connected(self):
        if not self.has_pid_file:
            return False
        else:
            if check_pid(self.pid):
                return True
            else:
                print('Error: stale PID file: {}'.format(self.pid_file))
                print('Cleaning up.')
                os.remove(self.pid_file)
                return False

    def status(self, json_output=False):
        if not self.has_pid_file:
            if json_output:
                json_status_dict = {
                    'status': 'disconnected'
                }
                print(json.dumps(json_status_dict))
            else:
                print('Shadowsocks not running.')
        else:
            if self.connected:
                server_name = string_from_file(
                    '{}/shadowsocks.server'.format(XDG_RUNTIME_DIR))
                if json_output:
                    json_status_dict = {
                        'status': 'connected',
                        'name': server_name,
                        'pid': self.pid
                    }
                    print(json.dumps(json_status_dict))
                else:
                    print('Shadowsocks running: PID: {} connected to: {}'.format(
                        self.pid, server_name))
            else:
                print('Error! Stale PID file: {}'.format(self.pid_file))
                exit()

    def list(self, json_output=False):
        if json_output:
            json_list_dict = list(self.servers.keys())
            print(json.dumps(json_list_dict))
        else:
            print('Configured servers:')
            for s in self.servers:
                print(s)

    def start(self, server):
        if not self.connected:
            config_file = tempfile.NamedTemporaryFile('w', delete=True)
            command = 'sslocal --pid-file={} --log-file={} -c {} -d start'
            command = command.format(self.pid_file, self.log_file,
                                     config_file.name)
            config_file.write(json.dumps(self.servers[server]))
            config_file.flush()
            command = shlex.split(command)
            try:
                ret = subprocess.check_call(command, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
            except FileNotFoundError:
                print('Error: shadowsocks binary not installed or not in path.')
                exit()

            config_file.close()

            if ret == 0:
                notify('Connected to {}'.format(server))
                print('Connected to {}'.format(server))
                fn = '{}/shadowsocks.server'.format(XDG_RUNTIME_DIR)
                with open(fn, 'w') as server_info_file:
                    server_info_file.write(server)
            else:
                print('Error connecting')
                print('Returned: {} check the logs.'.format(ret))
                exit()
        else:
            print('Already connected.')


    def stop(self):
        if self.connected:
            command = ['sslocal', '--pid-file={}'.format(self.pid_file),
                       '-d', 'stop']
            # ret = subprocess.check_call(command, stdout=subprocess.PIPE,
            #                             stderr=subprocess.STDOUT)
            try:
                os.kill(self.pid, 15)
            except OSError:
                print('Not Connected. Possible stale pid file.')
            else:
                print('Disconnected.')
                notify('Disconnected.')
        else:
            print('Not connected.')

    def restart(self):
        pass


def main():
    parser = argparse.ArgumentParser(prog='shadowctl',
        description='Shadowctl: Shadowsocks control utility.')
    # Subparsers
    sp = parser.add_subparsers(dest='action_name')
    # start
    sp_start = sp.add_parser('start', help='Starts %(prog)s daemon')
    sp_start.add_argument('server', type=str, help='Server to connect')
    # stop
    sp_stop = sp.add_parser('stop', help='Stops %(prog)s daemon')
    # list
    sp_list = sp.add_parser('list', help='List available servers.')
    sp_list.add_argument('--json', action='store_true',
                         help='Output messages in JSON')
    # status
    sp_status = sp.add_parser('status', help='List available servers.')
    sp_status.add_argument('--json', action='store_true',
                           help='Output messages in JSON')

    arguments = parser.parse_args()
    action_name = arguments.action_name

    ssc = ShadowsocksControl()

    if action_name == 'status':
        ssc.status(arguments.json)

    elif action_name == 'list':
        ssc.list(arguments.json)

    elif action_name == 'start':
        ssc.start(arguments.server)

    elif action_name == 'stop':
        ssc.stop()

