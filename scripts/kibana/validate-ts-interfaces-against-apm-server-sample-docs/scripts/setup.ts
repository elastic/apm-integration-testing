import prettier from 'prettier';
import axios from 'axios';
import { promisify } from 'util';
import fs from 'fs';
const writeFile = promisify(fs.writeFile);
import prettierRc from '../.prettierrc.json';

const BRANCH = 'master';

interface DocType {
  interfaceName: string;
  interfacePath: string;
  url: string;
}

const docTypes: DocType[] = [
  {
    interfaceName: 'SpanRaw',
    interfacePath: '../apm-ui-interfaces/raw/SpanRaw',
    url: `https://raw.githubusercontent.com/elastic/apm-server/${BRANCH}/beater/test_approved_es_documents/TestPublishIntegrationSpans.approved.json`
  },
  {
    interfaceName: 'TransactionRaw',
    interfacePath: '../apm-ui-interfaces/raw/TransactionRaw',
    url: `https://raw.githubusercontent.com/elastic/apm-server/${BRANCH}/beater/test_approved_es_documents/TestPublishIntegrationTransactions.approved.json`
  },
  {
    interfaceName: 'ErrorRaw',
    interfacePath: '../apm-ui-interfaces/raw/ErrorRaw',
    url: `https://raw.githubusercontent.com/elastic/apm-server/${BRANCH}/beater/test_approved_es_documents/TestPublishIntegrationErrors.approved.json`
  }
];

docTypes.map(docType => writeConvertedFile(docType));

async function writeConvertedFile({
  interfaceName,
  interfacePath,
  url
}: DocType) {
  const name = `${interfaceName}Docs`;
  const fileName = `./temp/apm-server-docs/${name}.ts`;
  const { data } = await axios.get(url);

  const content = `import { ${interfaceName} } from '${interfacePath}';
  export const ${name}:${interfaceName}[] = ${JSON.stringify(data.events)}`;

  const formattedContent = prettier.format(content, {
    ...prettierRc,
    parser: 'babel'
  });

  await writeFile(fileName, formattedContent);
}
