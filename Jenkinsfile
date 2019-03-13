#!/usr/bin/env groovy

@Library('apm@current') _

pipeline {
  agent any
  environment {
    BASE_DIR="src/github.com/elastic/apm-integration-testing"
    NOTIFY_TO = credentials('notify-to')
    JOB_GCS_BUCKET = credentials('gcs-bucket')
    PIPELINE_LOG_LEVEL='INFO'
  }
  triggers {
    cron 'H H(3-4) * * 1-5'
    issueCommentTrigger('.*(?:jenkins\\W+)?run\\W+(?:the\\W+)?tests(?:\\W+please)?.*')
  }
  options {
    timeout(time: 1, unit: 'HOURS')
    buildDiscarder(logRotator(numToKeepStr: '100', artifactNumToKeepStr: '100', daysToKeepStr: '30'))
    timestamps()
    ansiColor('xterm')
    disableResume()
    durabilityHint('PERFORMANCE_OPTIMIZED')
    rateLimitBuilds(throttle: [count: 60, durationName: 'hour', userBoost: true])
  }
  parameters {
    string(name: 'ELASTIC_STACK_VERSION', defaultValue: "7.0.0", description: "Elastic Stack Git branch/tag to use")
    string(name: 'BUILD_OPTS', defaultValue: "", description: "Addicional build options to passing compose.py")
    booleanParam(name: 'Run_As_Master_Branch', defaultValue: false, description: 'Allow to run any steps on a PR, some steps normally only run on master branch.')
  }
  stages{
    /**
     Checkout the code and stash it, to use it on other stages.
    */
    stage('Checkout'){
      agent { label 'master || immutable' }
      options { skipDefaultCheckout() }
      steps {
        deleteDir()
        gitCheckout(basedir: "${BASE_DIR}")
        stash allowEmpty: true, name: 'source', useDefaultExcludes: false
        dir("${BASE_DIR}"){
          sh '''
          echo "GIT_COMMIT=${GIT_COMMIT}"
          git rev-list HEAD -4 || echo KO
          git reflog -4 || echo KO
          '''
        }
      }
    }
    /**
      launch integration tests.
    */
    stage("Integration Tests") {
      parallel {
        stage('All') {
          agent { label 'linux && immutable' }
          options { skipDefaultCheckout() }
          steps {
            runJob('All')
          }
        }
        stage('Go') {
          agent { label 'linux && immutable' }
          options { skipDefaultCheckout() }
          when {
            anyOf {
              not {
                changeRequest()
              }
              environment name: 'Run_As_Master_Branch', value: 'true'
            }
          }
          steps {
            runJob('Go')
          }
        }
        stage('Java') {
          agent { label 'linux && immutable' }
          options { skipDefaultCheckout() }
          when {
            anyOf {
              not {
                changeRequest()
              }
              environment name: 'Run_As_Master_Branch', value: 'true'
            }
          }
          steps {
            runJob('Java')
          }
        }
        stage('Node.js') {
          agent { label 'linux && immutable' }
          options { skipDefaultCheckout() }
          when {
            anyOf {
              not {
                changeRequest()
              }
              environment name: 'Run_As_Master_Branch', value: 'true'
            }
          }
          steps {
            runJob('Node.js')
          }
        }
        stage('Python(disabled)') {
          agent { label 'linux && immutable' }
          options { skipDefaultCheckout() }
          when {
            anyOf {
              not {
                changeRequest()
              }
              environment name: 'Run_As_Master_Branch', value: 'true'
            }
          }
          steps {
            //runJob('Python')
            echo "NOOP"
          }
        }
        stage('Ruby') {
          agent { label 'linux && immutable' }
          options { skipDefaultCheckout() }
          when {
            anyOf {
              not {
                changeRequest()
              }
              environment name: 'Run_As_Master_Branch', value: 'true'
            }
          }
          steps {
            runJob('Ruby')
          }
        }
        stage('RUM') {
          agent { label 'linux && immutable' }
          options { skipDefaultCheckout() }
          when {
            anyOf {
              not {
                changeRequest()
              }
              environment name: 'Run_As_Master_Branch', value: 'true'
            }
          }
          steps {
            runJob('RUM')
          }
        }
      }
    }
  }
  post {
    success {
      echoColor(text: '[SUCCESS]', colorfg: 'green', colorbg: 'default')
    }
    aborted {
      echoColor(text: '[ABORTED]', colorfg: 'magenta', colorbg: 'default')
    }
    failure {
      echoColor(text: '[FAILURE]', colorfg: 'red', colorbg: 'default')
      step([$class: 'Mailer', notifyEveryUnstableBuild: true, recipients: "${NOTIFY_TO}", sendToIndividuals: false])
    }
    unstable {
      echoColor(text: '[UNSTABLE]', colorfg: 'yellow', colorbg: 'default')
    }
  }
}

def runJob(agentName, buildOpts = ''){
  def job = build(job: 'apm-integration-test-axis-pipeline',
    parameters: [
    string(name: 'agent_integration_test', value: agentName),
    string(name: 'ELASTIC_STACK_VERSION', value: params.ELASTIC_STACK_VERSION),
    string(name: 'INTEGRATION_TESTING_VERSION', value: env.GIT_BASE_COMMIT),
    string(name: 'BUILD_OPTS', value: buildOpts),
    string(name: 'UPSTREAM_BUILD', value: currentBuild.fullDisplayName),
    booleanParam(name: 'DISABLE_BUILD_PARALLEL', value: true)],
    propagate: true,
    quietPeriod: 10,
    wait: true)
}
