; Inno Setup Script for Studaxis
; Builds a Windows installer that places Studaxis.exe in Program Files,
; creates a Desktop shortcut, and runs the app once post-install to trigger
; the Ollama model pull (hardware-aware: 4GB vs 8GB+ RAM).

#define MyAppName "Studaxis"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Studaxis"
#define MyAppURL "https://github.com/studaxis/studaxis"
#define MyAppExeName "Studaxis.exe"

; Icon: Add "SetupIconFile=studaxis.ico" below (create from frontend/public/pwa-512x512.png)
; Omitting it uses the default Inno Setup icon.

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Output: creates dist/Studaxis-Setup-1.0.0.exe (same dist/ as PyInstaller output)
OutputDir=dist
OutputBaseFilename=Studaxis-Setup-{#MyAppVersion}
; SetupIconFile=studaxis.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Require admin for Program Files install
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
; Uninstall
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Install the PyInstaller-built exe
Source: "dist\Studaxis.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Post-install: run the exe once to trigger hardware check + Ollama model pull (4GB vs 8GB+)
; The app will open the browser and start the Ollama model download based on detected RAM.
Description: "Launch {#MyAppName} to pull the Ollama model for your hardware (4GB / 8GB+ RAM)"; Filename: "{app}\{#MyAppExeName}"; Flags: nowait postinstall skipifsilent

