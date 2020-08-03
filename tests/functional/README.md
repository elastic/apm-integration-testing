# End-To-End tests for the Observability solution

We want to make sure that any change in the different pieces of the Observability solution satisfy certain critical checks,
so for that reason we are adding [smoke tests](http://softwaretestingfundamentals.com/smoke-testing/) to verify that the any execution of this test suite includes the critical checks too.

>Smoke Testing, also known as “Build Verification Testing”, is a type of software testing that comprises of a non-exhaustive set of tests that aim at ensuring that the most important functions work. The result of this testing is used to decide if a build is stable enough to proceed with further testing.

## Tooling

The specification of these smoke tests has been done using the `BDD` (Behaviour-Driven Development) principles, where:

>BDD aims to narrow the communication gaps between team members, foster better understanding of the customer and promote continuous communication with real world examples.

The implementation of these smoke tests has been done with [Cypress](https://www.cypress.io/) + [Cucumber](https://cucumber.io/).

### Cucumber: BDD at its core

From their website:

>Cucumber is a tool that supports Behaviour-Driven Development(BDD), and it reads executable specifications written in plain text and validates that the software does what those specifications say. The specifications consists of multiple examples, or scenarios.

The way we are going to specify our software, which is the deployment of the test clusters, is using [`Gherkin`](https://cucumber.io/docs/gherkin/reference/).

>Gherkin uses a set of special keywords to give structure and meaning to executable specifications. Each keyword is translated to many spoken languages. Most lines in a Gherkin document start with one of the keywords.

The key part here is **executable specifications**: we will be able to automate the verification of the specifications and potentially get a coverage of these specs.

### Cypress: a test runner not using Selenium

From their website:

>Cypress makes setting up, writing, running and debugging tests easy.

For this POC, we have chosen Cypress over any other functional test framework because (sic) _"Cypress tests are only written in JavaScript"_, and the majority of our teams are tightly related to frontend development, so it seems reasonable to choose it.

Besides, (sic) _"Cypress is all in one"_, so no need to install any other tooling in the machines (local or CI).

### Test Specification

All the Gherkin (Cucumber) specifications are written in `.feature` files.

A good example could be [this one](./cypress/integration/apm-ui.feature).

### Test Implementation

We are using Cypress + Cucumber to implement the tests, where we create connections to the `Given`, `When`, `Then`, `And`, etc. in a well-known file structure, using feature file name as the parent directory for the Javascript files.

As an example, the Javascript implementation of the `apm-ui.feature` is located under the [./cypress/integration/apm-ui](./cypress/integration/apm-ui) directory. For the sake of simplicity, we are not reusing steps, so the javascript files contains all of them in one single file.

### Tests reports

We are using a nice visualisation of the test scenarios, using a parser of the Cucumber tests to generate an HTML page. To check this HTML report, execute following commands:

```shell
$ npm run test:ci
$ open ./cypress/html-reports/index.html
```

## Preparing the tests

The tests are located under the [./tests/functional](./tests/functional) directory. Because these tests run against a live environment, we need to spin up the Docker Compose services provided by this project. You can check the main [README.md](../../README.md) file of the [QUICKSTART.md](../../QUICKSTART.md) guide.

>The easiest way of running the services is executing this command:

```shell
$ ./scripts/compose.py start --release --with-opbeans-go 7.9.0-SNAPSHOT
```

It's **very important** to spin up the services that are going to be used in the tests, in this case the `opbeans-go` service, which is the only one used at this time.

## Running the tests

Place your terminal in the root directory of these tests and there execute Node's classic:

```shell
$ npm run test
```

It will spin up Cypress app so you can interact with its UI to run the tests.

On the other hand, if you prefer running the tests in a non-interactive manner, as the CI does, please run:

```shell
$ npm run test:ci
```
