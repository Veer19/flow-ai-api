@echo off
setlocal

set /p CLIENT_ID=Enter your Azure AD App Client ID: 

echo.
echo Creating federated credential for GitHub Actions...
echo Repo: Veer19/flow-ai-api
echo Branch: master
echo.

az ad app federated-credential create ^
  --id %CLIENT_ID% ^
  --parameters "{\"name\":\"github-oidc-master\",\"issuer\":\"https://token.actions.githubusercontent.com\",\"subject\":\"repo:Veer19/flow-ai-api:ref:refs/heads/master\",\"description\":\"GitHub Actions OIDC federation for master branch\",\"audiences\":[\"api://AzureADTokenExchange\"]}"

IF %ERRORLEVEL% NEQ 0 (
  echo.
  echo ❌ An error occurred while creating the federated credential.
) ELSE (
  echo.
  echo ✅ Federated credential successfully created!
)

echo.
pause
