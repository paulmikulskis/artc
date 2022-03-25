

from ctypes.wintypes import CHAR
import datetime
from enum import Enum
import json
import logging
import pprint
import socket
from sys import stderr
import time
from typing import Dict, List, Tuple
from unittest import result
import paramiko

log = logging.getLogger(__name__)

class MinerAPIResponseType(Enum):

    CANNOT_CONNECT = 'CANNOT_CONNECT'
    NO_OP = 'NO_OP'
    INVALID_REQUEST_BODY = 'INVALID_REQUEST_BODY'
    INVALID_REQUEST_PARAMETERS = 'INVALID_REQUEST_PARAMS'
    SUCCESS = 'SUCCESS'
    CLIENT_ERROR = 'CLIENT_ERROR'
    MINER_ERROR = 'MINER_ERROR'
    SSH_ERROR = 'SSH_ERROR'


MinerAPIErrorCodes = {
    # invalid JSON received
    23: MinerAPIResponseType.INVALID_REQUEST_BODY,
    # mining pool already disabled
    50: MinerAPIResponseType.NO_OP,
    # disabled mining pool
    48: MinerAPIResponseType.SUCCESS,
    # invalid request parameters such as wrong pool id
    107: MinerAPIResponseType.INVALID_REQUEST_PARAMETERS,
    # reporting temperatures
    201: MinerAPIResponseType.SUCCESS,
    # dev details
    69: MinerAPIResponseType.SUCCESS,
    # SSH error
    -1: MinerAPIResponseType.SSH_ERROR,

}

class MinerAPIError:

    def __init__(self, msg=None, code=None, time=None):
        self.msg = msg
        self.code = code
        self.date = time

    def __str__(self):
        return '[{}]: {}: {}'.format(self.date, self.code, self.msg)


class MinerAPIResponse:

      def __init__(self, resp: dict):
          self.resp = resp
          status = self.resp['STATUS']
          if isinstance(status, list):
              if len(self.resp.keys()) > 1:
                  self.data = resp[list(self.resp.keys())[1]]
              status = status[0]
              self.status = status
              self.message = status['Msg']
              self.code = int(status['Code'])
              time_int = status['When']
              self.type = MinerAPIResponseType.SUCCESS
              if self.code in MinerAPIErrorCodes.keys():
                  self.type = MinerAPIErrorCodes[self.code]
              if time_int:
                  self.time = datetime.datetime.fromtimestamp(time_int)
              else:
                  self.time = None
              if status['STATUS'] == 'E':
                  self.error = MinerAPIError(
                    self.message,
                    self.code,
                    self.message
                  )
              else:
                  self.error = None
      

      def __str__(self):

          return '{}'.format(
              json.dumps({
                  'code': self.code,
                  'response_type': self.type.value,
                  'message': self.message,
                  'time': self.time.strftime('%b-%d %H:%M:%S'),
                  'error': self.error,
                  'data': self.data
                  },
                  indent=2
              )
          )
          

