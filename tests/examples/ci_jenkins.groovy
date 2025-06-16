// Jenkins Pipeline Configuration for OneFileLLM
// Save as Jenkinsfile in repository root

pipeline {
    agent any
    
    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }
    
    environment {
        PYTHON_VERSION = '3.11'
    }
    
    stages {
        stage('Setup') {
            steps {
                echo 'Setting up Python environment...'
                sh '''
                    python${PYTHON_VERSION} -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install -r requirements-test.txt
                '''
            }
        }
        
        stage('Lint') {
            steps {
                sh '''
                    . venv/bin/activate
                    pip install flake8
                    flake8 onefilellm.py utils.py --max-line-length=120
                '''
            }
        }
        
        stage('Unit Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    python tests/run_all_tests.py --framework unittest --output-format junit > unittest-results.xml
                '''
            }
            post {
                always {
                    junit 'unittest-results.xml'
                }
            }
        }
        
        stage('Recorded Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    python tests/run_all_tests.py --framework pytest --output-format junit > pytest-results.xml
                '''
            }
            post {
                always {
                    junit 'pytest-results.xml'
                }
            }
        }
        
        stage('Integration Tests') {
            when {
                branch 'main'
            }
            steps {
                withCredentials([string(credentialsId: 'github-token', variable: 'GITHUB_TOKEN')]) {
                    sh '''
                        . venv/bin/activate
                        python tests/run_all_tests.py --integration --output-format junit > integration-results.xml
                    '''
                }
            }
            post {
                always {
                    junit 'integration-results.xml'
                }
            }
        }
        
        stage('Coverage Report') {
            steps {
                sh '''
                    . venv/bin/activate
                    coverage run tests/run_all_tests.py
                    coverage xml
                    coverage html
                '''
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'htmlcov',
                    reportFiles: 'index.html',
                    reportName: 'Coverage Report'
                ])
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        success {
            echo 'All tests passed!'
        }
        failure {
            emailext (
                subject: "Build Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "Build failed. Check console output at ${env.BUILD_URL}",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}