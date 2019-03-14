#!/usr/bin/env groovy

@Library('apm@current') _

pipeline {
  agent none
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
    booleanParam(name: 'Run_As_Master_Branch', defaultValue: true, description: 'Allow to run any steps on a PR, some steps normally only run on master branch.')
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
      }
    }
    /**
      launch integration tests.
    */
    stage("Integration Tests") {
      agent none
      steps {
        log(level: "INFO", text: "Launching Agent tests in parallel")
        /*
          Declarative pipeline's parallel stages lose the reference to the downstream job,
          because of that, I use the parallel step. It is probably a bug.
        */
        script {
          def downstreamJobs = [:]
          if(changeRequest() && !params.Run_As_Master_Branch){
            downstreamJobs = ['All': {runJob('All')}]
          } else {
            downstreamJobs = [
            'All': {runJob('All')},
            'Go': {runJob('Go')},
            'Java': {runJob('Java')},
            'Node.js': {runJob('Node.js')},
            'Python(disabled)': {
              //runJob('Python')
              echo "NOOP"
              },
            'Ruby': {runJob('Ruby')},
            'RUM': {runJob('RUM')}
            ]
          }
          parallel(downstreamJobs)
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
      node('master'){
        echoColor(text: '[FAILURE]', colorfg: 'red', colorbg: 'default')
        step([$class: 'Mailer', notifyEveryUnstableBuild: true, recipients: "${NOTIFY_TO}", sendToIndividuals: false])
      }
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
