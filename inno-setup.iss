; Inno Setup Script for generating Windows Installer of Local Console.

#define MyAppName "Local Console"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Sony Semiconductor Solutions Corporation"
#define MyAppExeName "local-console.exe"
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ".myp"
#define MyAppCanonical StringChange(MyAppName, " ", "")
#define MyAppAssocKey MyAppCanonical + MyAppAssocExt

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{63A38119-1103-4ED1-AD9B-0D873FB090B5}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppCanonical}
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputBaseFilename=local-console-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
AlwaysRestart=no
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "wedge-cli\*";  Excludes: "*.pyc,__pycache__\*,*.egg-info\*"; DestDir: "{tmp}\wedge-cli"; Flags: recursesubdirs

[Run]
Filename: "powershell.exe"; Parameters: "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser; {tmp}\\wedge-cli\\windows\\install.ps1 ""{app}"""; Flags: waituntilterminated;

[UninstallDelete]
Type: files; Name: "{userdesktop}\Wedge GUI.lnk"
Type: files; Name: "{userdesktop}\Local Console.lnk"
Type: filesandordirs; Name: "{app}"
