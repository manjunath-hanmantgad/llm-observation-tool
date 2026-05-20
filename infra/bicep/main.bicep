targetScope = 'resourceGroup'

param location string = resourceGroup().location
param appName string = 'llm-observatory'
param environment string = 'dev'
param acrImageTag string = 'latest'

@secure()
param postgresAdminPassword string

var suffix = '${appName}-${environment}'
var acrName = take(replace('${suffix}acr', '-', ''), 50)
var logAnalyticsSharedKey = listKeys(resourceId('Microsoft.OperationalInsights/workspaces', '${suffix}-law'), '2020-08-01').primarySharedKey
var commonEnv = [
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: appInsights.outputs.connectionString
  }
  {
    name: 'LLM_PROVIDER'
    value: 'azure'
  }
  {
    name: 'STORAGE_MODE'
    value: 'postgres'
  }
  {
    name: 'DATABASE_URL'
    value: 'postgresql+psycopg://observatoryadmin:${postgresAdminPassword}@${postgres.outputs.fqdn}:5432/observatory'
  }
]

module acr 'modules/acr.bicep' = {
  name: 'acr'
  params: {
    location: location
    acrName: acrName
  }
}

module appInsights 'modules/appinsights.bicep' = {
  name: 'appinsights'
  params: {
    location: location
    appInsightsName: '${suffix}-ai'
    workspaceName: '${suffix}-law'
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    location: location
    serverName: '${suffix}-pg'
    adminPassword: postgresAdminPassword
  }
}

module acaEnv 'modules/aca-environment.bicep' = {
  name: 'aca-env'
  params: {
    location: location
    environmentName: '${suffix}-env'
    logAnalyticsWorkspaceId: appInsights.outputs.workspaceId
    logAnalyticsSharedKey: logAnalyticsSharedKey
  }
}

module gateway 'modules/aca-app.bicep' = {
  name: 'gateway'
  params: {
    location: location
    appName: '${suffix}-gateway'
    environmentId: acaEnv.outputs.id
    imageName: '${acr.outputs.loginServer}/llm-observatory:${acrImageTag}'
    containerPort: 8001
    command: [
      'sh'
      '-c'
      'alembic upgrade head && uvicorn gateway.gateway:app --host 0.0.0.0 --port 8001'
    ]
    env: commonEnv
  }
}

module dashboard 'modules/aca-app.bicep' = {
  name: 'dashboard'
  params: {
    location: location
    appName: '${suffix}-dashboard'
    environmentId: acaEnv.outputs.id
    imageName: '${acr.outputs.loginServer}/llm-observatory:${acrImageTag}'
    containerPort: 8501
    command: [
      'streamlit'
      'run'
      'dashboard/app.py'
      '--server.address'
      '0.0.0.0'
      '--server.port'
      '8501'
    ]
    env: commonEnv
  }
}

module evalWorker 'modules/aca-app.bicep' = {
  name: 'evaluation-worker'
  params: {
    location: location
    appName: '${suffix}-evaluation-worker'
    environmentId: acaEnv.outputs.id
    imageName: '${acr.outputs.loginServer}/llm-observatory:${acrImageTag}'
    containerPort: 0
    minReplicas: 0
    maxReplicas: 1
    command: [
      'sh'
      '-c'
      'alembic upgrade head && python workers/evaluation_worker.py --limit 100'
    ]
    env: commonEnv
  }
}

module alertWorker 'modules/aca-app.bicep' = {
  name: 'alert-worker'
  params: {
    location: location
    appName: '${suffix}-alert-worker'
    environmentId: acaEnv.outputs.id
    imageName: '${acr.outputs.loginServer}/llm-observatory:${acrImageTag}'
    containerPort: 0
    minReplicas: 0
    maxReplicas: 1
    command: [
      'sh'
      '-c'
      'alembic upgrade head && python workers/alert_worker.py'
    ]
    env: commonEnv
  }
}

module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    location: location
    keyVaultName: '${suffix}-kv'
    managedIdentityPrincipalId: gateway.outputs.principalId
  }
}

output gatewayUrl string = 'https://${gateway.outputs.fqdn}'
output dashboardUrl string = 'https://${dashboard.outputs.fqdn}'
output acrLoginServer string = acr.outputs.loginServer
output keyVaultUri string = keyvault.outputs.uri
output postgresHost string = postgres.outputs.fqdn
output evalWorkerIdentityId string = evalWorker.outputs.identityId
output alertWorkerIdentityId string = alertWorker.outputs.identityId
