[Setup]
AppName=Water Delivery CRM
AppVersion=1.0
DefaultDirName={pf32}\WaterDeliveryCRM
DefaultGroupName=WaterDeliveryCRM
OutputDir=dist
OutputBaseFilename=WaterDeliveryCRM_Installer
Compression=lzma
SolidCompression=yes

[Files]
Source: "{#ProjectDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs; Excludes: "\.git\*;dist\*;\.venv\*;node_modules\*"

[Icons]
Name: "{group}\Run Server"; Filename: "{app}\run_server.bat"; WorkingDir: "{app}"
Name: "{group}\Run Bot"; Filename: "{app}\run_bot.bat"; WorkingDir: "{app}"

[Run]
Filename: "{app}\scripts\install_local.ps1"; Parameters: ""; WorkingDir: "{app}"; Flags: shellexec skipifsilent

; NOTE: To compile this script you need Inno Setup (https://jrsoftware.org/)
