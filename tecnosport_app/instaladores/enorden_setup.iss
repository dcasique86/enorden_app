; EnOrden-1.0.0 Setup script (Inno Setup 6)
; Perfil de usuario: instalación en %LOCALAPPDATA%\EnOrden sin permisos de admin.
; La base de datos, backups y logs se crean junto al .exe en el primer inicio.

#define AppName "EnOrden"
#define AppVersion "1.0.0"
#define AppPublisher "EnOrden"
#define AppExeName "EnOrden.exe"

[Setup]
AppId={{8F3E4C21-9A2B-4D5E-B7C1-1234567890AB}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\EnOrden
DefaultGroupName=EnOrden
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=C:\EnOrden\Release
OutputBaseFilename=EnOrden-Setup-{#AppVersion}
SetupIconFile=..\assets\en_orden.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\en_orden.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\en_orden.ico"; Tasks: desktopicon
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\en_orden.ico"; Tasks: startmenuicon
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\en_orden.ico"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce
Name: "startmenuicon"; Description: "Crear acceso directo en el Menú Inicio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Run]
; Casilla "Iniciar EnOrden al finalizar la instalación" (activada por defecto).
Filename: "{app}\{#AppExeName}"; Description: "Iniciar {#AppName} ahora"; Flags: nowait postinstall skipifsilent