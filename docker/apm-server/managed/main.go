package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"time"

	"github.com/pkg/errors"
)

func main() {
	// setup APM package and add it to default policy
	if err := setupManagedAPM(); err != nil {
		log.Fatal(err)
	}

	// create a reverse proxy to the APM Server running via Elastic Agent,
	// headers are not rewritten, as not considered important right now.
	target, _ := url.Parse("http://elastic-agent:8200")
	http.Handle("/", httputil.NewSingleHostReverseProxy(target))
	if err := http.ListenAndServe(":8200", nil); err != nil {
		log.Fatal(err)
	}
}

func setupManagedAPM() error {
	client := newKibanaClient()
	policy, err := fetchDefaultPolicy(client)
	if err != nil {
		return err
	}
	fmt.Println("default policy fetched")

	// fetch the available apm package
	packages, err := client.getPackages("package=apm&experimental=true")
	if err != nil {
		return err
	}
	if len(packages) == 0 {
		return errors.New("no apm package found")
	}
	fmt.Println("apm package fetched")

	// define expected APM package policy
	expectedAPMPackagePolicy := apmPackagePolicy(policy.ID, packages[0])

	// fetch apm package installed to default policy and verify if it is aligned with
	// expected setup
	defaultPolicyPackages, err := client.getPackagePolicies(fmt.Sprintf("kuery=ingest-package-policies.policy_id:%s", policy.ID))
	if err != nil {
		log.Fatal(err)
	}
	var apmPackagePolicies []packagePolicy
	for _, p := range defaultPolicyPackages {
		for _, input := range p.Inputs {
			if input.Type == "apm" {
				apmPackagePolicies = append(apmPackagePolicies, p)
				break
			}
		}
	}
	var requiresSetup bool
	switch len(apmPackagePolicies) {
	case 0:
		requiresSetup = true
		fmt.Println("agent policy has no apm integration")
	case 1:
		// apm package is defined to always only have 1 Input
		fmt.Println("agent policy has existing apm integration")
		existing := apmPackagePolicies[0]
		// verify that package is enabled, has default namespace and expected package properties
		if !existing.Enabled ||
			existing.Namespace != expectedAPMPackagePolicy.Namespace ||
			existing.Package != expectedAPMPackagePolicy.Package {
			requiresSetup = true
		} else {
			// verify that variables are configured as expected
			for k, expected := range expectedAPMPackagePolicy.Inputs[0].Vars {
				configured, ok := existing.Inputs[0].Vars[k]
				if !ok || configured["type"] != expected["type"] || configured["value"] != expected["value"] {
					requiresSetup = true
					break
				}
			}
		}
	default:
		// multiple apm package policies lead to issues,
		// delete them and create a new setup
		fmt.Println("agent policy has multiple existing apm integration")
		requiresSetup = true
	}
	if !requiresSetup {
		fmt.Println("apm integration does not require setup")
		return nil
	}
	fmt.Println("apm integration requires setup")
	if err := client.deletePackagePolicies(apmPackagePolicies); err != nil {
		return err
	}
	if err := client.addPackagePolicy(expectedAPMPackagePolicy); err != nil {
		return err
	}
	fmt.Println("apm integration succesfully added to agent policy")
	return nil
}

func fetchDefaultPolicy(client *kibanaClient) (agentPolicy, error) {
	for ct := 0; ct < 20; ct++ {
		agentPolicies, err := client.getAgentPolicies("kuery=ingest-agent-policies.is_default_fleet_server:true")
		if err != nil {
			return agentPolicy{}, err
		}
		if len(agentPolicies) > 0 {
			// there's supposed to only be one default policy,
			// in case there are more, there is a bug in the agent integrations logic
			return agentPolicies[0], nil
		}
		time.Sleep(5 * time.Second)
	}
	return agentPolicy{}, errors.New("no default agent policy found")
}

// apmPackagePolicy defines the expected APM package policy
func apmPackagePolicy(policyID string, pkg eprPackage) packagePolicy {
	return packagePolicy{
		Name:          "apm-integration-testing",
		Namespace:     "default",
		Enabled:       true,
		AgentPolicyID: policyID,
		Package: packagePolicyPackage{
			Name:    pkg.Name,
			Version: pkg.Version,
			Title:   pkg.Title,
		},
		Inputs: []packagePolicyInput{{
			Type:    "apm",
			Enabled: true,
			Streams: []interface{}{},
			Vars: map[string]map[string]interface{}{
				"enable_rum": map[string]interface{}{
					"type":  "bool",
					"value": true,
				},
				"host": map[string]interface{}{
					"type":  "string",
					"value": "0.0.0.0:8200",
				},
				"secret_token": map[string]interface{}{
					"type":  "string",
					"value": os.Getenv("APM_SERVER_SECRET_TOKEN"),
				},
			},
		}}}
}

