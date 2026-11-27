; Inno Setup Script Template for SMTE School Project Applications
; Variables expected from command line:
;   /DAppName=StudentManagement
;   /DAppExe=StudentManagement.exe
;   /DAppVersion=1.3.1
;   /DSourceExe=..\..\..\dist\StudentManagement.exe
;   /DOutputDir=..\..\..\dist\installers

#ifndef AppName
  #define AppName "StudentManagement"
#endif

#ifndef AppExe
  #define AppExe "StudentManagement.exe"
#endif

#ifndef AppVersion
  #define AppVersion "1.3.1"
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
#ifdef AppIcon
SetupIconFile={#AppIcon}
#endif
OutputDir={#OutputDir}
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
#ifdef EnableLanFirewall
PrivilegesRequired=admin
#else
PrivilegesRequired=lowest
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
#ifdef SourceDir
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#else
#ifdef SourceExe
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "{#AppExe}"; Flags: ignoreversion
#else
Source: "..\..\..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif
#endif

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
#ifdef EnableLanFirewall
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""SMTE Librarian LAN HTTP"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""SMTE Librarian LAN HTTP"" dir=in action=allow protocol=TCP localport=8765 profile=private,domain"; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""SMTE Librarian LAN Discovery"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""SMTE Librarian LAN Discovery"" dir=in action=allow protocol=UDP localport=8766 profile=private,domain"; Flags: runhidden waituntilterminated
#endif
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

#ifdef EnableLanFirewall
[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""SMTE Librarian LAN HTTP"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveLanHttpRule"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""SMTE Librarian LAN Discovery"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveLanDiscoveryRule"
#endif
