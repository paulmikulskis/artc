import {InfluxDB, FluxTableMetaData} from '@influxdata/influxdb-client'

const queryApi = new InfluxDB({url: `https://${process.env.influxHost}`, token: process.env.influxKey}).getQueryApi(process.env.org)
const statsQuery =
  'from(bucket: "default") \
  |> range(start: -15m) \
  |> filter(fn: (r) => r["_measurement"] == "chat_stats") \
  |> filter(fn: (r) => r["_field"] == "therm_oil" or r["_field"] == "therm_water") \
  |> filter(fn: (r) => r["deployment"] == "jontest")'

const programQuery =
  'from(bucket: "default") \
	|> range(start: -15m) \
  |> filter(fn: (r) => r["_measurement"] == "chat_stats") \
  |> filter(fn: (r) => r["_field"] == "programs") \
  |> filter(fn: (r) => r["deployment"] == "default")'

console.log('*** QUERY ROWS ***')

export default async function handler(req, res) {

  const data = await queryApi.collectRows(statsQuery /*, you can specify a row mapper as a second arg */)
  .then(data => {
    return data
  })
  .catch(error => {
    console.error(error)
    console.log('\nCollect ROWS ERROR')
  })

  data.sort((a, b) => b._time - a._time)
  
  const water_readings = data.filter((a) => a._field == 'therm_water')
  const oil_readings = data.filter((a) => a._field == 'therm_oil')

  const programData = await queryApi.collectRows(programQuery /*, you can specify a row mapper as a second arg */)
  .then(data => {
    return data
  })
  .catch(error => {
    console.error(error)
    console.log('\nCollect ROWS ERROR 2')
  })

  const sortedProgramData = programData.sort((a, b) => b._time - a._time)
  
  const programs = JSON.parse(sortedProgramData[(sortedProgramData.length) - 1]._value)
  const therm_water = Math.round(
    parseFloat((water_readings[(water_readings.length) - 1]._value  * 100))
  ) / 100
  const therm_oil = Math.round(parseFloat(oil_readings[(oil_readings.length) - 1]._value * 100)) / 100

  res.json({
    programData: programs,
    thermWater: therm_water,
    thermOil: therm_oil
  })

}


// There are more ways of how to receive results,
// the essential ones are shown/commented below. See also rxjs-query.ts .
//
// Execute query and receive table metadata and rows as they arrive from the server.
// https://docs.influxdata.com/influxdb/v2.1/reference/syntax/annotated-csv/
// queryApi.queryRows(fluxQuery, {
//   next: (row, tableMeta) => {
//     // the following line creates an object for each row
//     const o = tableMeta.toObject(row)
//     // console.log(JSON.stringify(o, null, 2))
//     console.log(
//       `${o._time} ${o._measurement} in '${o.location}' (${o.example}): ${o._field}=${o._value}`
//     )

//     // alternatively, you can get only a specific column value without
//     // the need to create an object for every row
//     // console.log(tableMeta.get(row, '_time'))

//     // or you can create a proxy to get column values on demand
//     // const p = new Proxy<Record<string, any>>(row, tableMeta)
//     // console.log(
//     //  `${p._time} ${p._measurement} in '${p.location}' (${p.example}): ${p._field}=${p._value}`
//     // )
//   },
//   error: (error) => {
//     console.error(error)
//     console.log('\nFinished ERROR')
//   },
//   complete: () => {
//     console.log('\nFinished SUCCESS')
//   },
// })

// // Execute query and collect result rows in a Promise.
// // Use with caution, it copies the whole stream of results into memory.
// queryApi
//   .collectRows(fluxQuery /*, you can specify a row mapper as a second arg */)
//   .then(data => {
//     data.forEach(x => console.log(JSON.stringify(x)))
//     console.log('\nCollect ROWS SUCCESS')
//   })
//   .catch(error => {
//     console.error(error)
//     console.log('\nCollect ROWS ERROR')
//   })

// // Execute query and return the whole result as a string.
// // Use with caution, it copies the whole stream of results into memory.
// queryApi
//   .queryRaw(fluxQuery)
//   .then(result => {
//     console.log(result)
//     console.log('\nQueryRaw SUCCESS')
//   })
//   .catch(error => {
//     console.error(error)
//     console.log('\nQueryRaw ERROR')
//   })

// Execute query and receive result lines in annotated csv format
// queryApi.queryLines(
//   fluxQuery,
//   {
//     next: (line: string) => {
//       console.log(line)
//     },
//     error: (error: Error) => {
//       console.error(error)
//       console.log('\nFinished ERROR')
//     },
//     complete: () => {
//       console.log('\nFinished SUCCESS')
//     },
//   }
// )