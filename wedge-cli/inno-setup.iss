; Inno Setup Script for generating Windows Installer of Offline Tool.

#define MyAppName "Offline Tool"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Sony Semiconductor Solutions Corporation"
#define MyAppExeName "offline-tool.exe"
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ".myp"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{63A38119-1103-4ED1-AD9B-0D873FB090B5}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
ChangesAssociations=yes
DisableProgramGroupPage=yes
; Remove the following line to run in administrative install mode (install for all users.)
PrivilegesRequired=lowest
OutputBaseFilename=offline-tool-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";

[Files]
Source: "offline_tool\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion; Components: OfflineTool
Source: "offline_tool\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: OfflineTool
; NOTE: Don't use "Flags: ignoreversion" on any shared system files
Source: "mosquitto-2.0.18-install-windows-x64.exe"; DestDir: "{app}"; Components: Mosquitto

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "gui"; Tasks: desktopicon

[Run]
Filename: "{app}\mosquitto-2.0.18-install-windows-x64.exe"; Description: "Install Mosquitto"; Components: Mosquitto; Flags: shellexec hidewizard;

[Components]
Name: "OfflineTool"; Description: "Install Offline Tool"; Types: DefaultType; Flags: fixed
Name: "Mosquitto"; Description: "Install Mosquitto"; Types: DefaultType

[Types]
Name: "DefaultType"; Description: "DefaultType"; Flags: iscustom
