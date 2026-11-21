; J.A.R.V.I.S. Mark LVI Core — Inno Setup Script
; Builds: JARVIS_Mark_LVI_Setup.exe

#define MyAppName "J.A.R.V.I.S. Mark LVI Core"
#define MyAppVersion "56.2.0"
#define MyAppPublisher "Black Intel"
#define MyAppURL "http://127.0.0.1:8000/app"
#define MyAppExeName "launch_jarvis.bat"

[Setup]
AppId={{E7BC7937-0D61-4942-83C4-B3F5A9674D30}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\JARVIS_Mark_LVI
DefaultGroupName={#MyAppName}
LicenseFile=..\LICENSE
OutputDir=..\..\release
OutputBaseFilename=JARVIS_Mark_LVI_Setup
SetupIconFile=..\config\jarvis.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\release\JARVIS_Mark_LVI_Windows_x64\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\config\jarvis.ico"
Name: "{group}\Setup Wizard"; Filename: "{app}\install_jarvis.bat"; IconFilename: "{app}\config\jarvis.ico"
Name: "{group}\Stop Host"; Filename: "{app}\stop_jarvis.bat"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\config\jarvis.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\install_jarvis.bat"; Description: "Run First-Time Setup Wizard"; Flags: postinstall shellexec skipifsilent
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: postinstall shellexec nowait skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\core\__pycache__"
Type: filesandordirs; Name: "{app}\dashboard\__pycache__"
Type: filesandordirs; Name: "{app}\installer\__pycache__"
Type: filesandordirs; Name: "{app}\memory\__pycache__"
