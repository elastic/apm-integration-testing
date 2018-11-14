#!/usr/bin/env groovy

library identifier: 'apm@master',
changelog: false,
retriever: modernSCM(
  [$class: 'GitSCMSource', 
  credentialsId: 'f94e9298-83ae-417e-ba91-85c279771570', 
  id: '37cf2c00-2cc7-482e-8c62-7bbffef475e2', 
  remote: 'git@github.com:elastic/apm-pipeline-library.git'])

pipeline {
  agent { label 'linux && immutable' }
  environment {
    HOME = "${env.HUDSON_HOME}"
    BASE_DIR="src/github.com/elastic/apm-integration-testing"
    JOB_GIT_CREDENTIALS = "f6c7695a-671e-4f4f-a331-acdce44ff9ba"
  }
   
  options {
    timeout(time: 1, unit: 'HOURS') 
    buildDiscarder(logRotator(numToKeepStr: '100', artifactNumToKeepStr: '100', daysToKeepStr: '30'))
    timestamps()
    //see https://issues.jenkins-ci.org/browse/JENKINS-11752, https://issues.jenkins-ci.org/browse/JENKINS-39536, https://issues.jenkins-ci.org/browse/JENKINS-54133 and jenkinsci/ansicolor-plugin#132
    //ansiColor('xterm')
    disableResume()
    durabilityHint('PERFORMANCE_OPTIMIZED')
  }
  parameters {
    string(name: 'branch_specifier', defaultValue: "", description: "the Git branch specifier to build (branchName, tagName, commitId, etc.)")
    string(name: 'ELASTIC_STACK_VERSION', defaultValue: "6.4", description: "Elastic Stack Git branch/tag to use")
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
    stage('Checkout'){
      agent { label 'master || linux' }
      steps {
        withEnvWrapper() {
          dir("${BASE_DIR}"){
            script{
              if(!env?.branch_specifier){
                echo "Checkout SCM"
                checkout scm
              } else {
                echo "Checkout ${branch_specifier}"
                checkout([$class: 'GitSCM', branches: [[name: "${branch_specifier}"]], 
                  doGenerateSubmoduleConfigurations: false, 
                  extensions: [], 
                  submoduleCfg: [], 
                  userRemoteConfigs: [[credentialsId: "${JOB_GIT_CREDENTIALS}", 
                  url: "${GIT_URL}"]]])
              }
              env.JOB_GIT_COMMIT = getGitCommitSha()
              env.JOB_GIT_URL = "${GIT_URL}"
              
              github_enterprise_constructor()
              
              on_change{
                echo "build cause a change (commit or PR)"
              }
              
              on_commit {
                echo "build cause a commit"
              }
              
              on_merge {
                echo "build cause a merge"
              }
              
              on_pull_request {
                echo "build cause PR"
              }
            }
          }
          stash allowEmpty: true, name: 'source'
          script {
            if(env.BUILD_DESCRIPTION){
              //currentBuild.displayName = "${currentBuild.displayName} ${BUILD_DESCRIPTION}"
              currentBuild.description = "${BUILD_DESCRIPTION}"
            }
          }
        }
      }
    }

    stage("Integration Tests"){
      environment {
        STAGE_STACK = "ES:${env.ELASTIC_STACK_VERSION}-APM:${env.APM_SERVER_BRANCH}"
        STAGE_ALL = "All-${env.STAGE_STACK}"
        STAGE_GO = "Go ${env.APM_AGENT_GO_PKG}-${env.STAGE_STACK}"
        STAGE_JAVA = "Java ${env.APM_AGENT_JAVA_PKG}-${env.STAGE_STACK}"
        STAGE_KIBANA = "Kibana-${env.STAGE_STACK}"
        STAGE_NODEJS = "Node.js ${env.APM_AGENT_NODEJS_PKG}-${env.STAGE_STACK}"
        STAGE_PYTHON = "Python ${env.APM_AGENT_PYTHON_PKG}-${env.STAGE_STACK}"
        STAGE_RUBY = "Ruby ${env.APM_AGENT_RUBY_PKG}-${env.STAGE_STACK}"
        STAGE_SERVER = "Server-${env.STAGE_STACK}"
      }
      failFast false
      parallel {
        stage("All") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            environment name: 'all_Test', value: 'true' 
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_ALL}", agentType: "all")
          } 
        }
        stage("Go") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            environment name: 'go_Test', value: 'true' 
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_GO}", agentType: "go")
          } 
        }
        stage("Java") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            environment name: 'java_Test', value: 'true' 
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_JAVA}", agentType: "java")
          }  
        }
        stage("Kibana") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            environment name: 'kibana_Test', value: 'true' 
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_KIBANA}", agentType: "kibana")
          }
        }
        stage("Node.js") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            environment name: 'nodejs_Test', value: 'true' 
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_NODEJS}", agentType: "nodejs")
          }
        }
        stage("Python") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            environment name: 'python_Test', value: 'true' 
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_PYTHON}", agentType: "python")
          }
        }
        stage("Ruby") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            environment name: 'ruby_Test', value: 'true' 
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_RUBY}", agentType: "ruby")
          }
        }
        stage("Server") { 
          agent { label 'linux && immutable' }
          when { 
            beforeAgent true
            environment name: 'server_Test', value: 'true' 
          }
          steps {
            stepIntegrationTest(source: "source", tag: "${STAGE_SERVER}", agentType: "server")
          }
        }
      }
    }
  }
}