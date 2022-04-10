from influxdb_client import Point, InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
import os
from os.path import join, dirname
from dotenv import load_dotenv

# Get the path to the directory this file is in
BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, '../../.base.env'))


class InfluxStatWriter:

    print('token=', os.environ.get("INFLUX_NODE_KEY"))
    print('ord=',os.environ.get("INFLUX_ORG"))

    def __init__(self, host, deployment_ids=[], port=8086, bucket='default', https=True):
        print('host=', host)
        self.host = host
        self.port = port
        self.bucket = bucket
        self.org = os.environ.get("INFLUX_ORG")
        preface = 'https://' if https else 'http://'
        self.client = InfluxDBClient(
            url='{}{}'.format(preface, self.host, self.port), 
            token=os.environ.get("INFLUX_NODE_KEY"),
            org=self.org
          )
        self.deployment_ids = deployment_ids if len(deployment_ids) > 0 else [os.environ.get("NODE_DEPLOYMENT_ID")]
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
    

    def write_dict(self, measurement_name: str, datapoints: dict):
        buffer = []
        for id in self.deployment_ids:
            for key, value in datapoints.items():
                point = Point(
                measurement_name
                ).tag(
                    "deployment", id
                    ).field(key, value)
                buffer.append(point)
            
            data_dict = {
                "measurement": "chat_stats",
                "tags": {"deployment": id},
                "fields": datapoints
            }
            self.write_api.write(self.bucket, self.org, data_dict)


