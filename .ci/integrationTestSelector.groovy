#!/usr/bin/env groovy
@Library('apm@current') _

import groovy.transform.Field

/**
  translate from human agent name to its app name .
*/
@Field Map mapAgentsApps = [
  '.NET': 'dotnet',
  'Go': 'go-net-http',
  'Java': 'java-spring',
  'Node.js': 'nodejs-express',
  'Python': 'python-django',
  'Ruby': 'ruby-rails',
  'RUM': 'rumjs',
  'All': 'all',
  'UI': 'ui'
]

/**
  translate from human agent name to an ID.
*/
@Field Map mapAgentsIDs = [
  '.NET': 'dotnet',
  'Go': 'go',
  'Java': 'java',
  'Node.js': 'nodejs',
  'Python': 'python',
  'Ruby': 'ruby',
  'RUM': 'rum',
  'All': 'all',
  'UI': 'ui'
]

pipeline {
  agent { label 'linux && immutable && docker' }
  environment {
    BASE_DIR="src/github.com/elastic/apm-integration-testing"
    NOTIFY_TO = credentials('notify-to')
    JOB_GCS_BUCKET = credentials('gcs-bucket')
    JOB_GIT_CREDENTIALS = '2a9602aa-ab9f-4e52-baf3-b71ca88469c7-UserAndToken'
    PIPELINE_LOG_LEVEL = 'INFO'
  }
  options {
    timeout(time: 1, unit: 'HOURS')
    buildDiscarder(logRotator(numToKeepStr: '300', artifactNumToKeepStr: '300', daysToKeepStr: '30'))
    timestamps()
    ansiColor('xterm')
    disableResume()
    durabilityHint('PERFORMANCE_OPTIMIZED')
  }
  parameters {
    choice(name: 'AGENT_INTEGRATION_TEST', choices: ['.NET', 'Go', 'Java', 'Node.js', 'Python', 'Ruby', 'RUM', 'UI', 'All'], description: 'Name of the APM Agent you want to run the integration tests.')
    string(name: 'ELASTIC_STACK_VERSION', defaultValue: "7.0.0", description: "Elastic Stack Git branch/tag to use")
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
      agent { label 'master || immutable' }
      steps {
        githubCheckNotify('PENDING')
        deleteDir()
        gitCheckout(basedir: "${BASE_DIR}")
        stash allowEmpty: true, name: 'source', useDefaultExcludes: false
        script{
          currentBuild.displayName = "apm-agent-${params.AGENT_INTEGRATION_TEST} - ${currentBuild.displayName}"
        }
      }
    }
    /**
      launch integration tests.
    */
    stage("Integration Tests"){
      when {
        expression {
          return (params.AGENT_INTEGRATION_TEST != 'All')
        }
      }
      steps {
        deleteDir()
        unstash "source"
        dir("${BASE_DIR}"){
          script {
            def agentName = mapAgentsIDs[params.AGENT_INTEGRATION_TEST]
            def agentApp = mapAgentsApps[params.AGENT_INTEGRATION_TEST]
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
        expression { return params.AGENT_INTEGRATION_TEST == 'All' }
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
        expression { return params.AGENT_INTEGRATION_TEST == 'UI' }
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
            docker.image('node:11').inside() {
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
  }
  post {
    always {
      githubCheckNotify(currentBuild.currentResult == 'SUCCESS' ? 'SUCCESS' : 'FAILURE')
      notifyBuildResult()
    }
  }
}

def wrappingup(){
  dir("${BASE_DIR}"){
    def stepName = mapAgentsIDs[params.AGENT_INTEGRATION_TEST]
    sh("./scripts/docker-get-logs.sh '${stepName}'|| echo 0")
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
