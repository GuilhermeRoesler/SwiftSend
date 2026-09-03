; SwiftSend — instalador Windows (binário PyInstaller canônico)
; Compilar: ISCC.exe /DMyAppVersion=1.0.0 SwiftSend.iss
; Ou: .\build_installer.ps1 -Version 1.0.0

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif
; VersionInfoVersion exige X.X.X.X numérico (sem sufixo -dev / -rc)
#ifndef MyAppVersionInfo
  #define MyAppVersionInfo "0.0.0.0"
#endif

#define MyAppName "SwiftSend"
#define MyAppPublisher "SwiftSend"
#define MyAppExeName "SwiftSend.exe"
#define MyAppURL "https://github.com/GuilhermeRoesler/SwiftSend"

[Setup]
AppId={{B8E4F2A1-9C3D-4E5F-A6B7-8C9D0E1F2A3B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=SwiftSend-Setup-{#MyAppVersion}
SetupIconFile=..\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersionInfo}
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\python\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Transferência de arquivos na LAN"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
const
  WebView2ClientGuid = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2BootstrapperURL = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703';

function IsWebView2RuntimeInstalled: Boolean;
var
  Ver: String;
begin
  Result := False;
  if RegQueryStringValue(
    HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\' + WebView2ClientGuid,
    'pv', Ver
  ) then
  begin
    Result := (Ver <> '') and (Ver <> '0.0.0.0');
    if Result then Exit;
  end;
  if RegQueryStringValue(
    HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + WebView2ClientGuid,
    'pv', Ver
  ) then
  begin
    Result := (Ver <> '') and (Ver <> '0.0.0.0');
  end;
end;

function InstallWebView2Runtime: Boolean;
var
  ResultCode: Integer;
  Bootstrapper: String;
begin
  Result := True;
  if IsWebView2RuntimeInstalled then
    Exit;

  WizardForm.StatusLabel.Caption := 'Baixando Microsoft Edge WebView2 Runtime...';
  try
    DownloadTemporaryFile(WebView2BootstrapperURL, 'MicrosoftEdgeWebview2Setup.exe', '', nil);
  except
    MsgBox(
      'Não foi possível baixar o WebView2 Runtime.' + #13#10 +
      'Instale manualmente: https://developer.microsoft.com/microsoft-edge/webview2/',
      mbError, MB_OK
    );
    Result := False;
    Exit;
  end;

  Bootstrapper := ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe');
  WizardForm.StatusLabel.Caption := 'Instalando Microsoft Edge WebView2 Runtime...';
  if not Exec(Bootstrapper, '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    MsgBox('Falha ao iniciar o instalador do WebView2.', mbError, MB_OK);
    Result := False;
    Exit;
  end;

  if ResultCode <> 0 then
  begin
    MsgBox(
      'O instalador do WebView2 retornou código ' + IntToStr(ResultCode) + '.' + #13#10 +
      'O SwiftSend pode não abrir a janela desktop sem o WebView2.',
      mbError, MB_OK
    );
    Result := False;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpReady then
    Result := InstallWebView2Runtime;
end;
