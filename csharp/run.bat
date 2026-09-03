@echo off
setlocal
cd /d "%~dp0"

where dotnet >nul 2>&1
if errorlevel 1 (
  echo .NET SDK nao encontrado. Instale o .NET 8 SDK.
  exit /b 1
)

dotnet build "%~dp0SwiftSend\SwiftSend.csproj" -c Release --nologo -v q
if errorlevel 1 exit /b 1

start "" "%~dp0SwiftSend\bin\Release\net8.0-windows\SwiftSend.exe"
