#!/usr/bin/env groovy
@Library('apm@current') _

pipeline {
  agent { label 'linux && immutable' }
  environment {
    BASE_DIR="src/github.com/elastic/apm-integration-testing"
    NOTIFY_TO = credentials('notify-to')
    JOB_GCS_BUCKET = credentials('gcs-bucket')
    JOB_GIT_CREDENTIALS = '2a9602aa-ab9f-4e52-baf3-b71ca88469c7-UserAndToken'
    PIPELINE_LOG_LEVEL = 'INFO'
    REUSE_CONTAINERS = "true"
    NAME = agentMapping.id(params.AGENT_INTEGRATION_TEST)
    AGENT_INTEGRATION_TEST = "${params.AGENT_INTEGRATION_TEST}"
    ELASTIC_STACK_VERSION = "${params.ELASTIC_STACK_VERSION}"
    BUILD_OPTS = "${params.BUILD_OPTS}"
    DETAILS_ARTIFACT = 'docs.txt'
    DETAILS_ARTIFACT_URL = "${env.BUILD_URL}artifact/${env.DETAILS_ARTIFACT}"
  }
  options {
    timeout(time: 1, unit: 'HOURS')
    timestamps()
    ansiColor('xterm')
    disableResume()
    durabilityHint('PERFORMANCE_OPTIMIZED')
    rateLimitBuilds(throttle: [count: 60, durationName: 'hour', userBoost: true])
  }
  parameters {
    choice(name: 'AGENT_INTEGRATION_TEST', choices: ['.NET', 'Go', 'Java', 'Node.js', 'Python', 'Ruby', 'RUM', 'UI', 'All', 'Opbeans'], description: 'Name of the APM Agent you want to run the integration tests.')
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
      options { skipDefaultCheckout() }
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
    stage('Integration Tests'){
      options { skipDefaultCheckout() }
      environment {
        TMPDIR = "${WORKSPACE}"
        ENABLE_ES_DUMP = "true"
        PATH = "${WORKSPACE}/${BASE_DIR}/.ci/scripts:${env.PATH}"
        APP = agentMapping.app(params.AGENT_INTEGRATION_TEST)
        // TODO: wait for changes in the library
        // OPBEANS_APP = agentMapping.opbeansApp(params.AGENT_INTEGRATION_TEST)
        OPBEANS_APP = "${env.NAME}"
      }
      when {
        expression {
          return (params.AGENT_INTEGRATION_TEST != 'All' &&
                  params.AGENT_INTEGRATION_TEST != 'Opbeans')
        }
      }
      parallel {
        stage('Agent app') {
          steps {
            deleteDir()
            unstash "source"
            dir("${BASE_DIR}"){
              sh(label: "Testing ${NAME} ${APP}", script: ".ci/scripts/agent.sh ${NAME} ${APP}")
            }
          }
          post {
            always {
              wrappingup()
            }
          }
        }
        stage('Opbeans app') {
          agent { label 'linux && immutable' }
          options { skipDefaultCheckout() }
          when {
            expression { return (params.AGENT_INTEGRATION_TEST != 'RUM') }
            beforeAgent true
          }
          steps {
            deleteDir()
            unstash "source"
            dir("${BASE_DIR}"){
              sh(label: "Testing ${NAME} ${OPBEANS_APP}", script: ".ci/scripts/opbeans-app.sh ${NAME} ${APP} ${OPBEANS_APP}")
            }
          }
          post {
            always {
              wrappingup(isJunit: false)
            }
          }
        }
        stage('Opbeans RUM app') {
          agent { label 'linux && immutable' }
          options { skipDefaultCheckout() }
          when {
            expression { return (params.AGENT_INTEGRATION_TEST == 'RUM') }
            beforeAgent true
          }
          steps {
            deleteDir()
            unstash "source"
            dir('opbeans-frontend') {
              git url: 'https://github.com/elastic/opbeans-frontend.git'
              sh script: ".ci/bump-version.sh ${env.BUILD_OPTS.replaceAll('--rum-agent-branch ', '')} false", label: 'Bump version'
              sh script: 'make build', label: 'Build docker image with the new rum agent'
            }
            dir("${BASE_DIR}"){
              sh(label: 'Testing RUM', script: '.ci/scripts/opbeans-rum.sh')
            }
          }
          post {
            always {
              wrappingup(isJunit: false)
            }
          }
        }
      }
    }
    stage("All") {
      when {
        expression { return params.AGENT_INTEGRATION_TEST == 'All' }
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
        expression { return params.AGENT_INTEGRATION_TEST == 'Opbeans' }
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

def wrappingup(Map params = [:]){
  def isJunit = params.containsKey('isJunit') ? params.get('isJunit') : true
  dir("${BASE_DIR}"){
    sh("./scripts/docker-get-logs.sh '${env.NAME}'|| echo 0")
    sh('make stop-env || echo 0')
    archiveArtifacts(
        allowEmptyArchive: true,
        artifacts: 'docker-info/**,**/tests/results/data-*.json,,**/tests/results/packetbeat-*.json',
        defaultExcludes: false)
    if (isJunit) {
      junit(allowEmptyResults: true, keepLongStdio: true, testResults: "**/tests/results/*-junit*.xml")
    }
    // Let's generate the debug report ...
    sh(label: 'Generate debug docs', script: ".ci/scripts/generate-debug-docs.sh | tee ${env.DETAILS_ARTIFACT}")
    archiveArtifacts(artifacts: "${env.DETAILS_ARTIFACT}")
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
