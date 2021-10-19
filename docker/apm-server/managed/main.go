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
	"strconv"
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
	apmPkg, err := client.getAPMPackage()
	if err != nil {
		return err
	}
	fmt.Println("apm package fetched")

	// define expected APM package policy
	expectedAPMPackagePolicy, err := apmPackagePolicy(policy.ID, apmPkg)
	if err != nil {
		return err
	}
	fmt.Println("apm package policy defined")

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
	fleetServer := ""
	if enable, err := strconv.ParseBool(os.Getenv("FLEET_SERVER_ENABLE")); err == nil && enable {
		fleetServer = "_fleet_server"
	}
	kuery := fmt.Sprintf("kuery=ingest-agent-policies.is_default%s:true", fleetServer)
	for ct := 0; ct < 20; ct++ {
		agentPolicies, err := client.getAgentPolicies(kuery)
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
func apmPackagePolicy(policyID string, pkg *eprPackage) (packagePolicy, error) {
	p := packagePolicy{
		Name:          "apm-integration-testing",
		Namespace:     "default",
		Enabled:       true,
		AgentPolicyID: policyID,
		Package: packagePolicyPackage{
			Name:    pkg.Name,
			Version: pkg.Version,
			Title:   pkg.Title,
		},
	}

	if len(pkg.PolicyTemplates) != 1 || len(pkg.PolicyTemplates[0].Inputs) != 1 {
		return p, fmt.Errorf("apm package policy input missing: %+v", pkg)
	}
	input := pkg.PolicyTemplates[0].Inputs[0]
	vars := make(map[string]map[string]interface{})
	for _, inputVar := range input.Vars {
		varMap := map[string]interface{}{"type": inputVar.Type}
		switch inputVar.Name {
		case "host":
			varMap["value"] = "0.0.0.0:8200"
		case "enable_rum":
			varMap["value"] = true
		case "secret_token":
			varMap["value"] = os.Getenv("APM_SERVER_SECRET_TOKEN")

		}
		vars[inputVar.Name] = varMap
	}
	p.Inputs = append(p.Inputs, packagePolicyInput{
		Type:    input.Type,
		Enabled: true,
		Streams: []interface{}{},
		Vars:    vars,
	})
	return p, nil
}

type kibanaClient struct {
	fleetURL string
}

func newKibanaClient() *kibanaClient {
	host := os.Getenv("KIBANA_HOST")
	if host == "" {
		host = "http://admin:changeme@kibana:5601"
	}
	return &kibanaClient{fleetURL: fmt.Sprintf("%s/api/fleet", host)}
}

func (client *kibanaClient) getAPMPackage() (*eprPackage, error) {
	url := fmt.Sprintf("%s/epm/packages?experimental=true", client.fleetURL)
	var pkgs eprPackagesResponse
	if err := makeRequest(http.MethodGet, url, nil, &pkgs); err != nil {
		return nil, err
	}
	for _, p := range pkgs.Packages {
		if p.Name != "apm" {
			continue
		}
		var apm eprPackageResponse
		url := fmt.Sprintf("%s/epm/packages/%s-%s", client.fleetURL, p.Name, p.Version)
		err := makeRequest(http.MethodGet, url, nil, &apm)
		return &apm.Package, err

	}
	return nil, errors.New("no apm package found")
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

type eprPackage struct {
	Name            string                  `json:"name"`
	Version         string                  `json:"version"`
	Release         string                  `json:"release"`
	Type            string                  `json:"type"`
	Title           string                  `json:"title"`
	Description     string                  `json:"description"`
	Download        string                  `json:"download"`
	Path            string                  `json:"path"`
	Status          string                  `json:"status"`
	PolicyTemplates []packagePolicyTemplate `json:"policy_templates"`
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

type packagePolicyTemplate struct {
	Inputs []packagePolicyTemplateInput `json:"inputs"`
}

type packagePolicyTemplateInput struct {
	Type         string                          `json:"type"`
	Title        string                          `json:"title"`
	TemplatePath string                          `json:"template_path"`
	Description  string                          `json:"description"`
	Vars         []packagePolicyTemplateInputVar `json:"vars"`
}

type packagePolicyTemplateInputVar struct {
	Name string `json:"name"`
	Type string `json:"type"`
}

type eprPackageResponse struct {
	Package eprPackage `json:"response"`
}

type eprPackagesResponse struct {
	Packages []eprPackage `json:"response"`
}
