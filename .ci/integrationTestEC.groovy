#!/usr/bin/env groovy
@Library('apm@current') _

pipeline {
  agent { label 'linux && immutable' }
  environment {
    BASE_DIR="src/github.com/elastic/apm-integration-testing"
    EC_DIR="src/github.com/elastic/observability-test-environments"
    NOTIFY_TO = credentials('notify-to')
    JOB_GCS_BUCKET = credentials('gcs-bucket')
    PIPELINE_LOG_LEVEL='INFO'
    DOCKERELASTIC_SECRET = 'secret/apm-team/ci/docker-registry/prod'
    DOCKER_REGISTRY = 'docker.elastic.co'
    ENABLE_ES_DUMP = "true"
    REUSE_CONTAINERS = "true"
    LANG = "C.UTF-8"
    LC_ALL = "C.UTF-8"
  }
  triggers {
    cron 'H H(5-7) * * 1-5'
  }
  options {
    timeout(time: 3, unit: 'HOURS')
    timestamps()
    ansiColor('xterm')
    disableResume()
    durabilityHint('PERFORMANCE_OPTIMIZED')
    rateLimitBuilds(throttle: [count: 60, durationName: 'hour', userBoost: true])
    quietPeriod(10)
  }
  parameters {
    string(name: 'BUILD_OPTS', defaultValue: "--no-elasticsearch --no-apm-server --no-kibana --no-apm-server-dashboards --no-apm-server-self-instrument", description: "Addicional build options to passing compose.py")
    booleanParam(name: 'destroy_mode', defaultValue: false, description: 'Run the script in destroy mode to destroy any cluster provisioned and delete vault secrets.')
    string(name: 'build_num_to_destroy', defaultValue: "", description: "Build number to destroy, it is needed on destroy_mode")
  }
  stages {
    /**
     Checkout the code and stash it, to use it on other stages.
    */
    stage('Checkout'){
      steps {
        deleteDir()
        gitCheckout(basedir: "${BASE_DIR}")
        dir("${EC_DIR}"){
          git(branch: 'master',
            credentialsId: 'f6c7695a-671e-4f4f-a331-acdce44ff9ba',
            url: 'git@github.com:elastic/observability-test-environments.git'
          )
        }
        stash allowEmpty: true, name: 'source', useDefaultExcludes: false
      }
    }
    stage('Tests On Elastic Cloud'){
      matrix {
        agent { label 'linux && immutable' }
        axes {
          axis {
              name 'ELASTIC_STACK_VERSION'
              values '8.0.0-SNAPSHOT', '7.7.0-SNAPSHOT', '7.6.1-SNAPSHOT'
          }
        }
        stages {
          stage('Prepare Test'){
            steps {
              log(level: "INFO", text: "Running tests - ${ELASTIC_STACK_VERSION}")
              deleteDir()
              unstash 'source'
            }
          }
          stage('Run ITs'){
            when {
              expression { return ! params.destroy_mode }
            }
            stages {
              stage('Provision Elastic Cloud environment'){
                steps {
                  dockerLogin(secret: "${DOCKERELASTIC_SECRET}", registry: "${DOCKER_REGISTRY}")
                  dir("${EC_DIR}/ansible"){
                    withTestEnv(){
                      sh(label: "Deploy Cluster", script: "make create-cluster")
                      sh(label: "Rename cluster-info folder", script: "mv build/cluster-info.html cluster-info-${ELASTIC_STACK_VERSION}.html")
                      archiveArtifacts(allowEmptyArchive: true, artifacts: 'cluster-info-*')
                    }
                  }
                  stash allowEmpty: true, includes: "${EC_DIR}/ansible/build/config_secrets.yml", name: "secrets-${ELASTIC_STACK_VERSION}"
                }
              }
              stage("Test Go") {
                steps {
                  runTest('go')
                }
                post {
                  cleanup {
                    grabResultsAndLogs("${ELASTIC_STACK_VERSION}-go")
                  }
                }
              }
              stage("Test .NET") {
                steps {
                  runTest('dotnet')
                }
                post {
                  cleanup {
                    grabResultsAndLogs("${ELASTIC_STACK_VERSION}-dotnet")
                  }
                }
              }
              stage("Test Java") {
                steps {
                  runTest('java')
                }
                post {
                  cleanup {
                    grabResultsAndLogs("${ELASTIC_STACK_VERSION}-java")
                  }
                }
              }
              stage("Test Node.js") {
                steps {
                  runTest('nodejs')
                }
                post {
                  cleanup {
                    grabResultsAndLogs("${ELASTIC_STACK_VERSION}-nodejs")
                  }
                }
              }
              stage("Test Python") {
                steps {
                  runTest('python')
                }
                post {
                  cleanup {
                    grabResultsAndLogs("${ELASTIC_STACK_VERSION}-python")
                  }
                }
              }
              stage("Test Ruby") {
                steps {
                  runTest('ruby')
                }
                post {
                  cleanup {
                    grabResultsAndLogs("${ELASTIC_STACK_VERSION}-ruby")
                  }
                }
              }
              stage("Test RUM") {
                steps {
                  runTest('rum')
                }
                post {
                  cleanup {
                    grabResultsAndLogs("${ELASTIC_STACK_VERSION}-rum")
                  }
                }
              }
              stage("Test All") {
                steps {
                  runTest('all')
                }
                post {
                  cleanup {
                    grabResultsAndLogs("${ELASTIC_STACK_VERSION}-all")
                  }
                }
              }

            }
          }
        }
        post {
          cleanup {
            destroyClusters()
          }
        }
      }
    }
  }
  post {
    cleanup {
      notifyBuildResult()
    }
  }
}

