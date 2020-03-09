#!/usr/bin/env groovy

pipeline {
  agent { label 'linux && immutable' }
  stages {
    stage('Tests On Elastic Cloud'){
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
          CLUSTER_CONFIG_FILE="${env.EC_WS}/tests/environments/elastic_cloud.yml"
          ENABLE_ES_DUMP = "true"
        }
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
            steps {
              log(level: "INFO", text: "Running tests - ${ELASTIC_STACK_VERSION} x ${TEST}")
              deleteDir()
              unstash 'source'
            }
          }
        }
      }
    }
  }
}
