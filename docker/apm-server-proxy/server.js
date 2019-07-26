const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
const util = require('util');
const writeFile = util.promisify(fs.writeFile);

const APM_SERVER_PORT =
  parseInt(process.env.ELASTIC_APM_SERVER_PORT, 10) || 8200;
const APM_SERVER_HOST = process.env.ELASTIC_APM_SERVER_HOST || '0.0.0.0';

// App
const app = express();
app.use(bodyParser.raw({ type: 'application/x-ndjson' }));

// used for health check
app.get('/', (req, res) => {
  console.log('Endpoint: /');
  res.status(202).end();
});

const payloads = [];

app.post('/intake/v2/events', (req, res) => {
  console.log('Endpoint: /intake/v2/events');
  const data = req.body.toString();
  payloads.push(data);

  res.status(202).end();
});

setInterval(persistToFile, 10000);

async function persistToFile() {
  console.log(`Persisting ${payloads.length} items`);
  await writeFile('./shared-volume/events.json', JSON.stringify(payloads));
  console.log('Persisted!');
}

app.listen(APM_SERVER_PORT, APM_SERVER_HOST);
console.log(`Running on http://${APM_SERVER_HOST}:${APM_SERVER_PORT}`);
