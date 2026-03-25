; ═══════════════════════════════════════════════════════════════════
; Dark-Army Windows Installer
; Face Swap + Voice Changer — by Zero
; ═══════════════════════════════════════════════════════════════════

Unicode True
SetCompressor /SOLID lzma

!define APP_NAME        "Dark-Army"
!define APP_VERSION     "1.0.0"
!define APP_PUBLISHER   "Zero"
!define APP_EXE         "DarkArmy.exe"
!define INSTALL_DIR     "$PROGRAMFILES64\DarkArmy"
!define UNINSTALL_KEY   "Software\Microsoft\Windows\CurrentVersion\Uninstall\DarkArmy"
!define REG_INSTALL_KEY "Software\DarkArmy"
!define VCREDIST_KEY    "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "DarkArmy-Setup.exe"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey HKLM "${REG_INSTALL_KEY}" "Install_Dir"
RequestExecutionLevel admin

BrandingText "Dark-Army by Zero"
ShowInstDetails show
ShowUninstDetails show

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON                "assets\icons\echelon.ico"
!define MUI_UNICON              "assets\icons\echelon.ico"
!define MUI_WELCOMEPAGE_TITLE   "Welcome to Dark-Army v${APP_VERSION}"
!define MUI_WELCOMEPAGE_TEXT    "Dark-Army combines real-time face swap AND voice changer in one app.$\r$\n$\r$\nWorks with Discord, Zoom, Google Meet, Teams, and OBS.$\r$\n$\r$\nCreated by Zero."
!define MUI_FINISHPAGE_RUN      "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Dark-Army now"
!define MUI_FINISHPAGE_LINK     "github.com/gengenesix/dark-army"
!define MUI_FINISHPAGE_LINK_LOCATION "https://github.com/gengenesix/dark-army"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Function CheckVCRedistInstalled
  ReadRegDWORD $0 HKLM "${VCREDIST_KEY}" "Installed"
  ${If} $0 == 1
    Push 1
    Return
  ${EndIf}
  ReadRegStr $0 HKLM "${VCREDIST_KEY}" "Version"
  ${If} $0 != ""
    Push 1
    Return
  ${EndIf}
  Push 0
FunctionEnd

Section "DarkArmy" SecMain
  SectionIn RO

  ; ── Kill any running instance silently ──
  nsExec::Exec 'cmd /c taskkill /F /IM "${APP_EXE}" /T 2>nul 1>nul'
  Pop $0
  Sleep 1500

  ; ── Run previous uninstaller silently ──
  ReadRegStr $R3 HKLM "${UNINSTALL_KEY}" "QuietUninstallString"
  ${If} $R3 != ""
    ExecWait '$R3' $R4
    Sleep 1000
  ${EndIf}

  ; ── Clear previous install dir ──
  ${If} ${FileExists} "$INSTDIR\*.*"
    RMDir /r "$INSTDIR"
    Sleep 500
  ${EndIf}

  ; ── Install VC++ Redist ──
  DetailPrint "Checking Visual C++ Runtime..."
  Call CheckVCRedistInstalled
  Pop $0
  ${If} $0 != 1
    DetailPrint "Installing Visual C++ 2015-2022 Runtime..."
    SetOutPath "$TEMP\DarkArmySetup"
    ClearErrors
    File "vc_redist.x64.exe"
    ${IfNot} ${Errors}
      ExecWait '"$TEMP\DarkArmySetup\vc_redist.x64.exe" /quiet /norestart' $1
      Delete "$TEMP\DarkArmySetup\vc_redist.x64.exe"
      RMDir "$TEMP\DarkArmySetup"
    ${EndIf}
  ${Else}
    DetailPrint "VC++ Runtime already installed."
  ${EndIf}

  ; ── Extract app files ──
  DetailPrint "Installing Dark-Army ${APP_VERSION}..."
  SetOverwrite on
  ClearErrors
  SetOutPath "$INSTDIR"
  File /r "dist\DarkArmy\*.*"

  ${If} ${Errors}
    RMDir /r "$INSTDIR"
    MessageBox MB_OK|MB_ICONSTOP "Installation failed. Please run as Administrator and check antivirus settings."
    Abort
  ${EndIf}

  ; ── Registry ──
  WriteRegStr   HKLM "${REG_INSTALL_KEY}"   "Install_Dir"           "$INSTDIR"
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "DisplayName"           "${APP_NAME}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "UninstallString"       '"$INSTDIR\uninstall.exe"'
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "QuietUninstallString"  '"$INSTDIR\uninstall.exe" /S'
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "InstallLocation"       "$INSTDIR"
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "DisplayIcon"           "$INSTDIR\${APP_EXE},0"
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "Publisher"             "${APP_PUBLISHER}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "DisplayVersion"        "${APP_VERSION}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "URLInfoAbout"          "https://github.com/gengenesix/dark-army"
  WriteRegDWORD HKLM "${UNINSTALL_KEY}"     "NoModify"              1
  WriteRegDWORD HKLM "${UNINSTALL_KEY}"     "NoRepair"              1

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "EstimatedSize" "$0"

  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Start Menu Shortcuts"
  CreateDirectory "$SMPROGRAMS\Dark-Army"
  CreateShortcut  "$SMPROGRAMS\Dark-Army\Dark-Army.lnk"  "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortcut  "$SMPROGRAMS\Dark-Army\Uninstall.lnk"  "$INSTDIR\uninstall.exe"
SectionEnd

Section "Desktop Shortcut"
  CreateShortcut "$DESKTOP\Dark-Army.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
SectionEnd

Section "Uninstall"
  nsExec::Exec 'cmd /c taskkill /F /IM "${APP_EXE}" /T 2>nul 1>nul'
  Pop $0
  Sleep 1500
  RMDir /r "$INSTDIR"
  Delete "$SMPROGRAMS\Dark-Army\Dark-Army.lnk"
  Delete "$SMPROGRAMS\Dark-Army\Uninstall.lnk"
  RMDir  "$SMPROGRAMS\Dark-Army"
  Delete "$DESKTOP\Dark-Army.lnk"
  DeleteRegKey HKLM "${UNINSTALL_KEY}"
  DeleteRegKey HKLM "${REG_INSTALL_KEY}"
  MessageBox MB_YESNO "Remove Dark-Army settings and voice models?" IDNO done
    RMDir /r "$APPDATA\DarkArmy"
  done:
SectionEnd
