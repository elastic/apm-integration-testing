/* global And, Given, Then */

export const DEFAULT_TIMEOUT = 60 * 1000;

Given("cluster credentials are present in the environment", () => {
  cy.checkCredentials();
});

When("the user checks the {string} service", service => {
  cy.navigateToAPMService(service);
  cy.waitForWelcomeTextDissapears();
});

Then("it contains transactions", () => {
  cy.get("table.euiTable--responsive tr.euiTableRow a.euiLink--primary", {
    timeout: DEFAULT_TIMEOUT
  })
    .its("length")
    .should("be.gt", 0);
});

// -----------

// identifier of the host type used in the target application (pod, container or trace)
// will be replaced after checking each host type, in the When method
let hostTypeID = "<empty>";

Given(
  "the transaction number {string} is selected for the {string} service",
  (transactionIndex, service) => {
    cy.navigateToAPMService(service);
    cy.get(
      `table.euiTable--responsive > tbody > tr.euiTableRow:nth-child(${transactionIndex}) > td:nth-child(1) > div.euiTableCellContent.euiTableCellContent--overflowingContent > span > a.euiLink--primary`,
      { timeout: DEFAULT_TIMEOUT }
    ).click();
  }
);

When("the user checks {string} {string}", (hostType, app) => {
  cy.clickOnTransactionActions();

  cy.contains(`${hostType} ${app}`, { timeout: DEFAULT_TIMEOUT })
    .invoke("attr", "href")
    .then($href => {
      // using Cypress' then to capture object's HREF element
      hostTypeID = extractHostTypeIDFromURL(hostType, $href);
    });

  cy.contains(`${hostType} ${app}`, { timeout: DEFAULT_TIMEOUT }).click({
    force: true
  });
});

function extractHostTypeIDFromURL(hostType, url) {
  var regex = /^.*\/app\/(.*)\/link-to\/(.*)-(.*)\/(.*)\?.*/;
  if (hostType === "Trace") {
    regex = /^.*\/app\/(.*)\/link-to\/(.*)\?(.*)trace\.id:%22(.*)%22%20OR%20(.*)/;
  }

  var groups = url.match(regex);
  return groups[4];
}

Then(
  "the {string} ID is used as filter in the {string} app",
  (hostType, app) => {
    var fieldIDLabel = "";
    if (hostType === "Pod") {
      fieldIDLabel = `kubernetes.pod.uid: ${hostTypeID}`;
    } else if (hostType === "Container") {
      fieldIDLabel = `container.id: ${hostTypeID}`;
    } else if (hostType === "Trace") {
      fieldIDLabel = `trace.id:"${hostTypeID}" OR "${hostTypeID}"`;
    }

    cy.log(fieldIDLabel);

    cy.get(".euiFieldSearch", { timeout: DEFAULT_TIMEOUT }).should(
      "have.value",
      fieldIDLabel
    );
  }
);
