#!/usr/bin/env groovy
@Library('apm@current') _

pipeline {
  agent { label 'linux && immutable && docker' }
  environment {
    BASE_DIR="src/github.com/elastic/apm-integration-testing"
    NOTIFY_TO = credentials('notify-to')
    JOB_GCS_BUCKET = credentials('gcs-bucket')
    JOB_GIT_CREDENTIALS = '2a9602aa-ab9f-4e52-baf3-b71ca88469c7-UserAndToken'
    PIPELINE_LOG_LEVEL = 'INFO'
  }
  triggers {
    cron 'H H(3-4) * * 1-5'
  }
  options {
    timeout(time: 1, unit: 'HOURS')
    buildDiscarder(logRotator(numToKeepStr: '300', artifactNumToKeepStr: '300', daysToKeepStr: '30'))
    timestamps()
    ansiColor('xterm')
    disableResume()
    durabilityHint('PERFORMANCE_OPTIMIZED')
    rateLimitBuilds(throttle: [count: 10, durationName: 'hour', userBoost: true])
  }
  stages{
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
    /**
      launch integration tests.
    */
    stage('Upgrade Tests'){
      steps {
        deleteDir()
        unstash "source"
        dir("${BASE_DIR}"){
          sh '.ci/scripts/7.0-upgrade.sh'
        }
      }
      post {
        always {
          wrappingup()
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

def wrappingup(){
  dir("${BASE_DIR}"){
    sh("./scripts/docker-get-logs.sh 'upgrade'|| echo 0")
    sh('make stop-env || echo 0')
    archiveArtifacts(
        allowEmptyArchive: true,
        artifacts: 'docker-info/**,**/tests/results/data-*.json,,**/tests/results/packetbeat-*.json',
        defaultExcludes: false)
    junit(
      allowEmptyResults: false,
      keepLongStdio: true,
      testResults: "**/tests/results/*-junit*.xml")
  }
}
