#!/usr/bin/env groovy

@Library('apm@current') _

pipeline {
  agent none
  environment {
    BASE_DIR="src/github.com/elastic/apm-integration-testing"
    NOTIFY_TO = credentials('notify-to')
    JOB_GCS_BUCKET = credentials('gcs-bucket')
    JOB_GIT_CREDENTIALS = 'f6c7695a-671e-4f4f-a331-acdce44ff9ba'
    PIPELINE_LOG_LEVEL='INFO'
  }
  triggers {
    cron 'H H(3-4) * * 1-5'
    issueCommentTrigger('(?i).*(?:jenkins\\W+)?run\\W+(?:the\\W+)?tests(?:\\W+please)?.*')
  }
  options {
    timeout(time: 1, unit: 'HOURS')
    buildDiscarder(logRotator(numToKeepStr: '100', artifactNumToKeepStr: '100', daysToKeepStr: '30'))
    timestamps()
    ansiColor('xterm')
    disableResume()
    durabilityHint('PERFORMANCE_OPTIMIZED')
    rateLimitBuilds(throttle: [count: 60, durationName: 'hour', userBoost: true])
    quietPeriod(10)
  }
  parameters {
    string(name: 'ELASTIC_STACK_VERSION', defaultValue: "7.0.0", description: "Elastic Stack Git branch/tag to use")
    string(name: 'BUILD_OPTS', defaultValue: "", description: "Additional build options to passing compose.py")
    string(name: 'GITHUB_CHECK_NAME', defaultValue: '', description: 'Name of the GitHub check to be updated. Only if this build is triggered from another parent stream.')
    string(name: 'GITHUB_CHECK_REPO', defaultValue: '', description: 'Name of the GitHub repo to be updated. Only if this build is triggered from another parent stream.')
    string(name: 'GITHUB_CHECK_SHA1', defaultValue: '', description: 'Name of the GitHub repo to be updated. Only if this build is triggered from another parent stream.')
    booleanParam(name: 'Run_As_Master_Branch', defaultValue: false, description: 'Allow to run any steps on a PR, some steps normally only run on master branch.')
  }
  stages{
    /**
     Checkout the code and stash it, to use it on other stages.
    */
    stage('Checkout'){
      agent { label 'master || immutable' }
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
          https://issues.jenkins-ci.org/browse/JENKINS-56562
        */
        script {
          def downstreamJobs = [:]
          if(env?.CHANGE_ID != null && !params.Run_As_Master_Branch){
            downstreamJobs = ['All': {runJob('All')}]
          } else {
            downstreamJobs = [
            'All': {runJob('All')},
            '.NET': {runJob('.NET')},
            'Go': {runJob('Go')},
            'Java': {runJob('Java')},
            'Node.js': {runJob('Node.js')},
            'Python': {runJob('Python')},
            'Ruby': {runJob('Ruby')},
            'RUM': {runJob('RUM')},
            'UI': {runJob('UI')}
            ]
          }
          parallel(downstreamJobs)
        }
      }
    }
  }
  post {
    always {
      githubCheckNotify()
      notifyBuildResult()
    }
  }
}

/**
 Notify the GitHub check of the parent stream
**/
def githubCheckNotify() {
  if (params.GITHUB_CHECK_NAME?.trim && params.GITHUB_CHECK_REPO?.trim() && params.GITHUB_CHECK_SHA1?.trim() ) {
    String statusSuffix =
    String status =
    githubNotify context: params.GITHUB_CHECK_NAME,
                 description: "${params.GITHUB_CHECK_NAME} ${currentBuild.currentResult == 'FAILURE' ? 'failed' : 'passed'}",
                 status: "${(currentBuild.currentResult == 'SUCCESS') ?: 'FAILED'}",
                 targetUrl: "${env.RUN_DISPLAY_URL}",
                 sha: params.GITHUB_CHECK_SHA1, account: 'elastic', repo: params.GITHUB_CHECK_REPO, credentialsId: env.JOB_GIT_CREDENTIALS
  }
}

def runJob(agentName, buildOpts = ''){
  def job = build(job: 'apm-integration-test-axis-pipeline',
    parameters: [
    string(name: 'AGENT_INTEGRATION_TEST', value: agentName),
    string(name: 'ELASTIC_STACK_VERSION', value: params.ELASTIC_STACK_VERSION),
    string(name: 'INTEGRATION_TESTING_VERSION', value: env.GIT_BASE_COMMIT),
    string(name: 'BUILD_OPTS', value: "${params.BUILD_OPTS} ${buildOpts}"),
    string(name: 'UPSTREAM_BUILD', value: currentBuild.fullDisplayName),
    booleanParam(name: 'DISABLE_BUILD_PARALLEL', value: '')],
    propagate: true,
    quietPeriod: 10,
    wait: true)
}
