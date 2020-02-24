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
    REUSE_CONTAINERS = "true"
    NAME = agentMapping.id(params.INTEGRATION_TEST)
    INTEGRATION_TEST = "${params.INTEGRATION_TEST}"
    ELASTIC_STACK_VERSION = "${params.ELASTIC_STACK_VERSION}"
    BUILD_OPTS = "${params.BUILD_OPTS}"
    DETAILS_ARTIFACT = 'docs.txt'
    DETAILS_ARTIFACT_URL = "${env.BUILD_URL}artifact/${env.DETAILS_ARTIFACT}"
  }
  options {
    timeout(time: 1, unit: 'HOURS')
    buildDiscarder(logRotator(numToKeepStr: '300', artifactNumToKeepStr: '300'))
    timestamps()
    ansiColor('xterm')
    disableResume()
    durabilityHint('PERFORMANCE_OPTIMIZED')
    rateLimitBuilds(throttle: [count: 60, durationName: 'hour', userBoost: true])
  }
  parameters {
    choice(name: 'INTEGRATION_TEST', choices: ['.NET', 'Go', 'Java', 'Node.js', 'Python', 'Ruby', 'RUM', 'UI', 'All', 'Opbeans'], description: 'Name of the Tests or APM Agent you want to run the integration tests.')
    string(name: 'ELASTIC_STACK_VERSION', defaultValue: "8.0.0", description: "Elastic Stack Git branch/tag to use")
    string(name: 'BUILD_OPTS', defaultValue: "", description: "Addicional build options to passing compose.py")
    string(name: 'GITHUB_CHECK_NAME', defaultValue: '', description: 'Name of the GitHub check to be updated. Only if this build is triggered from another parent stream.')
    string(name: 'GITHUB_CHECK_REPO', defaultValue: '', description: 'Name of the GitHub repo to be updated. Only if this build is triggered from another parent stream.')
    string(name: 'GITHUB_CHECK_SHA1', defaultValue: '', description: 'Name of the GitHub repo to be updated. Only if this build is triggered from another parent stream.')
  }
  stages{
    /**
     Checkout the code and stash it, to use it on other stages.
    */
    stage('Checkout'){
      steps {
        githubCheckNotify('PENDING')
        deleteDir()
        gitCheckout(basedir: "${BASE_DIR}")
        stash allowEmpty: true, name: 'source', useDefaultExcludes: false
        script{
          def displayName = "apm-agent-${params.INTEGRATION_TEST}"
          if (params.INTEGRATION_TEST.equals('All') || params.INTEGRATION_TEST.equals('UI') || params.INTEGRATION_TEST.equals('Opbeans')) {
            displayName = "${params.INTEGRATION_TEST}"
          }
          currentBuild.displayName = "${displayName} - ${currentBuild.displayName}"
        }
      }
    }
    /**
      launch integration tests.
    */
    stage("Integration Tests"){
      environment {
        TMPDIR = "${WORKSPACE}"
        ENABLE_ES_DUMP = "true"
        PATH = "${WORKSPACE}/${BASE_DIR}/.ci/scripts:${env.PATH}"
        APP = agentMapping.app(params.INTEGRATION_TEST)
      }
      when {
        expression {
          return (params.INTEGRATION_TEST != 'All' &&
                  params.INTEGRATION_TEST != 'Opbeans')
        }
      }
      steps {
        deleteDir()
        unstash "source"
        dir("${BASE_DIR}"){
          script {
            def agentName = agentMapping.id(params.AGENT_INTEGRATION_TEST)
            def agentApp = agentMapping.app(params.AGENT_INTEGRATION_TEST)
            sh """#!/bin/bash
            export TMPDIR="${WORKSPACE}"
            .ci/scripts/agent.sh ${agentName} ${agentApp}
            """
          }
        }
      }
      post {
        always {
          wrappingup()
        }
      }
    }
    stage("All") {
      when {
        expression { return params.INTEGRATION_TEST == 'All' }
      }
      environment {
        TMPDIR = "${WORKSPACE}"
        REUSE_CONTAINERS = "true"
      }
      steps {
        deleteDir()
        unstash "source"
        dir("${BASE_DIR}"){
          sh ".ci/scripts/all.sh"
        }
      }
      post {
        always {
          wrappingup()
        }
      }
    }
    stage("UI") {
      when {
        expression { return params.INTEGRATION_TEST == 'UI' }
      }
      environment {
        TMPDIR = "${WORKSPACE}/${BASE_DIR}"
        HOME = "${WORKSPACE}/${BASE_DIR}"
      }
      steps {
        deleteDir()
        unstash "source"
        dir("${BASE_DIR}"){
          script {
            docker.image('node:12').inside() {
              sh(label: "Check Schema", script: ".ci/scripts/ui.sh")
            }
          }
        }
      }
      post {
        always {
          wrappingup()
        }
      }
    }
    stage("Opbeans") {
      when {
        expression { return params.INTEGRATION_TEST == 'Opbeans' }
      }
      environment {
        TMPDIR = "${WORKSPACE}"
        ENABLE_ES_DUMP = "true"
        PATH = "${WORKSPACE}/${BASE_DIR}/.ci/scripts:${env.PATH}"
      }
      steps {
        deleteDir()
        unstash "source"
        dir("${BASE_DIR}"){
          sh ".ci/scripts/opbeans.sh"
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
      githubCheckNotify(currentBuild.currentResult == 'SUCCESS' ? 'SUCCESS' : 'FAILURE')
      notifyBuildResult()
    }
  }
}

def wrappingup(){
  dir("${BASE_DIR}"){
    def stepName = agentMapping.id(params.AGENT_INTEGRATION_TEST)
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


/**
 Notify the GitHub check of the parent stream
**/
def githubCheckNotify(String status) {
  if (params.GITHUB_CHECK_NAME?.trim() && params.GITHUB_CHECK_REPO?.trim() && params.GITHUB_CHECK_SHA1?.trim()) {
    githubNotify context: "${params.GITHUB_CHECK_NAME}",
                 description: "${params.GITHUB_CHECK_NAME} ${status.toLowerCase()}",
                 status: "${status}",
                 targetUrl: "${env.RUN_DISPLAY_URL}",
                 sha: params.GITHUB_CHECK_SHA1, account: 'elastic', repo: params.GITHUB_CHECK_REPO, credentialsId: env.JOB_GIT_CREDENTIALS
  }
}
