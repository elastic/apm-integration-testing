#!/usr/bin/env groovy
// PR run all.sh
// merge on master run all.sh
// periodic run all.sh version_nodejs.sh versions_python.sh versions_ruby.sh

import groovy.transform.Field

@Field def results = [:]

@Field Map ymlFiles = [
  'go': 'tests/versions/go.yml',
  'java': 'tests/versions/java.yml',
  'nodejs': 'tests/versions/nodejs.yml',
  'python': 'tests/versions/python.yml',
  'ruby': 'tests/versions/ruby.yml',
  'server': 'tests/versions/apm_server.yml'
]

@Field Map agentEnvVar = [
  'go': 'APM_AGENT_GO_PKG',
  'java': 'APM_AGENT_JAVA_PKG',
  'nodejs': 'APM_AGENT_NODEJS_PKG',
  'python': 'APM_AGENT_PYTHON_PKG',
  'ruby': 'APM_AGENT_RUBY_PKG',
  'server': 'APM_SERVER_BRANCH'
]

@Field Map agentYamlVar = [
  'go': 'GO_AGENT',
  'java': 'JAVA_AGENT',
  'nodejs': 'NODEJS_AGENT',
  'python': 'PYTHON_AGENT',
  'ruby': 'RUBY_AGENT',
  'server': 'APM_SERVER'
]

