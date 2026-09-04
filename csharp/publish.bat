@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM Publish local (devs). Nao faz parte do CD / GitHub Release.
REM Uso:
REM   publish.bat              → fdd + scd + r2r
REM   publish.bat fdd|scd|r2r  → um perfil

where dotnet >nul 2>&1
if errorlevel 1 (
  echo .NET SDK nao encontrado. Instale o .NET 8 SDK.
  exit /b 1
)

set "PROJ=%~dp0SwiftSend\SwiftSend.csproj"
set "ONLY=%~1"

if /i "%ONLY%"=="fdd" goto :fdd
if /i "%ONLY%"=="scd" goto :scd
if /i "%ONLY%"=="r2r" goto :r2r
if not "%ONLY%"=="" (
  echo Perfil invalido: %ONLY%
  echo Use: publish.bat [fdd^|scd^|r2r]
  exit /b 1
)

call :fdd || exit /b 1
call :scd || exit /b 1
call :r2r || exit /b 1
goto :done

:fdd
echo === Publish Framework-Dependent → csharp\dist\fdd ===
dotnet publish "%PROJ%" -c Release -p:PublishProfile=FrameworkDependent --nologo
if errorlevel 1 exit /b 1
call :verify "dist\fdd"
exit /b %ERRORLEVEL%

:scd
echo === Publish Self-Contained → csharp\dist\scd ===
dotnet publish "%PROJ%" -c Release -p:PublishProfile=SelfContained --nologo
if errorlevel 1 exit /b 1
call :verify "dist\scd"
exit /b %ERRORLEVEL%

:r2r
echo === Publish ReadyToRun → csharp\dist\r2r ===
dotnet publish "%PROJ%" -c Release -p:PublishProfile=ReadyToRun --nologo
if errorlevel 1 exit /b 1
call :verify "dist\r2r"
exit /b %ERRORLEVEL%

:verify
set "OUT=%~dp0%~1"
if not exist "%OUT%\shared\templates\dashboard.html" (
  echo ERRO: UI shared nao foi copiada para %OUT%
  exit /b 1
)
if not exist "%OUT%\SwiftSend.exe" (
  echo ERRO: SwiftSend.exe nao encontrado em %OUT%
  exit /b 1
)
echo OK: %OUT%
exit /b 0

:done
echo.
echo SUCESSO. Saidas em csharp\dist\fdd, scd e r2r.
echo Builds C# sao apenas para desenvolvimento local — releases usam o instalador Python.
exit /b 0
