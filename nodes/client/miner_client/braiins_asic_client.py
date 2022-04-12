

from ctypes.wintypes import CHAR
import datetime
from enum import Enum
import json
import logging
import os
from posixpath import abspath, dirname, join
import pprint
import socket
from sys import stderr
import time
from typing import Dict, List, Tuple
from unittest import result
from dotenv import load_dotenv
import paramiko

BASEDIR = abspath(dirname(__file__))
load_dotenv(join(BASEDIR, '../../../.base.env'))
log_level = os.environ.get("LOG_LEVEL")
log_type = os.environ.get("LOG_TYPE")

if log_level not in list(map(lambda x: x[1], logging._levelToName.items())):
    log_level = 'INFO'
if log_type not in ['FULL', 'CLEAN']:
    log_type = 'FULL'

ch = logging.StreamHandler()
# log = logging.getLogger(__name__.split('.')[-1])
log = logging.getLogger('miner_client')

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p') if log_type == 'FULL' else logging.Formatter('%(name)s - %(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)
log.setLevel(log_level)
logging.basicConfig(
    filename='control.log',
    encoding='utf-8', 
    level=logging.DEBUG
)

def f(n, roundn=3) -> float:
    '''
    Converts celcius to Farenheight
    '''
    return round(
        ((9/5) * n) + 32,
        roundn
        )

class MinerAPIResponseType(Enum):

    CANNOT_CONNECT = 'CANNOT_CONNECT'
    NO_OP = 'NO_OP'
    INVALID_REQUEST_BODY = 'INVALID_REQUEST_BODY'
    INVALID_REQUEST_PARAMETERS = 'INVALID_REQUEST_PARAMS'
    SUCCESS = 'SUCCESS'
    CLIENT_ERROR = 'CLIENT_ERROR'
    MINER_ERROR = 'MINER_ERROR'
    SSH_ERROR = 'SSH_ERROR'
    NO_RESPONSE = 'NO_RESPONSE'


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
    # Host or resource cannot be found
    404: MinerAPIResponseType.CANNOT_CONNECT,
    -2: MinerAPIResponseType.NO_RESPONSE

}

class MinerAPIError:

    def __init__(self, msg=None, code=None, time=None):
        self.msg = msg
        self.code = code
        self.date = time

    def __str__(self):
        return '{}: {}'.format(self.code, self.msg)


class MinerAPIResponse:

    def __init__(self, resp: dict):
        self.data = None
        self.resp = resp
        status = self.resp['STATUS']
        if isinstance(status, list):
            if len(self.resp.keys()) > 1:
                self.data = resp[list(self.resp.keys())[1]]
            else: self.data = None
    
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
        else:
            self.code = -1
            self.response_type = MinerAPIResponseType.MINER_ERROR,
            self.message = 'unrecognized error response',
            self.time = datetime.datetime.now(),
            self.error = 'unrecognized error response',
            self.data = None
      

    def __str__(self):
        return str({
            'code': self.code,
            'response_type': self.type.value,
            'message': self.message,
            'time': self.time.strftime('%b-%d %H:%M:%S'),
            'error': self.error,
            'data': self.data
            })

    def json(self):
        return json.dumps({
            'code': self.code,
            'response_type': self.type.value,
            'message': self.message,
            'time': self.time.strftime('%b-%d %H:%M:%S'),
            'error': str(self.error),
        })

          

class BraiinsOsClient:

    def __init__(
        self, 
        hosts: List[str] or str = None, 
        port: List[int] or int = 4028, 
        timeout: int = 3,
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
        STOP_COMMAND = '/etc/init.d/bosminer stop'
        resps = []
        for host in self.filter_hosts_to_contact(hosts):
            print('!! miners: sending "{}" to {}'.format(STOP_COMMAND, host))
            out, err = self._send_ssh_command(STOP_COMMAND, host)
            if err:
                resps.append(self._format_MinerAPIResponse('E', 'SSH ERROR', -1, datetime.datetime.now(), err))
            else:
                resps.append(self._format_MinerAPIResponse('S', 'sent {}'.format(out), 200, datetime.datetime.now()))

        print('MINER RESPONSES:', str(resps[0].error))
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
        log.debug(' paramiko attempting to connect to {} as {}:{}'.format(host['ip'], user, password))
        try:
            ssh.connect(host['ip'], username=user, password=password, timeout=3)
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
            err = ssh_stderr.read().decode('utf-8')
            out = ssh_stdout.read().decode('utf-8')
            #print('\n\n!!SSH OUT AND ERR:\nOUT:{}\nERR:{}'.format(out, err))
            if len(err) == 0: err = None
            if len(out) == 0: out = None
            ssh.close()
            log.info('sent ssh command to {}'.format(host['ip']))
            log.debug('received: "{}"'.format(out))
        except Exception as e:
            out = None
            err = 'unable to SSH to {} as {}:{}, msg: {}'.format(host['ip'], user, password, str(e))
            log.warn(err)

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
      -> Tuple[Dict[str, List[Tuple[str]]] or None, MinerAPIError or None]:
        '''
        returns a list of parsed temperature readings from all hosts

        Returns:
            tuple(List(tuple(board_temp, chip_temp, id)) or None, MinerAPIError or None)
        '''
        temps = self.get_temperatures()
        errors = []
        for ret in temps:
            api = ret[1]
            if api.error:
                return None, api.error

        return {
           resp[0]: [
              (d['Board'], d['Chip'], d['ID'])
                for resp in temps
                for d in resp[1].data
            ] 
            for resp in temps 
        }, None


    def get_tempterature_stats(self) -> dict[str, int]:
        templist = self.get_temperature_list()
        if templist[1] is not None:
            err = True
            return {}
        else:
            templist = templist[0]

        keys = list(templist.keys())
        temps = {'c'+str(keys.index(host))+'_board_'+str(d[2]): f(d[0]) for host, data in templist.items() for d in data }
        # temps2 = {'c'+str(keys.index(host))+'_chip_'+str(d[2]): d[1] for host, data in templist.items() for d in data }
        return temps

    
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
        except Exception as e:
            return self._format_MinerAPIResponse('E', 'unable to reach miner', 404)
        log.info('sending "{}" to {}'.format(command, host['connect_string']))
        sock.sendall(bytes(command, 'utf-8'))
        data = '{}'
        resp = None
        try:
            data = sock.recv(8192).decode('utf-8').strip()
            # cuts off any extra data after the last bracket from decoding
            data = "".join([data.rsplit("}" , 1)[0] , "}"])
            data = json.loads(data)
            resp = MinerAPIResponse(data)
            log.debug('{} produced response: {}'.format(host['connect_string'], resp))
        except:
            log.error('braiinsOS client timed out, setting data to {}')
            resp = self._format_MinerAPIResponse('E', 'not able to receive data from miner sock.recv', -2)

        sock.close()
        # print('miner response:')
        # print(resp)
        return resp

