Feature: APM UI features

Scenario Outline: As an APM UI user I want to check that <service> has transactions
  Given cluster credentials are present in the environment
  When the user checks the "<service>" service
  Then it contains transactions
Examples:
| service |
| opbeans-go |

Scenario Outline: As an APM user I want to check <hostType> logs for a transaction in <service>
  Given the transaction number "1" is selected for the "<service>" service
  When the user checks "<hostType>" "logs"
  Then the "<hostType>" ID is used as filter in the "logs" app
Examples:
| hostType | service |
| Container | opbeans-go |
| Trace | opbeans-go |
