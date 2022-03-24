

from enum import Enum
import json
import logging
import socket
from typing import List, Tuple


log = logging.getLogger(__name__)


MinerAPIErrorCodes = {
    23: "Invalid JSON",
    50: "Already disabled"

}

class MinerAPIErrorType(Enum):

    CANNOT_CONNECT = 'CANNOT_CONNECT'
    NO_OP = 'NO_OP'
    CLIENT_ERROR = 'CLIENT_ERROR'
    MINER_ERROR = 'MINER_ERROR'


class MinerAPIError:

    def __init__(self, type: MinerAPIErrorType, msg=None, resp=None):
        self.msg = msg
        self.type = type

    def __str__(self):
        return '{}: {}'.format(self.type, self.msg)


class BraiinsOsClient:

    def __init__(
        self, 
        hosts: List[str] or str = None, 
        port: List[int] or int = 4028, 
        timeout: int = 10
      ):
        self.timeout = timeout
        self.hosts = {}
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
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, self.ports[i]))
                info = socket.gethostbyaddr(host)
                new_host_info = {
                  'url': host,
                  'hostname': info[0],
                  'ip': info[2][0],
                  'port': int(self.ports[i]),
                  'connect_string': '{}:{}'.format(info[2][0], self.ports[i])
                }
                self.hosts[info[0]] = new_host_info
                sock.close()
                print('client can connect to:\n  {}'.format(new_host_info))
            except Exception as e:
                print(' !! unable to connect to "{}"'.format(host))
                print(e)

    

    def stop_pool(self, pool_id: int = 0, hosts: List[str] = None):
        '''
        stops a given slush pool

        Parameters:
            pool_id (int):The id of the pool to stop in BraiinsOs
            hosts (List[str] or str or None):The host or list of hosts to send this command to

        Returns:
            MinerResponse, MinerAPIError or Null   
        '''

        hosts_to_contact = filter(
          lambda x: x, 
          [ v 
            if ((not hosts) or v['hostname'] in hosts) 
            else None 
            for k, v in self.hosts.items()
          ]
        )

        for host in hosts_to_contact:
            command = '{"command":"disablepool","parameter":'+str(pool_id)+'}'
            self.send_command(command, host)


      
    def send_command(self, command, host):
        '''
        sends a line of text (JSON) to a given host registered with this client

        Parameters:
            command (str):The string to send to the miner
            host A dictionary of values from a host registered with this client

        Returns:
            MinerResponse, MinerAPIError or Null   
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((host['ip'], host['port']))
        log.info('sending "{}" to {}'.format(command, host['connect_string']))
        sock.sendall(bytes(command, 'utf-8'))
        response = sock.recv(8192)
        data = response.decode('utf-8').strip()
        # cuts off any extra data after the last bracket from decoding
        data = "".join([data.rsplit("}" , 1)[0] , "}"])
        data = json.loads(data)
        print(data)
        return 

