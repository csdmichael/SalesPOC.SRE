using './main.bicep'

param agentName = 'sre-poc-ai-my'
param location = 'eastus2'
param containerImage = 'ghcr.io/${readEnvironmentVariable('GITHUB_REPOSITORY', 'local/sre-poc-ai-my')}:latest'
