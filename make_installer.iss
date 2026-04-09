[Setup]
AppName=Discord Compressor
AppVersion=1.0
DefaultDirName={autopf}\Discord Compressor
DefaultGroupName=Discord Compressor
UninstallDisplayIcon={app}\Discord Compresser.exe
Compression=lzma2
SolidCompression=yes
OutputDir=userdocs:Inno Setup Examples Output
OutputBaseFilename=DiscordCompressor_Install

[Files]
; Point this to the actual exe PyInstaller generated
Source: "C:\Users\Raskoll\Documents\discord_comp\dist\Discord Compresser.exe"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
; Adds the Right-Click Menu text
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\DiscordCompress"; ValueType: string; ValueName: ""; ValueData: "Compress for Discord (10MB)"; Flags: uninsdeletekey

; Adds the icon to the Right-Click Menu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\DiscordCompress"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\Discord Compresser.exe"""; Flags: uninsdeletekey

; Adds the actual execution command, passing the file path ("%1") to your app
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\DiscordCompress\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Discord Compresser.exe"" --headless ""%1"""; Flags: uninsdeletekey