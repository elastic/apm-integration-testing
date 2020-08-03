const reporter = require("cucumber-html-reporter");

const options = {
  theme: "hierarchy",
  jsonDir: "cypress/cucumber-json",
  output: "cypress/html-reports/index.html",
  reportSuiteAsScenarios: true,
  scenarioTimestamp: true,
  launchReport: false,
  ignoreBadJsonFile: true,
  scenarioTimestamp: true
};

reporter.generate(options);
