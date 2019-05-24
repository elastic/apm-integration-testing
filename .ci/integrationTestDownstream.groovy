#!/usr/bin/env groovy
@Library('apm@current') _

import co.elastic.matrix.*
import groovy.transform.Field

/**
  This is the parallel tasks generator,
  it is need as field to store the results of the tests.
*/
@Field def integrationTestsGen

/**
  YAML files to get agent versions and exclusions.
*/
@Field Map ymlFiles = [
  'dotnet': 'tests/versions/dotnet.yml',
  'go': 'tests/versions/go.yml',
  'java': 'tests/versions/java.yml',
  'nodejs': 'tests/versions/nodejs.yml',
  'python': 'tests/versions/python.yml',
  'ruby': 'tests/versions/ruby.yml',
  'rum': 'tests/versions/rum.yml',
  'server': 'tests/versions/apm_server.yml'
]

/**
  Key which contains the agent versions.
*/
@Field Map agentYamlVar = [
  'dotnet': 'DOTNET_AGENT',
  'go': 'GO_AGENT',
  'java': 'JAVA_AGENT',
  'nodejs': 'NODEJS_AGENT',
  'python': 'PYTHON_AGENT',
  'ruby': 'RUBY_AGENT',
  'rum': 'RUM_AGENT',
  'server': 'APM_SERVER'
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
    REPO="git@github.com:elastic/apm-integration-testing.git"
    NOTIFY_TO = credentials('notify-to')
    JOB_GCS_BUCKET = credentials('gcs-bucket')
    JOB_GIT_CREDENTIALS = "f6c7695a-671e-4f4f-a331-acdce44ff9ba"
    PIPELINE_LOG_LEVEL = 'INFO'
    DISABLE_BUILD_PARALLEL = "${params.DISABLE_BUILD_PARALLEL}"
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
    choice(name: 'agent_integration_test', choices: ['.NET', 'Go', 'Java', 'Node.js', 'Python', 'Ruby', 'RUM', 'UI', 'All'], description: 'Name of the APM Agent you want to run the integration tests.')
    string(name: 'ELASTIC_STACK_VERSION', defaultValue: "7.0.0", description: "Elastic Stack Git branch/tag to use")
    string(name: 'INTEGRATION_TESTING_VERSION', defaultValue: "master", description: "Integration testing Git branch/tag to use")
    string(name: 'BUILD_OPTS', defaultValue: "", description: "Addicional build options to passing compose.py")
    string(name: 'UPSTREAM_BUILD', defaultValue: "", description: "upstream build info to show in the description.")
    booleanParam(name: 'DISABLE_BUILD_PARALLEL', defaultValue: true, description: "Disable the build parallel option on compose.py, disable it is better for error detection.")
  }
  stages{
    /**
     Checkout the code and stash it, to use it on other stages.
    */
    stage('Checkout'){
      options { skipDefaultCheckout() }
      steps {
        deleteDir()
        dir("${BASE_DIR}"){
          checkout([$class: 'GitSCM',
            branches: [[name: "${params.INTEGRATION_TESTING_VERSION}"]],
            doGenerateSubmoduleConfigurations: false,
            extensions: [],
            submoduleCfg: [],
            userRemoteConfigs: [[
              refspec: '+refs/heads/*:refs/remotes/origin/* +refs/pull/*/head:refs/remotes/origin/pr/*',
              url: "${REPO}",
              credentialsId: "${JOB_GIT_CREDENTIALS}"]]
          ])
        }
        stash allowEmpty: true, name: 'source', useDefaultExcludes: false
        script{
          currentBuild.displayName = "apm-agent-${params.agent_integration_test} - ${currentBuild.displayName}"
          currentBuild.description = "Agent ${params.agent_integration_test} - ${params.UPSTREAM_BUILD}"
        }
      }
    }
    /**
      launch integration tests.
    */
    stage("Integration Tests"){
      when {
        expression {
          return (params.agent_integration_test != 'All'
            && params.agent_integration_test != 'UI')
        }
      }
      steps {
        deleteDir()
        unstash "source"
        dir("${BASE_DIR}"){
          script {
            def agentTests = mapAgentsIDs[params.agent_integration_test]
            integrationTestsGen = new IntegrationTestingParallelTaskGenerator(
              xKey: agentYamlVar[agentTests],
              yKey: agentYamlVar['server'],
              xFile: ymlFiles[agentTests],
              yFile: ymlFiles['server'],
              exclusionFile: ymlFiles[agentTests],
              tag: agentTests,
              name: params.agent_integration_test,
              steps: this
              )
            def mapPatallelTasks = integrationTestsGen.generateParallelTests()
            parallel(mapPatallelTasks)
          }
        }
      }
    }
    stage("All") {
      when {
        expression { return params.agent_integration_test == 'All' }
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
          wrappingup('all')
        }
      }
    }
    stage("UI") {
      when {
        expression { return params.agent_integration_test == 'UI' }
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
    }
  }
  post {
    always{
      script{
        if(integrationTestsGen?.results){
          writeJSON(file: 'results.json', json: toJSON(integrationTestsGen.results), pretty: 2)
          def mapResults = ["${params.agent_integration_test}": integrationTestsGen.results]
          def processor = new ResultsProcessor()
          processor.processResults(mapResults)
          archiveArtifacts allowEmptyArchive: true, artifacts: 'results.json,results.html', defaultExcludes: false
        }
      }
    }
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

/**
  Parallel task generator for the integration tests.
*/
class IntegrationTestingParallelTaskGenerator extends DefaultParallelTaskGenerator {
  /**
    Enviroment variable to put the agent version before run tests.
  */
  public Map agentEnvVar = [
    'dotnet': 'APM_AGENT_DOTNET_VERSION',
    'go': 'APM_AGENT_GO_VERSION',
    'java': 'APM_AGENT_JAVA_VERSION',
    'nodejs': 'APM_AGENT_NODEJS_VERSION',
    'python': 'APM_AGENT_PYTHON_VERSION',
    'ruby': 'APM_AGENT_RUBY_VERSION',
    'rum': 'APM_AGENT_RUM_VERSION',
    'server': 'APM_SERVER_BRANCH'
  ]

  public IntegrationTestingParallelTaskGenerator(Map params){
    super(params)
  }

  /**
    build a clousure that launch and agent and execute the corresponding test script,
    then store the results.
  */
  public Closure generateStep(x, y){
    return {
      steps.node('linux && immutable'){
        def env = ["APM_SERVER_BRANCH=${y}",
          "${agentEnvVar[tag]}=${x}",
          "REUSE_CONTAINERS=true"
          ]
        def label = "${tag}-${x}-${y}"
        try{
          steps.runScript(label: label, agentType: tag, env: env)
          saveResult(x, y, 1)
        } catch (e){
          saveResult(x, y, 0)
          error("${label} tests failed : ${e.toString()}\n")
        } finally {
          steps.wrappingup(label)
        }
      }
    }
  }
}

/**
  Execute a test script.

  runScript(tag: "Running Go integration test", agentType: "go", env: [ 'V1': 'value', 'V2':'value'])
*/
def runScript(Map params = [:]){
  def label = params.containsKey('label') ? params.label : params?.agentType
  def agentType = params.agentType
  def env = params.env
  log(level: 'INFO', text: "${label}")
  deleteDir()
  unstash "source"
  dir("${BASE_DIR}"){
    withEnv(env){
      sh """#!/bin/bash
      export TMPDIR="${WORKSPACE}"
      .ci/scripts/${agentType}.sh
      """
    }
  }
}

def wrappingup(label){
  dir("${BASE_DIR}"){
    def stepName = label.replace(";","/")
      .replace("--","_")
      .replace(".","_")
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
