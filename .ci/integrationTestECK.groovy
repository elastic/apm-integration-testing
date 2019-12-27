#!/usr/bin/env groovy
@Library('apm@current') _

pipeline {
  agent { label 'linux && immutable' }
  environment {
    BASE_DIR="src/github.com/elastic/apm-integration-testing"
    EC_DIR="src/github.com/elastic/observability-test-environments"
    NOTIFY_TO = credentials('notify-to')
    JOB_GCS_BUCKET = credentials('gcs-bucket')
    PIPELINE_LOG_LEVEL='DEBUG'
    DOCKERELASTIC_SECRET = 'secret/apm-team/ci/docker-registry/prod'
    DOCKER_REGISTRY = 'docker.elastic.co'
  }
  triggers {
    cron 'H H(3-4) * * 1-5'
    issueCommentTrigger('(?i).*jenkins\\W+run\\W+(?:the\\W+)?tests(?:\\W+please)?.*')
  }
  options {
    timeout(time: 1, unit: 'HOURS')
    timestamps()
    ansiColor('xterm')
    disableResume()
    durabilityHint('PERFORMANCE_OPTIMIZED')
    rateLimitBuilds(throttle: [count: 60, durationName: 'hour', userBoost: true])
    quietPeriod(10)
  }
  parameters {
    string(name: 'BUILD_OPTS', defaultValue: "--no-elasticsearch --no-apm-server --no-kibana --no-apm-server-dashboards --no-apm-server-self-instrument", description: "Addicional build options to passing compose.py")
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
          git(branch: 'master-v2.0',
            credentialsId: 'f6c7695a-671e-4f4f-a331-acdce44ff9ba',
            url: 'git@github.com:elastic/observability-test-environments.git'
          )
        }
        stash allowEmpty: true, name: 'source', useDefaultExcludes: false
      }
    }
    stage('Tests On ECK'){
      matrix {
        agent { label 'linux && immutable' }
        environment {
          TMPDIR = "${env.WORKSPACE}"
          REUSE_CONTAINERS = "true"
          HOME = "${env.WORKSPACE}"
          CONFIG_HOME = "${env.WORKSPACE}"
          EC_WS ="${env.WORKSPACE}/${env.EC_DIR}"
          VENV = "${env.WORKSPACE}/.venv"
          PATH = "${env.WORKSPACE}/${env.BASE_DIR}/.ci/scripts:${env.VENV}/bin:${env.EC_WS}/bin:${env.EC_WS}/.ci/scripts:${env.PATH}"
          CLUSTER_CONFIG_FILE="${env.EC_WS}/tests/environments/eck.yml"
          ENABLE_ES_DUMP = "true"
        }
        axes {
          axis {
              name 'TEST'
              values 'all', 'dotnet', 'go', 'java', 'nodejs', 'python', 'ruby', 'rum'
          }
          axis {
              name 'ELASTIC_STACK_VERSION'
              values '8.0.0-SNAPSHOT', '7.5.0-SNAPSHOT', '7.4.0-SNAPSHOT'
          }
        }
        stages {
          stage('Prepare Test'){
            steps {
              log(level: "INFO", text: "Running tests - ${ELASTIC_STACK_VERSION} x ${TEST}")
              deleteDir()
              unstash 'source'
            }
          }
          stage('Provision ECK environment'){
            steps {
              dockerLogin(secret: "${DOCKERELASTIC_SECRET}", registry: "${DOCKER_REGISTRY}")
              dir("${EC_DIR}/ansible"){
                withVaultEnv(){
                  updateEnvConfig()
                  sh(label: "Deploy Cluster", script: "make deploy-cluster")
                  sh(label: "Rename cluster-info folder", script: "mv cluster-info cluster-info-${ELASTIC_STACK_VERSION}x${TEST}")
                  archiveArtifacts(allowEmptyArchive: true, artifacts: 'cluster-info*/**')
                }
              }
            }
          }
          stage("Test") {
            steps {
              dir("${BASE_DIR}"){
                withConfigEnv(){
                  sh ".ci/scripts/${TEST}.sh"
                }
              }
            }
          }
        }
        post {
          cleanup {
            wrappingUp("${TEST}")
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

def updateEnvConfig(){
  def config = readYaml(file: "${CLUSTER_CONFIG_FILE}")
  config.cluster_name = "${config.cluster_name}-${ELASTIC_STACK_VERSION}-${TEST}-${BUILD_NUMBER}"
  config.elasticsearch.image = "docker.elastic.co/observability-ci/elasticsearch:${ELASTIC_STACK_VERSION}"
  config.kibana.image = "docker.elastic.co/observability-ci/kibana:${ELASTIC_STACK_VERSION}"
  config.apm.image = "docker.elastic.co/observability-ci/apm-server:${ELASTIC_STACK_VERSION}"
  sh(label: 'Delete old config', script: "rm ${CLUSTER_CONFIG_FILE}")
  writeYaml(file: "${CLUSTER_CONFIG_FILE}", data: config)
  archiveArtifacts(allowEmptyArchive: true, artifacts: "${CLUSTER_CONFIG_FILE}", onlyIfSuccessful: true)
}

def withConfigEnv(Closure body) {
  def ecSecrets = "${env.EC_WS}/ansible/build/k8s"
  def apm = readYaml(file: "${ecSecrets}/apm-secrets.yaml")
  def es = readYaml(file: "${ecSecrets}/es-secrets.yaml")
  def kb = readYaml(file: "${ecSecrets}/kibana-secrets.yaml")
  withEnvMask(vars: [
    [var: 'APM_SERVER_URL', password: apm.stringData.url],
    [var: 'APM_SERVER_SECRET_TOKEN', password: apm.stringData.token],
    [var: 'ES_URL', password: es.stringData.url],
    [var: 'ES_USER', password: es.stringData.user],
    [var: 'ES_PASS', password: es.stringData.password],
    [var: 'KIBANA_URL', password: kb.stringData.url],
    [var: 'BUILD_OPTS', password: "${params.BUILD_OPTS} --apm-server-url ${apm.stringData.url} --apm-server-secret-token ${apm.stringData.token}"]
  ]){
    body()
  }
}

def wrappingUp(label){
  dir("${BASE_DIR}"){
    def stepName = label.replace(";","/")
      .replace("--","_")
      .replace(".","_")
      .replace(" ","_")
    sh("./scripts/docker-get-logs.sh '${stepName}'|| echo 0")
    sh('make stop-env || echo 0')
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

def destroyClusters(){
  def deployConfig = readYaml(file: "${CLUSTER_CONFIG_FILE}")
  dir("${EC_DIR}/ansible/build"){
    catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
      if(deployConfig.k8s.enabled){
        sh(label: 'Destroy k8s cluster', script: 'make destroy-cluster')
      }
    }
    catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
      if(deployConfig.elasticsearch.type == 'ec'){
        withVaultToken(){
          retry(3){
            sh(label: 'Destroy EC cluster', script: 'make -C elastic-cloud set-auth-env destroy-cluster')
            sleep(10)
          }
        }
      }
    }
  }
}