def runTest(test){
  deleteDir()
  unstash 'source'
  withConfigEnv(){
    catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
      dir("${BASE_DIR}"){
        sh ".ci/scripts/${test}.sh"
      }
    }
  }
}

def withTestEnv(Closure body){
  def ecWs ="${env.WORKSPACE}/${env.EC_DIR}"
  withEnv([
    "TMPDIR=${env.WORKSPACE}",
    "HOME=${env.WORKSPACE}",
    "CONFIG_HOME=${env.WORKSPACE}",
    "VENV=${env.WORKSPACE}/.venv",
    "PATH=${env.WORKSPACE}/${env.BASE_DIR}/.ci/scripts:${env.VENV}/bin:${ecWs}/bin:${ecWs}/.ci/scripts:${env.PATH}",
    "CLUSTER_CONFIG_FILE=${ecWs}/tests/environments/elastic_cloud.yml",
    "BUILD_NUMBER=${ params.destroy_mode ? params.build_num_to_destroy : env.BUILD_NUMBER}"
  ]){
    withVaultEnv(){
      body()
    }
  }
}

def withVaultEnv(Closure body){
  getVaultSecret.readSecretWrapper {
    def token = getVaultSecret.getVaultToken(env.VAULT_ADDR, env.VAULT_ROLE_ID, env.VAULT_SECRET_ID)
    withEnvMask(vars: [
      [var: 'VAULT_TOKEN', password: token],
      [var: 'VAULT_AUTH_METHOD', password: 'approle'],
      [var: 'VAULT_AUTHTYPE', password: 'approle']
    ]){
      body()
    }
  }
}

def withConfigEnv(Closure body) {
  unstash "secrets-${ELASTIC_STACK_VERSION}"
  def config = readYaml(file: "${EC_DIR}/ansible/build/config_secrets.yml")
  def esJson = getVaultSecret(secret: "${config.k8s_vault_elasticsearch_def_secret}")?.data.value
  def apmJson = getVaultSecret(secret: "${config.k8s_vault_apm_def_secret}")?.data.value
  def kbJson = getVaultSecret(secret: "${config.k8s_vault_kibana_def_secret}")?.data.value
  def es = readJSON(text: esJson)
  def apm = readJSON(text: apmJson)
  def kb = readJSON(text: kbJson)

  withEnvMask(vars: [
    [var: 'APM_SERVER_URL', password: apm.url],
    [var: 'ELASTIC_APM_SECRET_TOKEN', password: apm.token],
    [var: 'ES_URL', password: es.url],
    [var: 'ES_USER', password: es.username],
    [var: 'ES_PASS', password: es.password],
    [var: 'KIBANA_URL', password: kb.url],
    [var: 'BUILD_OPTS', password: "${params.BUILD_OPTS} --apm-server-url ${apm.url} --apm-server-secret-token ${apm.token}"]
  ]){
    body()
  }
}

def grabResultsAndLogs(label){
  withConfigEnv(){
    dir("${BASE_DIR}"){
      def stepName = label.replace(";","/")
        .replace("--","_")
        .replace(".","_")
        .replace(" ","_")
      sh("./scripts/docker-get-logs.sh '${stepName}'|| echo 0")
      sh('make stop-env || echo 0')
      sh('.ci/scripts/remove_env.sh docker-info')
      archiveArtifacts(
          allowEmptyArchive: true,
          artifacts: 'docker-info/**,**/tests/results/data-*.json,,**/tests/results/packetbeat-*.json',
          defaultExcludes: false)
      junit(
        allowEmptyResults: true,
        keepLongStdio: true,
        testResults: "**/tests/results/*-junit*.xml")
    }
  }
}

def destroyClusters(){
  stage('Destroy Cluster'){
    dir("${EC_DIR}/ansible"){
      withTestEnv(){
        catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
          sh(label: 'Destroy k8s cluster', script: 'make destroy-cluster')
        }
      }
    }
  }
}
