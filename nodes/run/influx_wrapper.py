from influxdb_client import Point, InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
import os
from os.path import join, dirname
from dotenv import load_dotenv

# Get the path to the directory this file is in
BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, '../../.base.env'))


class StatWriter:

    print('token=', os.environ.get("INFLUX_NODE_KEY"))
    print('ord=',os.environ.get("INFLUX_ORG"))

    def __init__(self, host):
        self.host = host
        self.client = InfluxDBClient(
            url=self.host, 
            token=os.environ.get("INFLUX_NODE_KEY"),
            org=os.environ.get("INFLUX_ORG")
          )
        self.deployment_id = os.environ.get("NODE_DEPLOYMENT_ID")
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
    

    def write_dict(self, measurement_name, datapoints):
        buffer = []
        for key, value in datapoints.items():
            point = Point(
              measurement_name
              ).tag(
                "deployment", self.deployment_id
                ).field(key, value)
            buffer.append(point)
        self.write_api.write(bucket="my-bucket", record=buffer)


