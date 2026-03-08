using './main.bicep'

param agentName = 'sre-ai-my'
param location = 'eastus2'
param containerImage = 'ghcr.io/${readEnvironmentVariable('GITHUB_REPOSITORY', 'local/sre-ai-my')}:latest'
