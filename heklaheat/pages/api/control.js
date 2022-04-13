import NextCors from 'nextjs-cors';
import axios from "axios";

export default async function handler(req, res) {

  console.log('DINGER?????????')
   // Run the cors middleware
   // nextjs-cors uses the cors package, so we invite you to check the documentation https://github.com/expressjs/cors
   await NextCors(req, res, {
      // Options
      methods: ['GET', 'HEAD', 'PUT', 'PATCH', 'POST', 'DELETE'],
      origin: '*',
      optionsSuccessStatus: 200, // some legacy browsers (IE11, various SmartTVs) choke on 204
   });

  const reqData = req.body

  const axiosInstance = axios.create({
    baseURL: 'http://sungbean.com:5000',
    timeout: 2000,
    headers: {'X-Custom-Header': 'foobar'}
  });

  const postBody = {
    id: reqData.deploymentId == 'demo-deployment-1' ? 'jumba_bot' : reqData.deploymentId,
    command: 'start',
    params: `${reqData.programName}, ${parseFloat(reqData.temp)}`
  }

  const data = await axiosInstance
    .post("/control", postBody)
    .catch((error) => {
      console.error(error);
  });

  return res.json({response: data.data})

}