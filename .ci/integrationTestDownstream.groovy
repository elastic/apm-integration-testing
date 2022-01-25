#!/usr/bin/env groovy
@Library('apm@current') _

import co.elastic.matrix.*
import groovy.transform.Field

/**
  This is the parallel tasks generator,
  it is need as field to store the results of the tests.
*/
@Field def integrationTestsGen

pipeline {
  agent { label 'linux && immutable' }
  environment {
    BASE_DIR="src/github.com/elastic/apm-integration-testing"
    REPO="git@github.com:elastic/apm-integration-testing.git"
    NOTIFY_TO = credentials('notify-to')
    JOB_GCS_BUCKET = credentials('gcs-bucket')
    JOB_GIT_CREDENTIALS = "f6c7695a-671e-4f4f-a331-acdce44ff9ba"
    PIPELINE_LOG_LEVEL = 'INFO'
    DISABLE_BUILD_PARALLEL = "${params.DISABLE_BUILD_PARALLEL}"
    ENABLE_ES_DUMP = "true"
    NAME = agentMapping.id(params.INTEGRATION_TEST)
    INTEGRATION_TEST = "${params.INTEGRATION_TEST}"
    ELASTIC_STACK_VERSION = "${ params?.ELASTIC_STACK_VERSION?.trim() ? params.ELASTIC_STACK_VERSION.trim() : stackVersions.edge() }"
    BUILD_OPTS = "${params.BUILD_OPTS}"
  }
  options {
    timeout(time: 3, unit: 'HOURS')
    timestamps()
    ansiColor('xterm')
    disableResume()
    durabilityHint('PERFORMANCE_OPTIMIZED')
  }
  parameters {
    choice(name: 'INTEGRATION_TEST', choices: ['.NET', 'Go', 'Java', 'Node.js', 'PHP', 'Python', 'Ruby', 'RUM', 'UI', 'All'], description: 'Name of the Tests or APM Agent you want to run the integration tests.')
    string(name: 'ELASTIC_STACK_VERSION', defaultValue: "", description: "Elastic Stack Git branch/tag to use")
    string(name: 'INTEGRATION_TESTING_VERSION', defaultValue: "7.16", description: "Integration testing Git branch/tag to use")
    string(name: 'MERGE_TARGET', defaultValue: "7.x.x", description: "Integration testing Git branch/tag where to merge this code")
    string(name: 'BUILD_OPTS', defaultValue: "", description: "Additional build options to passing compose.py")
    string(name: 'UPSTREAM_BUILD', defaultValue: "", description: "upstream build info to show in the description.")
    booleanParam(name: 'DISABLE_BUILD_PARALLEL', defaultValue: true, description: "Disable the build parallel option on compose.py. Disabling it is better for error detection.")
  }
  stages{
    /**
     Checkout the code and stash it, to use it on other stages.
    */
    stage('Checkout'){
      options { skipDefaultCheckout() }
      steps {
        echo "Correct PR"
        sh('git show-ref')
        deleteDir()
        gitCheckout(basedir: "${BASE_DIR}",
          branch: "${params.INTEGRATION_TESTING_VERSION}",
          repo: "${REPO}",
          credentialsId: "${JOB_GIT_CREDENTIALS}",
          mergeTarget: "${params.MERGE_TARGET}",
          reference: "/var/lib/jenkins/apm-integration-testing.git",
          shallow: false
        )
        stash allowEmpty: true, name: 'source', useDefaultExcludes: false
        script {
          def displayName = "apm-agent-${params.INTEGRATION_TEST}"
          def description = "Agent ${params.INTEGRATION_TEST}"
          if (params.INTEGRATION_TEST.equals('All') || params.INTEGRATION_TEST.equals('UI')) {
            displayName = "${params.INTEGRATION_TEST}"
            description = "${params.INTEGRATION_TEST}"
          }
          currentBuild.displayName = "${displayName} - ${currentBuild.displayName}"
          currentBuild.description = "${description} - ${params.UPSTREAM_BUILD}"
        }
      }
    }
    /**
      launch integration tests.
    */
    stage("Integration Tests"){
      when {
        expression {
          return (params.INTEGRATION_TEST != 'All'
            && params.INTEGRATION_TEST != 'UI')
        }
      }
      steps {
        deleteDir()
        unstash "source"
        dir("${BASE_DIR}"){
          script {
            integrationTestsGen = new IntegrationTestingParallelTaskGenerator(
              xKey: agentMapping.agentVar(env.NAME),
              yKey: agentMapping.agentVar('server'),
              xFile: agentMapping.yamlVersionFile(env.NAME),
              yFile: agentMapping.yamlVersionFile('server'),
              exclusionFile: agentMapping.yamlVersionFile(env.NAME),
              tag: env.NAME,
              name: params.INTEGRATION_TEST,
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
        expression { return params.INTEGRATION_TEST == 'All' }
      }
      environment {
        TMPDIR = "${WORKSPACE}"
        REUSE_CONTAINERS = "true"
        PATH = "${WORKSPACE}/${BASE_DIR}/.ci/scripts:${env.PATH}"
      }
      steps {
        withGithubNotify(context: 'All', isBlueOcean: true) {
          deleteDir()
          unstash "source"
          filebeat(output: "docker-all.log", archiveOnlyOnFail: true){
            dir("${BASE_DIR}"){
              retryWithSleep(retries: 3, seconds: 5, backoff: true) {
                sh(label: 'Prepare docker images', script: '.ci/scripts/build-docker-all.sh')
              }
              withOtelEnv() {
                sh(label: 'Run all', script: '.ci/scripts/all.sh')
              }
            }
          }
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
        expression { return params.INTEGRATION_TEST == 'UI' }
      }
      environment {
        TMPDIR = "${WORKSPACE}/${BASE_DIR}"
        HOME = "${WORKSPACE}/${BASE_DIR}"
      }
      steps {
        withGithubNotify(context: 'UI', isBlueOcean: true) {
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
  }
  post {
    cleanup {
      script{
        if(integrationTestsGen?.results){
          writeJSON(file: 'results.json', json: toJSON(integrationTestsGen.results), pretty: 2)
          def mapResults = ["${params.INTEGRATION_TEST}": integrationTestsGen.results]
          def processor = new ResultsProcessor()
          processor.processResults(mapResults)
          archiveArtifacts allowEmptyArchive: true, artifacts: 'results.json,results.html', defaultExcludes: false
        }
        notifyBuildResult(prComment: false)
      }
    }
  }
}

/**
  Parallel task generator for the integration tests.
*/
class IntegrationTestingParallelTaskGenerator extends DefaultParallelTaskGenerator {

  public IntegrationTestingParallelTaskGenerator(Map params){
    super(params)
  }

  /**
    build a clousure that launch an agent or test and execute the corresponding test script,
    then store the results.
  */
  public Closure generateStep(x, y){
    return {
      steps.node('linux && immutable'){
        def env = ["APM_SERVER_BRANCH=${y}",
          "${steps.agentMapping.envVar(tag)}=${x}",
          "REUSE_CONTAINERS=true",
          "ENABLE_ES_DUMP=true",
          "PATH=${steps.env.WORKSPACE}/${steps.env.BASE_DIR}/.ci/scripts:${steps.env.PATH}",
          "TMPDIR=${steps.env.WORKSPACE}"
          ]
        def label = "${tag}-${x}-${y}"
        try{
          saveResult(x, y, 0)
          steps.runScript(label: label, agentType: tag, env: env)
          saveResult(x, y, 1)
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
  def dockerLogs = label.replace(":","_").replace(";","_").replace(" ","").replace("--","-")
  withGithubNotify(context: "${label}", isBlueOcean: true) {
    log(level: 'INFO', text: "${label}")
    deleteDir()
    unstash "source"
    filebeat(output: "docker-${dockerLogs}.log", archiveOnlyOnFail: true){
      sh 'docker ps -a && docker images -a && docker volume ls && docker network ls'
      dir("${BASE_DIR}"){
        withEnv(env){
          withOtelEnv() {
            sh(label: "Testing ${agentType}", script: ".ci/scripts/${agentType}.sh")
          }
          sh 'docker ps -a && docker images -a && docker volume ls && docker network ls'
        }
      }
    }
  }
}

def wrappingup(label){
  dir("${BASE_DIR}"){
    def testResultsFolder = 'tests/results'
    def testResultsPattern = "${testResultsFolder}/*-junit*.xml"
    def labelFolder = normalise(label)
    sh('make stop-env || echo 0')
    sh(label: 'Folder to aggregate test results from stages',
       script: "mkdir -p ${labelFolder}/${testResultsFolder} && cp -rf ${testResultsPattern} ${labelFolder}/${testResultsFolder}")
    archiveArtifacts(
        allowEmptyArchive: true,
        artifacts: "${testResultsFolder}/data-*.json,${testResultsFolder}/packetbeat-*.json,${labelFolder}/${testResultsPattern}",
        defaultExcludes: false)
    junit(testResults: testResultsPattern, allowEmptyResults: true, keepLongStdio: true)
    // Let's generate the debug report ...
    sh(label: 'Generate debug docs', script: '.ci/scripts/generate-debug-docs.sh "downstream" | tee docs.txt')
    archiveArtifacts(artifacts: 'docs.txt')
  }
}

def normalise(label) {
  return label?.replace(';','/').replace('--','_').replace('.','_').replace(' ','_')
}
