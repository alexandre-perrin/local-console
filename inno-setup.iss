; Inno Setup Script for generating Windows Installer of Offline Tool.

#define MyAppName "Offline Tool"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Sony Semiconductor Solutions Corporation"
#define MyAppExeName "offline-tool.exe"
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
ChangesAssociations=yes
DisableProgramGroupPage=yes
OutputBaseFilename=offline-tool-setup
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
Filename: "powershell.exe"; Parameters: "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser; {tmp}\wedge-cli\windows\wedge_install.ps1"; Flags: waituntilterminated;

[UninstallDelete]
Type: files; Name: "{userdesktop}\Wedge GUI.lnk"
Type: filesandordirs; Name: "{userappdata}\WedgeCLI"
