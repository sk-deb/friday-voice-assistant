; Inno Setup script for FRIDAY.
;
; Compile after PyInstaller has produced dist\Friday:
;     ISCC.exe packaging\friday_installer.iss
;
; Produces dist\installer\FridaySetup.exe - a normal Windows installer with
; Start Menu entries, an optional desktop icon, an optional autostart entry,
; and a clean uninstall that leaves the owner's data behind unless they ask
; for it to be removed.

#define AppName "Friday"
#define AppVersion "1.1.0"
#define AppPublisher "Srihari Kalesh"
#define AppExe "friday.exe"

[Setup]
AppId={{8F3C1D74-5A21-4E96-9C8B-FRIDAY000001}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=FridaySetup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\{#AppExe}
; The bundle is large; refuse to start rather than fail halfway through.
ExtraDiskSpaceRequired=0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "Start FRIDAY in always-listening mode when I sign in"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
; The whole PyInstaller folder build, recursively.
Source: "..\dist\Friday\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Per-user data directory, writable without administrator rights.
Name: "{userappdata}\Friday"; Flags: uninsneveruninstall

[Icons]
; Three shortcuts because FRIDAY has three genuinely different modes.
Name: "{group}\Friday (always listening)"; Filename: "{app}\{#AppExe}"; Parameters: "--mode wake"; Comment: "Say the wake word to talk"
Name: "{group}\Friday (press to talk)"; Filename: "{app}\{#AppExe}"; Parameters: "--mode ptt"; Comment: "Press Enter, then speak"
Name: "{group}\Friday (type instead)"; Filename: "{app}\{#AppExe}"; Parameters: "--mode text"; Comment: "No microphone needed"
Name: "{group}\Friday settings (.env)"; Filename: "notepad.exe"; Parameters: """{userappdata}\Friday\.env"""; Comment: "Gemini API key and preferences"
Name: "{group}\Friday documentation"; Filename: "{app}\docs"
Name: "{group}\Uninstall Friday"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Friday"; Filename: "{app}\{#AppExe}"; Parameters: "--mode ptt"; Tasks: desktopicon
Name: "{userstartup}\Friday"; Filename: "{app}\{#AppExe}"; Parameters: "--mode wake"; Tasks: startup

[Run]
Filename: "notepad.exe"; Parameters: """{userappdata}\Friday\.env"""; Description: "Open settings to paste my Gemini API key"; Flags: postinstall nowait skipifsilent
Filename: "{app}\{#AppExe}"; Parameters: "--mode text"; Description: "Start FRIDAY now (typed mode)"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Only build leftovers. Conversation history, notes and the API key survive an
; uninstall on purpose - see the note in Code below.
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
procedure SeedEnvFile();
var
  DataDir, EnvPath, Template: String;
  Lines: TArrayOfString;
begin
  DataDir := ExpandConstant('{userappdata}\Friday');
  EnvPath := DataDir + '\.env';

  if FileExists(EnvPath) then
    exit;  { never overwrite an existing key }

  ForceDirectories(DataDir);

  Template := ExpandConstant('{app}\.env.example');
  if FileExists(Template) then
  begin
    FileCopy(Template, EnvPath, True);
    exit;
  end;

  SetArrayLength(Lines, 6);
  Lines[0] := '# FRIDAY settings. Restart FRIDAY after editing.';
  Lines[1] := '# Get a free key from Google AI Studio, then paste it below.';
  Lines[2] := 'GEMINI_API_KEY=';
  Lines[3] := '';
  Lines[4] := '# Default language and the ones she may switch into.';
  Lines[5] := 'FRIDAY_LANGUAGE=en';
  SaveStringsToUTF8File(EnvPath, Lines, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    SeedEnvFile();
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\Friday');
    if DirExists(DataDir) then
    begin
      { Downloaded speech models are large and the notes are irreplaceable, so
        ask rather than assume. }
      if MsgBox('Also delete FRIDAY''s memory, notes, downloaded speech models'
        + ' and your API key?' + #13#10#13#10 + DataDir + #13#10#13#10
        + 'Choose No if you plan to reinstall.',
        mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;
