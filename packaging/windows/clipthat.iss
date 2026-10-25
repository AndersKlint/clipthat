#if VER < EncodeVer(6, 3, 0)
  #error Inno Setup 6.3+ (6.x) is required for native x64 architecture selection
#endif
#ifndef SourceDir
  #error SourceDir must specify the absolute staged bundle directory
#endif
#ifndef OutputDir
  #error OutputDir must specify the absolute package output directory
#endif
#define AppExe "yt_section_downloader.exe"
#define AppVersion GetFileVersion(SourceDir + "\" + AppExe)

[Setup]
AppId=com.drjetski.clipthat
AppName=ClipThat!
AppVersion={#AppVersion}
AppPublisher=Dr. Jetski Studios
AppPublisherURL=https://drjetski.com
AppSupportURL=https://drjetski.com
AppUpdatesURL=https://drjetski.com
DefaultDirName={localappdata}\Programs\ClipThat!
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExe}
OutputDir={#OutputDir}
OutputBaseFilename=ClipThat-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\ClipThat!"; Filename: "{app}\{#AppExe}"; AppUserModelID: "com.drjetski.clipthat"
Name: "{userdesktop}\ClipThat!"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon; AppUserModelID: "com.drjetski.clipthat"

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,ClipThat!}"; Flags: nowait postinstall skipifsilent
