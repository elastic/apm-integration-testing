# Testing in Cloud

## Continuous Integration

The APM Integration Tests are run periodically in Elastic Cloud [via Jenkins](https://apm-ci.elastic.co/job/apm-it-ec/).

The Jenkins cloud tests are defined [in Groovy](../.ci/integrationTestEC.groovy) and run on the APM CI.

## Running Cloud tests manually

It is also possible to run the integration test suite manually without needing to make use of the CI. To do so, follow the steps below:

1. Do a git checkout of the Observability Test Environments repo: `git checkout git@github.com:elastic/observability-test-environments.git`.
2. Ensure that you have this repo checked out as well: `git checkout git@github.com:elastic/apm-integration-testing.git`.
3. Ensure that you are logged into Elastic's Vault service. You can verify this by ensuring that results are returned for `vault list secret/observability-team`.
4. Export an environment variable corresponding to the version of the stack you wish to test on in Elastic Cloud. Possible values may be found by examining the [values present in the Groovy definition for the job](https://github.com/elastic/apm-integration-testing/blob/master/.ci/integrationTestEC.groovy#L58). As of this writing, those possible values are `8.0.0-SNAPSHOT`, `7.x`, `7.14.1`. Export the version before continuing: `export ELASTIC_STACK_VERSION=8.0.0-SNAPSHOT`.
5. Export an environment variable `CLUSTER_CONFIG_FILE` which points to the checked-out copy of `$(pwd)/observability-test-environments/tests/environments/elastic_cloud_tf_gcp.yml`.
6. Export a variable for your test run which differentiates your cluster from others. This value may be arbitrary and will just be used to ensure that your cluster does not overwrite another: `export BUILD_NUMBER=my-great-test`.
6. From the `observability-test-environments` directory checked out in step 1, run `make -C ansible create-cluster`. This will take several minutes to complete.
7. After the cluster has been configured, a number of additional environment variables will need to be exported. They are located in a file which should now be present in `observability-test-environments/ansible/build/config_secrets.yml`. The file contains various paths to Vault keys which store the secrets themselves. Below [is a table showing](#config-secrets) which environment variables must be set, which Vault keys they are stored in and which values they are located within the YAML data structure returned by a Vault lookup. Following the table, ensure that the allowed variables listed in the first column of the table are exported.
8. Export a variable called `BUILD_OPTS` which contains the flags which should be passed to the APM Integration Test suite. At a minimum, the following must be set: `--apm-server-url $APM_SERVER_URL --apm-server-secret-token $APM_SERVER_TOKEN`. To duplicate the values used by the CI, the following may also be added: `--no-elasticsearch --no-apm-server --no-kibana --no-apm-server-dashboards --no-apm-server-self-instrument`.
9. Run the tests as desired. Various scripts for starting up tests may be found in [the scripts directory](../.ci/scripts/). For example, to run all tests, execute `all.sh` or to run just the Python tests, execute `python.sh`.
10. Once testing has been concluded, please tear down your cloud environment by running `make -C ansible destroy-cluster` from the `observability-test-environments` directory.

#### Config secrets

The following variables must be exported to your shell in order to point the APM Integration Test runner at the provisioned cloud instance.

|ENV  |Config value for vault lookup|Value from Vault lookup|
|-----|----------|------------------------------------------|
|APM_SERVER_URL|k8s_vault_apm_def_secret|url|
|APM_SERVER_TOKEN|k8s_vault_apm_def_secret|token|
|ELASTIC_APM_SECRET_TOKEN|k8s_vault_apm_def_secret|url|
|ES_URL|k8s_vault_elasticsearch_def_secret|url|
|ES_USER|k8s_vault_elasticsearch_def_secret|username|
|ES_PASS|k8s_vault_elasticsearch_def_secret|password|
|KIBANA_URL|k8s_vault_kibana_def_secret|url|

### Accessing your cluster

After provisioning your cluster, examine `observability-test-environments/ansible/build/terraform/elastic_cloud/main.tf` to locate the name of your deployment.
