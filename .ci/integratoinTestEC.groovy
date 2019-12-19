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
    TMPDIR = "${env.WORKSPACE}"
    REUSE_CONTAINERS = "true"
    HOME = "${env.WORKSPACE}"
    CONFIG_HOME = "${env.WORKSPACE}"
    BIN_DIR = "${env.WORKSPACE}/bin"
    HELM_INSTALL_DIR = "${env.BIN_DIR}"
    EC_WS ="${env.WORKSPACE}/${env.EC_DIR}"
    VENV = "${env.WORKSPACE}/.venv"
    PATH = "${env.WORKSPACE}/${env.BASE_DIR}/.ci/scripts:${env.VENV}/bin:${env.EC_WS}/bin:${env.EC_WS}/.ci/scripts:${env.BIN_DIR}:${env.PATH}"
    CLUSTER_CONFIG_FILE="${env.EC_WS}/tests/environments/elastic_cloud.yml"
    DOCKERELASTIC_SECRET = 'secret/apm-team/ci/docker-registry/prod'
    DOCKER_REGISTRY = 'docker.elastic.co'
    ENABLE_ES_DUMP = "true"
    BRANCH_NAME = "test-it-on-ec"
  }
  triggers {
    cron 'H H(3-4) * * 1-5'
    issueCommentTrigger('(?i).*(?:jenkins\\W+)?run\\W+(?:the\\W+)?tests(?:\\W+please)?.*')
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
    string(name: 'ELASTIC_STACK_VERSION', defaultValue: "8.0.0-SNAPSHOT", description: "Elastic Stack Git branch/tag to use")
    string(name: 'BUILD_OPTS', defaultValue: "--no-elasticsearch --no-apm-server --no-kibana --no-apm-server-dashboards --no-apm-server-self-instrument", description: "Addicional build options to passing compose.py")
    booleanParam(name: 'Run_As_Master_Branch', defaultValue: false, description: 'Allow to run any steps on a PR, some steps normally only run on master branch.')
  }
  stages {
    /**
     Checkout the code and stash it, to use it on other stages.
    */
    stage('Checkout'){
      steps {
        deleteDir()
        gitCheckout(basedir: "${BASE_DIR}")
        stash allowEmpty: true, name: 'source', useDefaultExcludes: false
      }
    }
    stage('Provision Elastic Cloud environment'){
      steps {
        dockerLogin(secret: "${DOCKERELASTIC_SECRET}", registry: "${DOCKER_REGISTRY}")
        dir("${EC_DIR}"){
          git(branch: 'master-v2.0',
            credentialsId: 'f6c7695a-671e-4f4f-a331-acdce44ff9ba',
            url: 'git@github.com:elastic/observability-test-environments.git'
          )
          withVaultEnv(){
            dir('ansible'){
              sh('export')
              script {
                def config = readYaml(file: "${CLUSTER_CONFIG_FILE}")
                config.k8s.cluster_name = "${config.k8s.cluster_name}-${BUILD_NUMBER}"
                config.elasticsearch.version = "${params.ELASTIC_STACK_VERSION}"
                config.kibana.version = "${params.ELASTIC_STACK_VERSION}"
                config.apm.version = "${params.ELASTIC_STACK_VERSION}"
                sh(label: 'Cat config', script: "cat ${CLUSTER_CONFIG_FILE}")
                sh(label: 'Delete old config', script: "rm ${CLUSTER_CONFIG_FILE}")
                writeYaml(file: "${CLUSTER_CONFIG_FILE}", data: config)
              }
              sh(label: "Deploy Cluster", script: "make deploy-cluster")
              archiveArtifacts(allowEmptyArchive: true, artifacts: 'cluster-info/**')
              setEnvVar('EC_SECRETS', "${env.EC_WS}/ansible/build/k8s")
              setEnvVar('APM_SERVER_URL', readYaml(file: "${env.EC_SECRETS}/cluster-secrets.yaml").stringData.url)
              setEnvVar('APM_SERVER_SECRET_TOKEN', readYaml(file: "${env.EC_SECRETS}/cluster-secrets.yaml").stringData.token)
              setEnvVar('ES_URL', readYaml(file: "${env.EC_SECRETS}/es-secrets.yaml").stringData.url)
              setEnvVar('KIBANA_URL', readYaml(file: "${env.EC_SECRETS}/kibana-secrets.yaml").stringData.url)
            }
          }
        }
      }
    }
    stage("All") {
      environment {
        BUILD_OPTS = "${params.BUILD_OPTS} --apm-server-url ${env.APM_SERVER_URL} --apm-server-secret-token ${env.APM_SERVER_SECRET_TOKEN}"
      }
      steps {
        dir("${BASE_DIR}"){
          sh ".ci/scripts/all.sh"
        }
      }
    }
  }
  post {
    cleanup {
      notifyBuildResult()
      destroyClusters()
    }
  }
}

def withVaultEnv(Closure body){
  getVaultSecret.readSecretWrapper {
    def token = getVaultSecret.getVaultToken(env.VAULT_ADDR, env.VAULT_ROLE_ID, env.VAULT_SECRET_ID)
    withEnvMask(vars: [
      [var: 'VAULT_TOKEN', password: token],
      [var: 'VAULT_AUTH_METHOD', password: 'approle']
    ]){
      body()
    }
  }
}

def destroyClusters(){
  def deployConfig = readYaml(file: "${CLUSTER_CONFIG_FILE}")
  dir("${EC_DIR}/ansible/build"){
    catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
      sh(label: 'Destroy k8s cluster', script: 'make destroy-cluster')
    }
    catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
      if(deployConfig.elasticsearch.type == 'ec'){
        withVaultToken(){
          sh(label: 'Destroy EC clsuter', script: 'make -C elastic-cloud set-auth-env destroy-cluster')
        }
      }
    }
  }
}
