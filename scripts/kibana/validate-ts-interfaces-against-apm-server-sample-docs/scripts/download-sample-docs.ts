import prettier from 'prettier';
import axios from 'axios';
import { promisify } from 'util';
import fs from 'fs';
const writeFile = promisify(fs.writeFile);
import prettierRc from '../.prettierrc.json';

const [owner = 'elastic', branch = 'master'] = process.argv.slice(2);
console.log(`Downloading sample docs: ${owner}:${branch}`);

interface DocType {
  name: string;
  url: string;
  getFileContent: (data: any) => string;
}

const docTypes: DocType[] = [
  {
    name: 'spans',
    url: `https://raw.githubusercontent.com/elastic/apm-server/${branch}/beater/test_approved_es_documents/TestPublishIntegrationSpans.approved.json`,
    getFileContent: data => {
      return `import { SpanRaw } from '../apm-ui-interfaces/raw/span_raw';
      import { AllowUnknownProperties } from '../../scripts/helpers';
      export const sampleDoc:AllowUnknownProperties<SpanRaw>[] = ${JSON.stringify(
        data.events
      )}`;
    }
  },
  {
    name: 'transactions',
    url: `https://raw.githubusercontent.com/elastic/apm-server/${branch}/beater/test_approved_es_documents/TestPublishIntegrationTransactions.approved.json`,
    getFileContent: data => {
      return `import { TransactionRaw } from '../apm-ui-interfaces/raw/transaction_raw';
      import { AllowUnknownProperties } from '../../scripts/helpers';
      export const sampleDoc:AllowUnknownProperties<TransactionRaw>[] = ${JSON.stringify(
        data.events
      )}`;
    }
  },
  {
    name: 'errors',
    url: `https://raw.githubusercontent.com/elastic/apm-server/${branch}/beater/test_approved_es_documents/TestPublishIntegrationErrors.approved.json`,
    getFileContent: data => {
      return `import { ErrorRaw } from '../apm-ui-interfaces/raw/error_raw';
      import { AllowUnknownProperties } from '../../scripts/helpers';
      export const sampleDoc:AllowUnknownProperties<ErrorRaw>[] = ${JSON.stringify(
        data.events
      )}`;
    }
  },
  {
    name: 'metrics',
    url: `https://raw.githubusercontent.com/elastic/apm-server/${branch}/beater/test_approved_es_documents/TestPublishIntegrationMetricsets.approved.json`,
    getFileContent: data => {
      return `import { MetricRaw } from '../apm-ui-interfaces/raw/metric_raw';
      import { AllowUnknownProperties } from '../../scripts/helpers';
      export const sampleDoc:AllowUnknownProperties<MetricRaw>[] = ${JSON.stringify(
        data.events
      )}`;
    }
  },
  {
    name: 'minimal',
    url: `https://raw.githubusercontent.com/elastic/apm-server/${branch}/beater/test_approved_es_documents/TestPublishIntegrationMinimalEvents.approved.json`,
    getFileContent: data => {
      return `import { SpanRaw } from '../apm-ui-interfaces/raw/span_raw';
      import { TransactionRaw } from '../apm-ui-interfaces/raw/transaction_raw';
      import { ErrorRaw } from '../apm-ui-interfaces/raw/error_raw';
      import { MetricRaw } from '../apm-ui-interfaces/raw/metric_raw';
      import { AllowUnknownProperties } from '../../scripts/helpers';
      export const sampleDoc: AllowUnknownProperties<
        SpanRaw | TransactionRaw | ErrorRaw | MetricRaw
      >[] = ${JSON.stringify(data.events)}`;
    }
  }
];

const promises = docTypes.map(async docType => {
  const fileName = `./tmp/apm-server-docs/${docType.name}.ts`;
  const { data } = await axios.get(docType.url);

  const content = docType.getFileContent(data);

  const formattedContent = prettier.format(content, {
    ...prettierRc,
    parser: 'babel'
  });

  await writeFile(fileName, formattedContent);
});

Promise.all(promises);
