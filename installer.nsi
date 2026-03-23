; ═══════════════════════════════════════════════════════
; Echelon Windows Installer
; Created by Zero
; ═══════════════════════════════════════════════════════

Unicode True
!define APP_NAME      "Echelon"
!define APP_VERSION   "2.0.0"
!define APP_PUBLISHER "Zero"
!define APP_EXE       "Echelon.exe"
!define INSTALL_DIR   "$PROGRAMFILES64\Echelon"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\Echelon"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "Echelon-Setup.exe"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey HKLM "Software\Echelon" "Install_Dir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
BrandingText "Echelon by Zero"
ShowInstDetails show

; Modern UI 2
!include "MUI2.nsh"
!include "FileFunc.nsh"

; UI Settings
!define MUI_ABORTWARNING
!define MUI_ICON                          "assets\icons\echelon.ico"
!define MUI_UNICON                        "assets\icons\echelon.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP      "assets\icons\installer_banner.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP            "assets\icons\installer_header.bmp"
!define MUI_HEADERIMAGE_RIGHT
!define MUI_WELCOMEPAGE_TITLE             "Welcome to Echelon v${APP_VERSION}"
!define MUI_WELCOMEPAGE_TEXT              "Echelon lets you swap your face in real-time during any video call.$\r$\n$\r$\nWorks with Zoom, Google Meet, Discord, WhatsApp, and Teams.$\r$\n$\r$\nCreated by Zero."
!define MUI_FINISHPAGE_RUN                "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT           "Launch Echelon now"
!define MUI_FINISHPAGE_SHOWREADME         ""
!define MUI_FINISHPAGE_LINK               "github.com/gengenesix/echelon"
!define MUI_FINISHPAGE_LINK_LOCATION      "https://github.com/gengenesix/echelon"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ── Main Install ─────────────────────────────────────
Section "Echelon" SecMain
  SectionIn RO  ; Required section

  SetOutPath "$INSTDIR"

  ; Copy all files from PyInstaller output
  File /r "dist\Echelon\*.*"

  ; Write registry entries
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayName"     "Echelon"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "UninstallString"  '"$INSTDIR\uninstall.exe"'
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayIcon"     "$INSTDIR\${APP_EXE}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "Publisher"       "${APP_PUBLISHER}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayVersion"  "${APP_VERSION}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "URLInfoAbout"    "https://github.com/gengenesix/echelon"
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify"        1
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair"        1

  ; Get install size
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "EstimatedSize" "$0"

  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; ── Start Menu ───────────────────────────────────────
Section "Start Menu Shortcuts"
  CreateDirectory "$SMPROGRAMS\Echelon"
  CreateShortcut  "$SMPROGRAMS\Echelon\Echelon.lnk"    "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortcut  "$SMPROGRAMS\Echelon\Uninstall.lnk"  "$INSTDIR\uninstall.exe"
SectionEnd

; ── Desktop Shortcut ─────────────────────────────────
Section "Desktop Shortcut"
  CreateShortcut "$DESKTOP\Echelon.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
SectionEnd

; ── Uninstaller ──────────────────────────────────────
Section "Uninstall"
  ; Kill running instance
  ExecWait 'taskkill /F /IM "${APP_EXE}" /T' $0

  ; Remove files
  RMDir /r "$INSTDIR"

  ; Remove shortcuts
  Delete "$SMPROGRAMS\Echelon\Echelon.lnk"
  Delete "$SMPROGRAMS\Echelon\Uninstall.lnk"
  RMDir  "$SMPROGRAMS\Echelon"
  Delete "$DESKTOP\Echelon.lnk"

  ; Remove registry entries
  DeleteRegKey HKLM "${UNINSTALL_KEY}"
  DeleteRegKey HKLM "Software\Echelon"

  ; Remove user data (optional — ask user)
  MessageBox MB_YESNO "Remove Echelon settings and saved faces?" IDNO skip_userdata
    RMDir /r "$APPDATA\Echelon"
  skip_userdata:
SectionEnd
