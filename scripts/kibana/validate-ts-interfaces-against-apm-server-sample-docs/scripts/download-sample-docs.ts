import prettier from 'prettier';
import axios from 'axios';
import { promisify } from 'util';
import fs from 'fs';
const writeFile = promisify(fs.writeFile);
import prettierRc from '../.prettierrc.json';

const [owner = 'elastic', branch = 'master'] = process.argv.slice(2);
console.log(`Downloading sample docs: ${owner}:${branch}`);

interface DocType {
  interfaceName: string;
  interfacePath: string;
  url: string;
}

const docTypes: DocType[] = [
  {
    interfaceName: 'SpanRaw',
    interfacePath: '../apm-ui-interfaces/raw/span_raw',
    url: `https://raw.githubusercontent.com/elastic/apm-server/${branch}/beater/test_approved_es_documents/TestPublishIntegrationSpans.approved.json`
  },
  {
    interfaceName: 'TransactionRaw',
    interfacePath: '../apm-ui-interfaces/raw/transaction_raw',
    url: `https://raw.githubusercontent.com/elastic/apm-server/${branch}/beater/test_approved_es_documents/TestPublishIntegrationTransactions.approved.json`
  },
  {
    interfaceName: 'ErrorRaw',
    interfacePath: '../apm-ui-interfaces/raw/error_raw',
    url: `https://raw.githubusercontent.com/elastic/apm-server/${branch}/beater/test_approved_es_documents/TestPublishIntegrationErrors.approved.json`
  },
  {
    interfaceName: 'MetricRaw',
    interfacePath: '../apm-ui-interfaces/raw/metric_raw',
    url: `https://raw.githubusercontent.com/elastic/apm-server/${branch}/beater/test_approved_es_documents/TestPublishIntegrationMetricsets.approved.json`
  }
];

docTypes.map(docType => writeConvertedFile(docType));

async function writeConvertedFile({
  interfaceName,
  interfacePath,
  url
}: DocType) {
  const name = `${interfaceName}Docs`;
  const fileName = `./tmp/apm-server-docs/${name}.ts`;
  const { data } = await axios.get(url);

  const content = `import { ${interfaceName} } from '${interfacePath}';
  import { AllowUnknownProperties } from '../../scripts/helpers';
  export const ${name}:AllowUnknownProperties<${interfaceName}>[] = ${JSON.stringify(
    data.events
  )}`;

  const formattedContent = prettier.format(content, {
    ...prettierRc,
    parser: 'babel'
  });

  await writeFile(fileName, formattedContent);
}
