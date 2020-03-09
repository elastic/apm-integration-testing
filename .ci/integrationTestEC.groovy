#!/usr/bin/env groovy

pipeline {
  agent { label 'linux && immutable' }
  stages {
    stage('Tests On Elastic Cloud'){
      matrix {
        agent { label 'linux && immutable' }
        environment {
          PATH = "/tmp/aaaa/.ci/scripts:/tmp/bin:aaaa/bin:aaaa/.ci/scripts:${env.PATH}"
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
              echo "Running tests - ${ELASTIC_STACK_VERSION} x ${TEST}"
            }
          }
        }
      }
    }
  }
}
