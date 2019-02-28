#!/usr/bin/env groovy
@Library('apm@v1.0.8') _

pipeline {
  agent any
  environment {
    BASE_DIR="src/github.com/elastic/apm-integration-testing"
    NOTIFY_TO = credentials('notify-to')
    JOB_GCS_BUCKET = credentials('gcs-bucket')
    PIPELINE_LOG_LEVEL='INFO'
  }
  options {
    timeout(time: 1, unit: 'HOURS')
    buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '20', daysToKeepStr: '30'))
    timestamps()
    ansiColor('xterm')
    disableResume()
    durabilityHint('PERFORMANCE_OPTIMIZED')
  }
  triggers {
    cron 'H H(3-4) * * 1-5'
    issueCommentTrigger('.*(?:jenkins\\W+)?run\\W+(?:the\\W+)?tests(?:\\W+please)?.*')
  }
  parameters {
    string(name: 'ELASTIC_STACK_VERSION', defaultValue: "6.6 --release", description: "Elastic Stack Git branch/tag to use")
    string(name: 'BUILD_OPTS', defaultValue: "", description: "Addicional build options to passing compose.py")
    booleanParam(name: 'DISABLE_BUILD_PARALLEL', defaultValue: true, description: "Disable the build parallel option on compose.py, disable it is better for error detection.")
    booleanParam(name: 'Run_As_Master_Branch', defaultValue: false, description: 'Allow to run any steps on a PR, some steps normally only run on master branch.')
  }
  stages{
    /**
     Checkout the code and stash it, to use it on other stages.
    */
    stage('Checkout'){
      agent { label 'flyweight' }
      options { skipDefaultCheckout() }
      steps {
        deleteDir()
        gitCheckout(basedir: "${BASE_DIR}")
        stash allowEmpty: true, name: 'source', useDefaultExcludes: false
      }
    }

    stage("All Test Only") {
      agent { label 'flyweight' }
      options { skipDefaultCheckout() }
      when {
        beforeAgent true
        changeRequest()
      }
      steps {
        runJob('All', '--nodejs-agent-package=elastic/apm-agent-nodejs#1.x --python-agent-package=git+https://github.com/elastic/apm-agent-python.git@3.x --ruby-agent-version-state=github --ruby-agent-version=1.x')
      }
    }
    /**
      launch integration tests.
    */
    stage("Integration Tests") {
      agent { label 'flyweight' }
      options { skipDefaultCheckout() }
      when {
        beforeAgent true
        allOf {
          anyOf {
            not {
              changeRequest()
            }
            branch 'master'
            branch "\\d+\\.\\d+"
            branch "v\\d?"
            tag "v\\d+\\.\\d+\\.\\d+*"
            environment name: 'Run_As_Master_Branch', value: 'true'
          }
        }
      }
      steps {
        log(level: "INFO", text: "Launching Agent tests in parallel")
        /*
          Declarative pipeline's parallel stages lose the reference to the downstream job,
          because of that, I use the parallel step. It is probably a bug.
        */
        script {
          parallel(
            "Node.js": {
              runJob('Node.js')
            },
            "Python": {
              runJob('Python')
            },
            "Ruby": {
              runJob('Ruby')
            },
            "All": {
              runJob('All', '--nodejs-agent-package=elastic/apm-agent-nodejs#1.x --python-agent-package=git+https://github.com/elastic/apm-agent-python.git@3.x --ruby-agent-version-state=github --ruby-agent-version=1.x')
            }
          )
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
    string(name: 'INTEGRATION_TESTING_VERSION', value: env.GIT_COMMIT),
    string(name: 'BUILD_OPTS', value: buildOpts),
    string(name: 'UPSTREAM_BUILD', value: currentBuild.fullDisplayName),
    booleanParam(name: 'DISABLE_BUILD_PARALLEL', value: true)],
    propagate: true,
    quietPeriod: 10,
    wait: true)
}
