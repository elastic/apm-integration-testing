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
  }
  triggers {
    cron 'H H(3-4) * * 1-5'
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
    stage('Tests On Elastic Cloud'){
      matrix {
        agent { label 'linux && immutable' }
        axes {
          axis {
              name 'TEST'
              values 'all', 'dotnet', 'go', 'java', 'nodejs', 'python', 'ruby', 'rum'
          }
          axis {
              name 'ELASTIC_STACK_VERSION'
              values '8.0.0-SNAPSHOT', '7.7.0-SNAPSHOT', '7.6.1-SNAPSHOT', '6.8.7-SNAPSHOT'
          }
        }
        stages {
          stage('Prepare Test'){
            environment {
              TMPDIR = "${env.WORKSPACE}"
              REUSE_CONTAINERS = "true"
              HOME = "${env.WORKSPACE}"
              CONFIG_HOME = "${env.WORKSPACE}"
              EC_WS ="${env.WORKSPACE}/${env.EC_DIR}"
              VENV = "${env.WORKSPACE}/.venv"
              PATH = "${env.WORKSPACE}/${env.BASE_DIR}/.ci/scripts:${env.VENV}/bin:${env.EC_WS}/bin:${env.EC_WS}/.ci/scripts:${env.PATH}"
              CLUSTER_CONFIG_FILE="${env.EC_WS}/tests/environments/elastic_cloud.yml"
              ENABLE_ES_DUMP = "true"
            }
            steps {
              log(level: "INFO", text: "Running tests - ${ELASTIC_STACK_VERSION} x ${TEST}")
              deleteDir()
              unstash 'source'
            }
          }
        }
        post {
          cleanup {
            grabResultsAndLogs("${TEST}")
            destroyClusters()
          }
        }
      }
    }
  }
}
