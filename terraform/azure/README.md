# Azure resources with Terraform

This directory contains a set of directories containing terraform templates that can be used 
to deploy Azure resources for integration testing purposes. The name of each directory
describes the resources deployed.

This README is intended to be a quickstart guide for getting up and running quickly. For
more detailed documentation, please consult the [Terraform documentation.](https://www.terraform.io/docs/)

[Download and install Terraform to get started.](https://www.terraform.io/downloads.html)

## Authenticating to Azure

The Terraform `azurerm` provider requires 
[authenticating to Azure](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs#authenticating-to-azure) 
in order to deploy resources. Authentication can be performed in a number of ways:

### CI Authentication 

For CI scenarios, a Service Principal can be provided through the following environment variables

| Environment variable name | description                                                                |
| ------------------------- | -------------------------------------------------------------------------- |
| `ARM_CLIENT_ID`           | The client id of the Service Principal                                     |
| `ARM_CLIENT_SECRET`       | The client secret of the Service Principal                                 |
| `ARM_TENANT_ID`           | The tenant id of the Azure Active Directory                                |
| `ARM_SUBSCRIPTION_ID`     | The subscription id of the Azure subscription in which to deploy resources |


A Service Principal can be created using [Azure CLI 2.0](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/guides/service_principal_client_secret#creating-a-service-principal) or using [the Azure portal](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/guides/service_principal_client_secret#creating-a-service-principal-in-the-azure-portal). The Service Principal
credentials can be stored in and retrieved from Vault as needed for CI steps.

| IMPORTANT: The Service Principal must have [permission to list Service Principals from Microsoft Graph API](https://docs.microsoft.com/en-us/graph/api/serviceprincipal-list?view=graph-rest-1.0&tabs=http). The `Application.Read.All` permission is the least privileged permission that allows this. |
| --- |

Terraform will use the Service Principal specified in the environment variables to deploy resources.

### Local Development Authentication

For local development, a user can log into Azure CLI 2.0, set a subscription to use, and Terraform
will use the logged in user and subscription to deploy resources.

First, you will need to [install Azure CLI 2.0](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) and
ensure that `az` is in your `PATH`.

Now, log in to `az`

```sh
az login
```

You'll be directed to the browser to log in to the Azure portal. Then,

```sh
az account list
```

to list the subscriptions associated with your account, which will return something similar to the following

```json
[
  {
    "cloudName": "AzureCloud",
    "homeTenantId": "00000000-0000-0000-0000-000000000000",
    "id": "00000000-0000-0000-0000-000000000000",
    "isDefault": true,
    "managedByTenants": [],
    "name": "apm-agents-dev",
    "state": "Enabled",
    "tenantId": "00000000-0000-0000-0000-000000000000",
    "user": {
      "name": "user@example.com",
      "type": "user"
    }
  }
]
```

It's recommended to use the `apm-agents-dev` subscription. Select the `id` field of the `apm-agents-dev` subscription
object, and set it as the subscription to use

```sh
az account set --subscription "<id>"
```

Everything is now ready to deploy resources; Terraform will use the logged
in user to deploy resources.

## Deploying resources

Navigate to the directory containing the terraform template(s) associated with the resources to deploy. As an example,
say we want to deploy Azure Service Bus. First, navigate to `terraform/azure/service_bus`

```sh
cd terraform/azure/service_bus
```

Then, initialize the directory for use with terraform

```sh
terraform init
```

Now, apply the terraform plan

```sh
terraform apply
```

If the template expects input variables, you will now be prompted to supply them. When all input variables have been provided, 
terraform will build a plan and apply it to reach the desired state of configuration described in the template.

## Retrieving resource outputs

When terraform has finished the apply command, outputs can be retrieved to pass to tests, to allow them to work with the deployed
resources. In the case of Azure Service Bus, the connection string can be retrieved with

```sh
terraform output connection_string
```

## Deleting resources

Once resources are no longer needed, they can be deleted with

```sh
terraform destroy
```

The command will expect to be passed the **same values for input variables** as were supplied in `terraform apply`. Once
the destroy command has finished, the Azure resources will have been deleted.

## Commands in CI

Executing terraform commands in CI will be passed additional flags and arguments, to allow templates to be deployed without interaction.

For init

```sh
terraform init -no-color
```

For apply

```sh
terraform apply -auto-approve -no-color -input=false [-var <NAME>=<VALUE>]*
```

For outputs

```sh
terraform output -raw -no-color <NAME>
```

For destroy

```sh
terraform apply -auto-approve -no-color -input=false [-var <NAME>=<VALUE>]*
```
