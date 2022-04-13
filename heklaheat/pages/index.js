
import Knob from "../components/knob"; //https://codesandbox.io/s/knob-for-ac-forked-4ujmm7?file=/src/App.tsx:9018-9055
import { Dispatch, SetStateAction, useState, useEffect } from "react";
import axios from "axios";
import useDebounce from "../utils/useDebounce";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPowerOff, faRocket } from "@fortawesome/free-solid-svg-icons";
import styles from '../styles/Home.module.css'

import Container from '@material-ui/core/Container';
import Typography from '@material-ui/core/Typography';
import Box from '@material-ui/core/Box';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';


import styled from 'styled-components'

const MyContainer = styled.div`
  
`;

const MyBox = styled(Box)`
  height: 100vh;
  width: 100vw;
  padding: 2em;
`;

const MyPaper = styled(Paper)`
  padding-top: 5em;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
`;

export default function App() {

  var REFRESH_PERIOD = 1 * 5 * 1000; /* ms */

  const deploymentId = 'demo-deployment-1'
  const programName = 'jacuzzitest'

  const [data, setData] = useState({
    power: 1,
    temp: 120,
    mode: 0,
    fan: 10
    // powerful: 0,
    // quiet: 1,
    // swingh: 1,
    // swingv: 1
  });
  const [temp, setTemp] = useState(100);
  const [power, setPower] = useState(true);
  const [thermOil, setThermOil] = useState(0.0)
  const [thermWater, setThermWater] = useState(0.0)
  const [programData, setProgramData] = useState(null)
  const [lastDataFetchTime, setLastDataFetchTime] = useState(null)

  const debouncedData = useDebounce(data, 1000);

  useEffect(() => {
    const now = new Date()
    if (programData !== null) {
      const programFilter = Object.entries(programData).filter((k, v) => v.target_temp !== null).pop()
      if (programFilter === null) return
      console.log('PROGRAM:', programFilter[1])
      const program = programFilter[1]
      const targetTemp = program.target_temp
      setTemp(targetTemp)
    }

    if ((lastDataFetchTime === null) || (now - lastDataFetchTime) > REFRESH_PERIOD) {
      axios.get('/api/influx').then(response => {
        console.log(response.data)
        setThermOil(response.data.thermOil)
        setThermWater(response.data.thermWater)
        setProgramData(response.data.programData)
        setLastDataFetchTime(now)

      })
    }

  }, [thermOil])

  useEffect(() => {
    setData({ ...data, temp: temp });
  }, [temp]);

  useEffect(
    () => {
      if (debouncedData) {
        const postData = {...debouncedData, deploymentId:deploymentId, programName:programName}
        if (debouncedData.temp !== -1) {
          console.log('POST DATA:', postData)
          axios.post('/api/control', postData).then((response) => {
            console.log('RESPONSE IN APP:', response)
          })
        }
      }
    },
    [debouncedData]
  );


  useEffect(() => {
    setData({ ...data, power: power ? 1 : 0 });
  }, [power]);

  
  return (
    <MyBox>
      <MyPaper elevation={2} sx={{height: '100%'}}>
        <div className="main" style={{marginBottom: '3rem'}}>
          <Typography variant="h4" component="h1" gutterBottom>
            Hekla Heating
          </Typography>
          <br />
          <div className="center">
            <div className={styles.temperature}>
              <div
                className={`power ${power ? "on" : "off"}`}
                onClick={() => {
                  setPower(!power);
                }}
              >
                {/* <FontAwesomeIcon icon={faPowerOff} /> */}
              </div>
              <Knob
                fgColor="#FF645A"
                bgColor="#FEFEFE"
                inputColor="#FFFFFF"
                value={temp}
                onChange={setTemp}
                min={60}
                max={160}
                lineCap="round"
                thickness={0.15}
                angleOffset={220}
                angleArc={280}
                displayInput={false}
                displayCustom={() => (
                  <span className={styles.temp}>
                    {temp}
                    <span>°F</span>
                  </span>
                )}
                className="knob"
              />
            </div>
          </div>
        </div>
        <Stack spacing={4} direction='row'>
          <Typography variant="h6" component="h1">
              Water: {thermWater}
          </Typography>
          <Typography variant="h6" component="h1">
              Oil: {thermOil}
          </Typography>
        </Stack>
      </MyPaper>
    </MyBox>
  );
}
