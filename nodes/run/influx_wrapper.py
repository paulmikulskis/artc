from influxdb_client import InfluxDBClient


class StatWriter:

    def __init__(self, host, password):
        self.host = host
        self.password = password
        self.client = InfluxDBClient(url=self.host, to)