; Inno Setup Script Template for SMTE School Project Applications
; Variables expected from command line:
;   /DAppName=StudentManagement
;   /DAppExe=StudentManagement.exe
;   /DAppVersion=1.1.1
;   /DSourceExe=..\..\..\dist\StudentManagement.exe
;   /DOutputDir=..\..\..\dist\installers

#ifndef AppName
  #define AppName "StudentManagement"
#endif

#ifndef AppExe
  #define AppExe "StudentManagement.exe"
#endif

#ifndef AppVersion
  #define AppVersion "1.1.1"
#endif

#ifndef SourceExe
  #define SourceExe "..\..\..\dist\" + AppExe
#endif

#ifndef OutputDir
  #define OutputDir "..\..\..\dist\installers"
#endif

[Setup]
AppId={{C78DFE32-0941-4E7B-BFA6-92AE8997321F}-{#AppName}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
UninstallDisplayName={#AppName} v{#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
VersionInfoTextVersion={#AppVersion}
AppPublisher=School Management System
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir={#OutputDir}
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "{#AppExe}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
