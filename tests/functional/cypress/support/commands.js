// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --
// Cypress.Commands.add("login", (email, password) => { ... })
//
//
// -- This is a child command --
// Cypress.Commands.add("drag", { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add("dismiss", { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This is will overwrite an existing command --
// Cypress.Commands.overwrite("visit", (originalFn, url, options) => { ... })

export const DEFAULT_TIMEOUT = 60 * 1000;

const user = Cypress.env("user");
const password = Cypress.env("password");

Cypress.Commands.add("checkCredentials", () => {
  checkCredentialIsPresent(user, "user");
  checkCredentialIsPresent(password, "password");
});

function checkCredentialIsPresent(variable, name) {
  if (typeof variable === "undefined") {
    throw Error(
      `${name} is missing. Please set up CYPRESS_${name} environment variable`
    );
  }
  expect(variable.length, `${name} is incorrect`).to.be.greaterThan(0);
}

Cypress.Commands.add("kibanaLogin", () => {
  visitAuthenticatedURL("/");
});

Cypress.Commands.add("navigateToAPMService", service => {
  let apmURL = `/app/apm#/services/${service}/transactions?rangeFrom=now-24h&rangeTo=now&refreshInterval=0&refreshPaused=true&transactionType=request`;

  visitAuthenticatedURL(apmURL);
});

function visitAuthenticatedURL(url) {
  cy.visit(url, {
    auth: {
      username: user,
      password: password
    },
    log: false,
    followRedirect: true
  });
}

Cypress.Commands.add("clickOnTransactionActions", () => {
  cy.get(
    `#transactionActionMenu > .euiPopover__anchor > .euiButtonEmpty > .euiButtonEmpty__content > .euiButtonEmpty__text`
  ).click();
});

Cypress.Commands.add("waitForWelcomeTextDissapears", () => {
  cy.get("div#kbn_loading_message", { timeout: DEFAULT_TIMEOUT }).should(
    "not.be.visible"
  );
});