type kibanaClient struct {
	fleetURL string
	pkgURL   string
}

func newKibanaClient() *kibanaClient {
	host := os.Getenv("KIBANA_HOST")
	if host == "" {
		host = "http://admin:changeme@kibana:5601"
	}
	pkgURL := os.Getenv("XPACK_FLEET_REGISTRYURL")
	if pkgURL == "" {
		pkgURL = "https://epr.elastic.co"
	}
	return &kibanaClient{
		fleetURL: fmt.Sprintf("%s/api/fleet", host),
		pkgURL:   pkgURL,
	}
}

func (client *kibanaClient) getPackages(query string) ([]eprPackage, error) {
	url := fmt.Sprintf("%s/search?%s", client.pkgURL, query)
	var packages []eprPackage
	if err := makeRequest(http.MethodGet, url, nil, &packages); err != nil {
		return packages, errors.Wrap(err, "getPackages")
	}
	return packages, nil
}

func (client *kibanaClient) getAgentPolicies(query string) ([]agentPolicy, error) {
	url := fmt.Sprintf("%s/agent_policies?%s", client.fleetURL, query)
	var result struct {
		Items []agentPolicy `json:"items"`
	}
	if err := makeRequest(http.MethodGet, url, nil, &result); err != nil {
		return result.Items, errors.Wrap(err, "getAgentPolicies")
	}
	return result.Items, nil
}

func (client *kibanaClient) addPackagePolicy(policy packagePolicy) error {
	url := fmt.Sprintf("%s/package_policies", client.fleetURL)
	var buf bytes.Buffer
	if err := json.NewEncoder(&buf).Encode(&policy); err != nil {
		return err
	}
	var result interface{}
	if err := makeRequest(http.MethodPost, url, &buf, &result); err != nil {
		return errors.Wrap(err, "addPackagePolicies")
	}
	return nil
}

func (client *kibanaClient) getPackagePolicies(query string) ([]packagePolicy, error) {
	url := fmt.Sprintf("%s/package_policies?%s", client.fleetURL, query)
	var result struct {
		Items []packagePolicy `json:"items"`
	}
	if err := makeRequest(http.MethodGet, url, nil, &result); err != nil {
		return result.Items, errors.Wrap(err, "getPackagePolicies")
	}
	return result.Items, nil
}

// deletePackagePolicy deletes one or more package policies.
func (client *kibanaClient) deletePackagePolicies(policies []packagePolicy) error {
	if len(policies) == 0 {
		return nil
	}
	var ids []string
	for _, p := range policies {
		ids = append(ids, p.ID)
	}
	var params struct {
		PackagePolicyIDs []string `json:"packagePolicyIds"`
	}
	params.PackagePolicyIDs = ids
	var body bytes.Buffer
	if err := json.NewEncoder(&body).Encode(params); err != nil {
		return err
	}
	var result interface{}
	if err := makeRequest(http.MethodPost, client.fleetURL+"/package_policies/delete", &body, &result); err != nil {
		return errors.Wrap(err, "deletePackagePolicies")
	}
	return nil
}

func makeRequest(method string, url string, body io.Reader, out interface{}) error {
	req, err := http.NewRequest(method, url, body)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("kbn-xsrf", "1")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		body, _ := ioutil.ReadAll(resp.Body)
		return fmt.Errorf("request failed (%s): %s", resp.Status, body)
	}
	return json.NewDecoder(resp.Body).Decode(&out)
}

// agentPolicy holds details of a Fleet Agent Policy.
type agentPolicy struct {
	ID string `json:"id"`
}

// packagePolicy holds details of a Fleet Package Policy.
type packagePolicy struct {
	ID            string               `json:"id,omitempty"`
	Name          string               `json:"name"`
	Namespace     string               `json:"namespace"`
	Enabled       bool                 `json:"enabled"`
	AgentPolicyID string               `json:"policy_id"`
	OutputID      string               `json:"output_id"`
	Inputs        []packagePolicyInput `json:"inputs"`
	Package       packagePolicyPackage `json:"package"`
}

type packagePolicyPackage struct {
	Name    string `json:"name"`
	Version string `json:"version"`
	Title   string `json:"title"`
}

type packagePolicyInput struct {
	Type    string                            `json:"type"`
	Enabled bool                              `json:"enabled"`
	Streams []interface{}                     `json:"streams"`
	Vars    map[string]map[string]interface{} `json:"vars,omitempty"`
}

type eprPackage struct {
	Name    string `json:"name"`
	Version string `json:"version"`
	Title   string `json:"title"`
}