@Field Map displayName = [
  'go': 'Go',
  'java': 'Java',
  'nodejs': 'Node.js',
  'python': 'Python',
  'ruby': 'Ruby',
  'server': 'APM Server'
]

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
  parameters {
    string(name: 'ELASTIC_STACK_VERSION', defaultValue: "6.5", description: "Elastic Stack Git branch/tag to use")
    string(name: 'BUILD_OPTS', defaultValue: "", description: "Addicional build options to passing compose.py")
    booleanParam(name: 'DISABLE_BUILD_PARALLEL', defaultValue: true, description: "Disable the build parallel option on compose.py, disable it is better for error detection.")
    booleanParam(name: 'all_Test', defaultValue: true, description: 'Enable Test')
    booleanParam(name: 'agents_Test', defaultValue: true, description: 'Enable Test')
  }
  stages{
    /**
     Checkout the code and stash it, to use it on other stages.
    */
    stage('Checkout'){
      agent { label 'linux && immutable' }
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
    stage("Integration Tests"){
      failFast false
      parallel {
        stage("All") { 
          agent { label 'linux && immutable' }
          options { skipDefaultCheckout() }
          when { 
            beforeAgent true
            expression { return params.all_Test }
          }
          steps {
            runScript(source: "source", tag: "All", agentType: "all")
          } 
        }
        stage("Agents") { 
          agent { label 'linux && immutable' }
          options { skipDefaultCheckout() }
          when { 
            beforeAgent true
            expression { return params.agents_Test }
          }
          steps {
            deleteDir()
            unstash "source"
            dir("${BASE_DIR}"){
              script {
                def matrix = [:]
                matrix.putAll(generateParallelTests('go'))
                matrix.putAll(generateParallelTests('java'))
                matrix.putAll(generateParallelTests('python'))
                matrix.putAll(generateParallelTests('nodejs'))
                matrix.putAll(generateParallelTests('ruby'))
                parallel(matrix)
              }
            }
          } 
        }
      }
    }
  }
  post {
    always{
      writeJSON(file: 'results.json', json: toJSON(results), pretty: 2)
      processResults(results)
      archiveArtifacts allowEmptyArchive: true, artifacts: 'results.json,results.html', defaultExcludes: false
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

def getXVersions(file, xKey){
  return readYaml(file: file)[xKey]
}

def getYVersions(file, yKey){
  return readYaml(file: file)[yKey]
}

def getExcludeVersions(file, xKey, yKey){
  def ret = []
  readYaml(file: file)['exclude'].each{ v ->
    def x = v[xKey]
    def y = v[yKey]
    String key = "${x}#${y}"
    log(level: "DEBUG", text: "Exclude : ${key}")
    ret.add(key)
  }
  return ret
}

def saveResult(x, y, results, value){
  if(results.data[x] == null){
    results.data[x] = [:]
    results.data[x]["Agent ${results.displayname}"] = x
  }
  results.data[x][y] = value
}

def buildColumn(x, yItems, excludes){
  def column = [:]
  yItems.each{ y ->
    String key = "${x}#${y}"
    if(!excludes.contains(key)){
      column[key] = [X: x, Y: y]
    }
  }
  return column
}

def generateParallelTests(tag) {
  def xKey = agentYamlVar[tag]
  def yKey = agentYamlVar['server']
  def xFile = ymlFiles[tag]
  def yFile = ymlFiles['server']
  def exclusionFile = ymlFiles[tag]
  results[tag] = [:]
  results[tag].data = [:]
  results[tag].tag = tag
  results[tag].displayname = displayName[tag]
  results[tag].x = getXVersions(xFile, xKey)
  results[tag].y = getYVersions(yFile, yKey)
  results[tag].excludes = getExcludeVersions(exclusionFile, xKey, yKey)
  return buildMatrix(results[tag]);
}

def buildMatrix(data){
  def parallelSteps = [:]
  data.x.each{ x ->
    def column = buildColumn(x, data.y, data.excludes)
    log(level: "DEBUG", text: "Column : ${column.toString()}")
    def stagesMap = generateParallelSteps(data.tag, column)
    log(level: "DEBUG", text: "stagesMap : ${stagesMap.toString()}")
    parallelSteps.putAll(stagesMap)
  }
  log(level: "DEBUG", text: "parallelStages : ${parallelSteps.toString()}")
  return parallelSteps
}

/**
  build a map of clousures to be used as parallel steps.
*/
def generateParallelSteps(tag, column){
  def parallelStep = [:]
  column.each{ key, value ->
    def keyGrp = "${tag}-${value.X}-${value.Y}"
    parallelStep[keyGrp] = testStep(tag, value.X, value.Y)
  }
  return parallelStep
}

/**
  build a clousure that launch and agent and execute the corresponding test script,
  then store the results.
*/
def testStep(tag, x, y){
  return {
    node('linux && immutable'){
      try {
        withEnv([
          "APM_SERVER_BRANCH=${y}",
          "${agentEnvVar[tag]}=${x}"]){
          runScript(baseDir: "${BASE_DIR}", source: 'source', tag: "${tag}-${x}-${y}", agentType: tag)
          saveResult(x, y, results[tag], 1)
        }
      } catch(e){
        saveResult(x, y, results[tag], 0)
        error("Some ${tag} tests failed")
      } finally {
        junit(
          allowEmptyResults: true, 
          keepLongStdio: true, 
          testResults: "${BASE_DIR}/tests/results/*-junit*.xml")
      }
    }
  }
}

/**
  Execute a test script.
  
  runScript(baseDir: 'src', source: 'source', tag: "Running Go integration test", agentType: "go")
*/

def runScript(Map params = [:]){
  def tag = params.containsKey('tag') ? params.tag : params?.agentType
  def agentType = params?.agentType
  def source = params.containsKey('source') ? params.source : 'source'
  def baseDir = params.containsKey('baseDir') ? params.baseDir : 'src/github.com/elastic/apm-integration-testing'

  if(agentType == null){
    error "runScript: no valid agentType"
  }

  if(source == null){
    error "runScript: no valid source to unstash"
  }

  log(level: 'INFO', text: "${tag}")
  deleteDir()
  unstash "${source}"
  dir("${baseDir}"){
    def pytestIni = "[pytest]\n"
    pytestIni += "junit_suite_name = ${tag}\n"
    pytestIni += "addopts = --color=yes -ra\n"
    writeFile(file: "pytest.ini", text: pytestIni, encoding: "UTF-8")

    sh """#!/bin/bash
    echo "${tag}"
    export TMPDIR="${WORKSPACE}"
    chmod ugo+rx ./scripts/ci/*.sh
    ./scripts/ci/${agentType}.sh
    """
  }
}


def processResults(results){
  sh 'curl -sLO https://code.jquery.com/jquery-3.3.1.slim.min.js'
  sh 'curl -sLO https://cdn.jsdelivr.net/npm/htmlson.js@1.0.4/src/htmlson.js'
  def jquery = readFile(file: 'jquery-3.3.1.slim.min.js')
  def htmlson = readFile(file: 'htmlson.js')
  String html = """<html>
  <head>
    <title>Integration Test Results</title>
  </head>
  <script type="text/javascript">${jquery}</script>
  <script type="text/javascript">${htmlson}</script>
  <style>
    table {
      font-family: Arial, Helvetica, sans-serif;
      border: 1px solid #000000;
      background-color: #EEEEEE;
      width: 50em;
      text-align: center;
      border-collapse: collapse;
      margin: 30px 20px;
    }
    table td, table th {
      border: 1px solid #AAAAAA;
      padding: 3px 2px;
    }
    table tbody td {
      font-size: 13px;
    }
    table tr:nth-child(even) {
      background: #D0E4F5;
    }
    table thead {
      background: #1C6EA4;
      background: -moz-linear-gradient(top, #5592bb 0%, #327cad 66%, #1C6EA4 100%);
      background: -webkit-linear-gradient(top, #5592bb 0%, #327cad 66%, #1C6EA4 100%);
      background: linear-gradient(to bottom, #5592bb 0%, #327cad 66%, #1C6EA4 100%);
      border-bottom: 2px solid #444444;
    }
    table thead th {
      font-size: 15px;
      font-weight: bold;
      color: #FFFFFF;
      text-align: center;
      border-left: 2px solid #D0E4F5;
    }
    table thead th:first-child {
      border-left: none;
    }

    table tfoot td {
      font-size: 14px;
    }
    table tfoot .links {
      text-align: right;
    }
    table tfoot .links a{
      display: inline-block;
      background: #1C6EA4;
      color: #FFFFFF;
      padding: 2px 8px;
      border-radius: 5px;
    }
    
    .error {
      color: red;
    }
    
    .ok {
      color: green;
    }
  </style>
  <body>
  """
  
  results.each{ k, v ->
    def records = []
    v.data.each{ dk, dv ->
      def row = [:]
      v.y.each{ vy ->
        row.put(vy, "N/A")
      }
      row.putAll(dv)
      records.add(row)
    }
    
    String jsonRecords = toJSON(records).toString()
    html += """
    <h2>Agent ${v.displayname}</h2>
    <table class="${k}Agent"></table>
    <script type="text/javascript">
      let ${k}Data = ${jsonRecords};
      let ${k}Table = \$('.${k}Agent').htmlson({data: ${k}Data});
    </script>
    """
  }
  
  html += '''
  <script type="text/javascript">
    $('td').each(function(){
      if(this.textContent === "1"){
        $( this ).replaceWith("<td class='ok'>OK</td>");
      } else if(this.textContent === "0") {
        $( this ).replaceWith("<td class='error'>ERROR</td>");
      }
    });
  </script>
  </body>
  </html>
  '''
  writeFile(file: 'results.html', text: html)
}

