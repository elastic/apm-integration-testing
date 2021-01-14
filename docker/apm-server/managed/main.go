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

	"github.com/pkg/errors"
)

func main() {
	setup()
	// create a reverse proxy to the APM Server running via Elastic Agent,
	// headers are not rewritten, as not considered important right now.
	target, _ := url.Parse("http://elastic-agent:8200")
	http.Handle("/", httputil.NewSingleHostReverseProxy(target))
	if err := http.ListenAndServe(":8200", nil); err != nil {
		log.Fatal(err)
		os.Exit(-1)
	}
}

func setup() {
	client := newKibanaClient()
	if err := cleanup(client); err != nil {
		log.Fatal(err)
		os.Exit(-1)
	}
	if err := addAPMPolicy(client); err != nil {
		log.Fatal(err)
		os.Exit(-1)
	}
}

type kibanaClient struct {
	fleetURL string
	pkgURL   string
}
type item struct {
	ID string `json:"id"`
}
type items struct {
	Items []item `json:"items"`
}

func newKibanaClient() *kibanaClient {
	host := os.Getenv("KIBANA_HOST")
	if host == "" {
		host = "http://admin:changeme@localhost:5601"
	}
	return &kibanaClient{
		fleetURL: fmt.Sprintf("%s/api/fleet", host),
		pkgURL:   "https://epr-snapshot.elastic.co",
	}
}

func cleanup(client *kibanaClient) error {
	result, err := client.getPackagePolicies(fmt.Sprintf("kuery=ingest-package-policies.package.name:%s", "apm"))
	if err != nil {
		return errors.Wrap(err, "cleanup")
	}
	var ids []string
	for _, item := range result.Items {
		ids = append(ids, item.ID)
	}
	return client.deletePackagePolicies(ids)
}

func addAPMPolicy(client *kibanaClient) error {
	agentPolicies, err := client.getAgentPolicies("kuery=ingest-agent-policies.is_default:true")
	if err != nil {
		return errors.Wrap(err, "addAPMPolicy")
	}
	if len(agentPolicies.Items) == 0 {
		return errors.New("no default agent policy found")
	}
	packages, err := client.getPackages("package=apm&experimental=true")
	if err != nil {
		return errors.Wrap(err, "addAPMPolicy")
	}
	if len(packages) == 0 {
		return errors.New("addAPMPolicy: no apm package found")
	}
	secretToken := os.Getenv("APM_SERVER_SECRET_TOKEN")
	apmPackage := packages[0]
	apmPackagePolicy := packagePolicy{
		Name:          "apm-integration-testing",
		Namespace:     "default",
		Enabled:       true,
		AgentPolicyID: agentPolicies.Items[0].ID,
		Package: packagePolicyPackage{
			Name:    apmPackage.Name,
			Version: apmPackage.Version,
			Title:   apmPackage.Title,
		},
		Inputs: []packagePolicyInput{{
			Type:    "apm",
			Enabled: true,
			Streams: []interface{}{},
			Vars: map[string]interface{}{
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
					"value": secretToken,
				},
			},
		}},
	}
	if err := client.addPackagePolicy(apmPackagePolicy); err != nil {
		return errors.Wrap(err, "addAPMPolicy")
	}
	return nil
}

func (client *kibanaClient) getPackages(query string) ([]eprPackage, error) {
	url := fmt.Sprintf("%s/search?%s", client.pkgURL, query)
	var packages []eprPackage
	if err := makeRequest(http.MethodGet, url, nil, &packages); err != nil {
		return packages, errors.Wrap(err, "getPackages")
	}
	return packages, nil
}

func (client *kibanaClient) getAgentPolicies(query string) (items, error) {
	url := fmt.Sprintf("%s/agent_policies?%s", client.fleetURL, query)
	var result items
	if err := makeRequest(http.MethodGet, url, nil, &result); err != nil {
		return items{}, errors.Wrap(err, "getAgentPolicies")
	}
	return result, nil
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

func (client *kibanaClient) getPackagePolicies(query string) (items, error) {
	url := fmt.Sprintf("%s/package_policies?%s", client.fleetURL, query)
	var result items
	if err := makeRequest(http.MethodGet, url, nil, &result); err != nil {
		return result, errors.Wrap(err, "getPackagePolicies")
	}
	return result, nil
}

// deletePackagePolicy deletes one or more package policies.
func (client *kibanaClient) deletePackagePolicies(ids []string) error {
	if len(ids) == 0 {
		return nil
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

// packagePolicy holds details of a Fleet Package Policy.
type packagePolicy struct {
	ID            string               `json:"id,omitempty"`
	Name          string               `json:"name"`
	Namespace     string               `json:"namespace"`
	Enabled       bool                 `json:"enabled"`
	Description   string               `json:"description"`
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
	Type    string                 `json:"type"`
	Enabled bool                   `json:"enabled"`
	Streams []interface{}          `json:"streams"`
	Config  map[string]interface{} `json:"config,omitempty"`
	Vars    map[string]interface{} `json:"vars,omitempty"`
}

type eprPackage struct {
	Name        string `json:"name"`
	Version     string `json:"version"`
	Release     string `json:"release"`
	Type        string `json:"type"`
	Title       string `json:"title"`
	Description string `json:"description"`
	Download    string `json:"download"`
	Path        string `json:"path"`
	Status      string `json:"status"`
}
