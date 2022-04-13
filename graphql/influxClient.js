import {InfluxDB} from '@influxdata/influxdb-client'
import 'dotenv/config'

// You can generate an API token from the "API Tokens Tab" in the UI
const token = process.env.INFLUX_NODE_KEY
const org = 'https://' + process.env.INFLUX_ORG
const bucket = process.env.INFLUX_BUCKET
const client = new InfluxDB({url: process.env.INFLUX_HOST, token: token})


const queryApi = client.getQueryApi(org)

const query = `from(bucket: "${bucket}") |> range(start: -2w)`
queryApi.queryRows(query, {
  next: (row, tableMeta) => {
    const o = tableMeta.toObject(row)
    console.log(`${o._time} ${o._measurement}: ${o._field}=${o._value}`)
  },
  error: (error) => {
    console.error(error)
    console.log('Finished ERROR')
  },
  complete: () => {
    console.log('Finished SUCCESS')
  },
})