class BraiinsOsClient:

    def __init__(
        self, 
        hosts: List[str] or str = None, 
        port: List[int] or int = 4028, 
        timeout: int = 10,
        password: str = '1234count'
      ):
        self.timeout = timeout
        self.hosts = {}
        self.user = 'root'
        # later implement ARP lookup
        if hosts == None:
            log.error(' !! no host specified, exiting')


        if isinstance(hosts, list):
            self.addresses = hosts
        if isinstance(hosts, str):
            self.addresses = [hosts]
        
        if isinstance(port, list):
            self.ports = port
        if isinstance(hosts, str):
            self.ports = [port]

        for i, host in enumerate(self.addresses):
            try:
                info = socket.gethostbyaddr(host)
                new_host_info = {
                    'url': host,
                    'hostname': info[0],
                    'ip': info[2][0],
                    'port': int(self.ports[i]),
                    'connect_string': '{}:{}'.format(info[2][0], self.ports[i]),
                    'password': password
                }
                self.hosts[info[0]] = new_host_info
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((host, self.ports[i]))
                    sock.close()
                    print('client can connect to bosminer API at:\n  {}'.format(new_host_info))
                except Exception as e:
                    print(' currently unable to connect to bosminer API at "{}"'.format(host))
                    print(e)
            except Exception as e:
                print(' host "{}" is unreachable!'.format(host))
                print(e)
    

    def filter_hosts_to_contact(self, hosts) -> List[dict]:
        return filter(
            lambda x: x, 
            [ v 
              if ((not hosts) or v['hostname'] in hosts) 
              else None 
              for k, v in self.hosts.items()
            ]
        )


    def start_miner(self, hosts: List[str] or str = None):
        '''
        starts a given miner or list of miners (defaults to all miners configured)

        Parameters:
            hosts (List[str] or str or None):The host or list of hosts to send this command to

        Returns:
            Dict[ip: MinerAPIResponse]
        '''
        if ((not isinstance(hosts, list) and (hosts is not None))): hosts = [hosts]
        START_COMMAND = '/etc/init.d/bosminer start'
        resps = []
        for host in self.filter_hosts_to_contact(hosts):
            out, err = self._send_ssh_command(START_COMMAND, host)
            if err:
                resps.append(self._format_MinerAPIResponse('E', 'SSH ERROR', -1, datetime.datetime.now(), err))
            else:
                resps.append(self._format_MinerAPIResponse('S', 'sent {}'.format(out), 200, datetime.datetime.now()))

        return resps


    def stop_miner(self, hosts: List[str] or str = None):
        '''
        stops a given miner or list of miners (defaults to all miners configured)

        Parameters:
            hosts (List[str] or str or None):The host or list of hosts to send this command to

        Returns:
            Dict[ip: MinerAPIResponse]
        '''
        if ((not isinstance(hosts, list) and (hosts is not None))): hosts = [hosts]
        START_COMMAND = '/etc/init.d/bosminer stop'
        resps = []
        for host in self.filter_hosts_to_contact(hosts):
            out, err = self._send_ssh_command(START_COMMAND, host)
            if err:
                resps.append(self._format_MinerAPIResponse('E', 'SSH ERROR', -1, datetime.datetime.now(), err))
            else:
                resps.append(self._format_MinerAPIResponse('S', 'sent {}'.format(out), 200, datetime.datetime.now()))

        return resps


    def is_mining(self, hosts: List[str] or str = None):
        '''
        returns a set of booleans on whether the miners are mining

        Parameters:
            hosts (List[str] or str or None):The host or list of hosts to send this command to

        Returns:
            [bool]
        '''
        if ((not isinstance(hosts, list) and (hosts is not None))): hosts = [hosts]
        COMMAND = 'ps | grep "/usr/bin/bosminer" | grep -v grep'
        resps = {}
        for host in self.filter_hosts_to_contact(hosts):
            out, err = self._send_ssh_command(COMMAND, host)
            if out is not None: resps[host['hostname']] = True
            else: resps[host['hostname']] = False

        return resps


    def _format_MinerAPIResponse(self, status_letter: CHAR, msg: str, code: int, when: datetime.datetime=None, data=None) -> MinerAPIResponse:
        '''
        formats a set of return values to create a MinerAPIResponse
          typically used if you wish to craft a class-ed MinerAPIResponse but are not sourcing the return JSON
          straight from the CGMiner API in bosminer, such as creating a custom SSH error

        Parameters:
            status_letter (CHAR):Status letter this message would reflect if the CGMiner API were to have sent it e.g. 'S' for success
            msg (str):A custom message to send
            code (int):return code
            when (datetime): (Optional) datetime representing when this response was created
            data (any): (Optional) data to include in the response object

        Returns:
            MinerAPIResponse
        '''
        return MinerAPIResponse({
          'STATUS': [
            {'STATUS': str(status_letter), 'Msg': msg, 'Code': code, 'When': when.timestamp() if when else datetime.datetime.now().timestamp()},
            data
          ]
        })

    
    def _send_ssh_command(self, command, host):
        '''
        send an SSH command to the miner.  This will execute as ROOT, be careful!

        Parameters:
            command (str):The command to execute
            host (dict):The host object from self.hosts to send this command to

        Returns:
            Dict[ip: MinerAPIResponse]
        '''
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        user = self.user
        password = host['password']
        print(' paramiko attempting to connect to {} as {}:{}'.format(host['ip'], user, password))
        try:
            ssh.connect(host['ip'], username=user, password=password)
        except Exception as e:
            return None, self._format_MinerAPIResponse('E', 'unable to reach miner via SSH', 404)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
        err = ssh_stderr.read().decode('utf-8')
        out = ssh_stdout.read().decode('utf-8')
        if len(err) == 0: err = None
        if len(out) == 0: out = None
        ssh.close()
        return out, err


    def stop_pool(self, pool_id: int = 0, hosts: List[str] = None) -> List[MinerAPIResponse]:
        '''
        stops a given slush pool

        Parameters:
            pool_id (int):The id of the pool to stop in BraiinsOs
            hosts (List[str] or str or None):The host or list of hosts to send this command to

        Returns:
            List[MinerAPIResponse]
        '''

        results = []
        for host in self.filter_hosts_to_contact(hosts):
            command = '{"command":"disablepool","parameter":'+str(pool_id)+'}'
            results.append(self.send_command(command, host))

        return results



    def start_pool(self, pool_id: int = 0, hosts: List[str] = None) -> List[MinerAPIResponse]:
        '''
        starts a given slush pool

        Parameters:
            pool_id (int):The id of the pool to start in BraiinsOs
            hosts (List[str] or str or None):The host or list of hosts to send this command to

        Returns:
            List[MinerAPIResponse]
        '''

        results = []
        for host in self.filter_hosts_to_contact(hosts):
            command = '{"command":"enablepool","parameter":'+str(pool_id)+'}'
            results.append(self.send_command(command, host))

        return results


    def get_temperatures(self, hosts: List[str] = None) -> List[Tuple[str, MinerAPIResponse]]:
        '''
        gets the termperature readings of the given hosts

        Parameters:
            hosts (List[str] or str or None):The host or list of hosts to send this command to

        Returns:
            List[MinerAPIResponse]
        '''

        results = []
        for host in self.filter_hosts_to_contact(hosts):
            command = '{"command":"temps"}'
            results.append((host['hostname'], self.send_command(command, host)))

        return results


    def get_temperature_list(self) \
      -> Tuple[Dict[str, List[Tuple[str]]], MinerAPIError or None]:
        '''
        returns a list of parsed temperature readings from all hosts

        Returns:
            tuple(List(tuple(board_temp, chip_temp, id)) or None, MinerAPIError or None)
        '''
        temps = self.get_temperatures()
        error = list(filter(lambda x: x, map(lambda x: x[1].error, temps)))
        if len(error) > 1:
            return None, error[0]
        return {
           resp[0]: [
              (d['Board'], d['Chip'], d['ID'])
                for resp in temps
                for d in resp[1].data
            ] 
            for resp in temps 
        }, None

    
    def get_details(self, hosts: List[str] = None) -> List[MinerAPIResponse]:
        '''
        gets the "dev details" from the miners specified
        details include:
          - Chips, Cores, Device Path, Driver, Frequency, ID, Kernel, Model, Name, Voltage

        Parameters:
            hosts (List[str] or str or None):The host or list of hosts to send this command to

        Returns:
            TODO
        '''

        results = {}
        for host in self.filter_hosts_to_contact(hosts):
            command = '{"command":"devdetails"}'
            results[host['hostname']] = (self.send_command(command, host))
        
        error = list(filter(lambda x: x, map(lambda x: x.error, results.values())))
        if len(error) > 1:
            return None, error[0]

        dicts = list(map(
            lambda x: {
                x[0]:
                [
                  dict(map(
                      lambda y: [y[0].replace(' ', '').strip().lower(), y[1]], 
                      list(info.items()) + [list(('ip', self.hosts[x[0]]['ip']))] 
                  ))
                  for info in x[1].data
                ]
            }, 
            results.items()
        ))
        #pprint.pprint(dicts)
        return dicts

      
    def send_command(self, command, host):
        '''
        sends a line of text (JSON) to a given host registered with this client

        Parameters:
            command (str):The string to send to the miner
            host A dictionary of values from a host registered with this client

        Returns:
            MinerResponse
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((host['ip'], host['port']))
        except ConnectionRefusedError as e:
            return self._format_MinerAPIResponse('E', 'unable to reach miner', 404)
        log.info('sending "{}" to {}'.format(command, host['connect_string']))
        sock.sendall(bytes(command, 'utf-8'))
        response = sock.recv(8192)
        data = response.decode('utf-8').strip()
        # cuts off any extra data after the last bracket from decoding
        data = "".join([data.rsplit("}" , 1)[0] , "}"])
        data = json.loads(data)
        resp = MinerAPIResponse(data)
        # print('miner response:')
        # print(resp)
        return resp

