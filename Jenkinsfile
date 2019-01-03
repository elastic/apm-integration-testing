#!/usr/bin/env groovy

pipeline {
  agent none
  environment {
    BASE_DIR="src/github.com/elastic/apm-integration-testing"
    NOTIFY_TO = credentials('notify-to')
    JOB_GCS_BUCKET = credentials('gcs-bucket')
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
    string(name: 'APM_SERVER_BRANCH', defaultValue: "master", description: "APM Server Git branch/tag to use")
    string(name: 'APM_AGENT_NODEJS_PKG', defaultValue: "release;latest", description: "APM Agent NodeJS package to use, it can be a release version (release;VERSION) or build from a github branch (github;BRANCH)")
    string(name: 'APM_AGENT_PYTHON_PKG', defaultValue: "release;latest", description: "APM Agent Python package to use, it can be a release version (release;VERSION) or build from a github branch (github;RANCH)")
    string(name: 'APM_AGENT_RUBY_PKG', defaultValue: "release;latest", description: "APM Agent Ruby package to use, it can be a release version (release;VERSION) or build from a github branch (github;RANCH)")
    string(name: 'APM_AGENT_JAVA_PKG', defaultValue: "master", description: "APM Agent Java package to use, it is build from a github branch (RANCH)")
    string(name: 'APM_AGENT_GO_PKG', defaultValue: "master", description: "APM Agent Go package to use, it is build from a github branch (RANCH)")
    string(name: 'BUILD_OPTS', defaultValue: "", description: "Addicional build options to passing compose.py")
    string(name: 'BUILD_DESCRIPTION', defaultValue: "", description: "Text to named the build in the queue")
    booleanParam(name: 'DISABLE_BUILD_PARALLEL', defaultValue: true, description: "Disable the build parallel option on compose.py, disable it is better for error detection.")
    booleanParam(name: 'all_Test', defaultValue: false, description: 'Enable Test')
    booleanParam(name: 'go_Test', defaultValue: false, description: 'Enable Test')
    booleanParam(name: 'java_Test', defaultValue: false, description: 'Enable Test')
    booleanParam(name: 'kibana_Test', defaultValue: false, description: 'Enable Test')
    booleanParam(name: 'nodejs_Test', defaultValue: false, description: 'Enable Test')
    booleanParam(name: 'python_Test', defaultValue: false, description: 'Enable Test')
    booleanParam(name: 'ruby_Test', defaultValue: false, description: 'Enable Test')
    booleanParam(name: 'server_Test', defaultValue: false, description: 'Enable Test')
  }
  stages{
    /**
     Checkout the code and stash it, to use it on other stages.
    */
    stage('Checkout'){
      agent { label 'linux && immutable' }
      steps {
        deleteDir()
        gitCheckout(basedir: "${BASE_DIR}")
        stash allowEmpty: true, name: 'source', useDefaultExcludes: false
        script {
          if(env.BUILD_DESCRIPTION){
            currentBuild.description = "${BUILD_DESCRIPTION}"
          }
        }
      }
    }
    /**
      launch integration tests.
    */
    stage("Integration Tests"){
      environment {
        STAGE_STACK = "ES:${params.ELASTIC_STACK_VERSION}-APM:${params.APM_SERVER_BRANCH}"
        STAGE_ALL = "All-${env.STAGE_STACK}"
        STAGE_GO = "Go ${params.APM_AGENT_GO_PKG}-${env.STAGE_STACK}"
        STAGE_JAVA = "Java ${params.APM_AGENT_JAVA_PKG}-${env.STAGE_STACK}"
        STAGE_KIBANA = "Kibana-${env.STAGE_STACK}"
        STAGE_NODEJS = "Node.js ${params.APM_AGENT_NODEJS_PKG}-${env.STAGE_STACK}"
        STAGE_PYTHON = "Python ${params.APM_AGENT_PYTHON_PKG}-${env.STAGE_STACK}"
        STAGE_RUBY = "Ruby ${params.APM_AGENT_RUBY_PKG}-${env.STAGE_STACK}"
        STAGE_SERVER = "Server-${env.STAGE_STACK}"
      }
      failFast false
      parallel {
        stage("All") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            expression { return params.all_Test }
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_ALL}", agentType: "all")
          } 
        }
        stage("Go") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            expression { return params.go_Test }
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_GO}", agentType: "go")
          } 
        }
        stage("Java") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            expression { return params.java_Test }
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_JAVA}", agentType: "java")
          }  
        }
        stage("Kibana") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            expression { return params.kibana_Test }
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_KIBANA}", agentType: "kibana")
          }
        }
        stage("Node.js") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            expression { return params.nodejs_Test }
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_NODEJS}", agentType: "nodejs")
          }
        }
        stage("Python") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            expression { return params.python_Test }
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_PYTHON}", agentType: "python")
          }
        }
        stage("Ruby") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            expression { return params.ruby_Test }
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_RUBY}", agentType: "ruby")
          }
        }
        stage("Server") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            expression { return params.server_Test }
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_SERVER}", agentType: "server")
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