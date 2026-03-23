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
!define MUI_ICON                "assets\icons\echelon.ico"
!define MUI_UNICON              "assets\icons\echelon.ico"
!define MUI_WELCOMEPAGE_TITLE   "Welcome to Echelon v${APP_VERSION}"
!define MUI_WELCOMEPAGE_TEXT    "Echelon lets you swap your face in real-time during any video call.$\r$\n$\r$\nWorks with Zoom, Google Meet, Discord, WhatsApp, and Teams.$\r$\n$\r$\nCreated by Zero.$\r$\n$\r$\nThis installer will automatically install all required components."
!define MUI_FINISHPAGE_RUN      "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Echelon now"
!define MUI_FINISHPAGE_LINK     "github.com/gengenesix/echelon"
!define MUI_FINISHPAGE_LINK_LOCATION "https://github.com/gengenesix/echelon"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ── Helper: Check if VC++ 2022 is installed ───────────
Function CheckVCRedist
  ; Check for VC++ 2015-2022 x64
  ReadRegDWORD $0 HKLM "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64" "Installed"
  ${If} $0 == 1
    ; Already installed
    Return
  ${EndIf}
  ; Also check newer registry path
  ReadRegStr $1 HKLM "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Version"
  ${If} $1 != ""
    Return
  ${EndIf}
  ; Not found — install it
  DetailPrint "Installing Microsoft Visual C++ Runtime (required)..."
  SetDetailsPrint listonly
  ExecWait '"$INSTDIR\_redist\vc_redist.x64.exe" /install /quiet /norestart' $2
  SetDetailsPrint both
  ${If} $2 != 0
    ${If} $2 != 3010  ; 3010 = success, reboot required
      MessageBox MB_OK|MB_ICONEXCLAMATION "Visual C++ Runtime installation returned code $2. The app may not work correctly. Please install vc_redist.x64.exe manually from Microsoft."
    ${EndIf}
  ${EndIf}
FunctionEnd

; ── Main Install ─────────────────────────────────────
Section "Echelon" SecMain
  SectionIn RO

  ; Install app files
  SetOutPath "$INSTDIR"
  File /r "dist\Echelon\*.*"

  ; Install VC++ redist
  SetOutPath "$INSTDIR\_redist"
  File "vc_redist.x64.exe"

  ; Run VC++ check/install
  Call CheckVCRedist

  ; Write registry
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayName"     "Echelon"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayIcon"     "$INSTDIR\${APP_EXE}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "Publisher"       "${APP_PUBLISHER}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayVersion"  "${APP_VERSION}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "URLInfoAbout"    "https://github.com/gengenesix/echelon"
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify"        1
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair"        1

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "EstimatedSize" "$0"

  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; ── Start Menu ───────────────────────────────────────
Section "Start Menu Shortcuts"
  CreateDirectory "$SMPROGRAMS\Echelon"
  CreateShortcut  "$SMPROGRAMS\Echelon\Echelon.lnk"   "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortcut  "$SMPROGRAMS\Echelon\Uninstall.lnk" "$INSTDIR\uninstall.exe"
SectionEnd

; ── Desktop Shortcut ─────────────────────────────────
Section "Desktop Shortcut"
  CreateShortcut "$DESKTOP\Echelon.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
SectionEnd

; ── Uninstaller ──────────────────────────────────────
Section "Uninstall"
  ExecWait 'taskkill /F /IM "${APP_EXE}" /T'
  RMDir /r "$INSTDIR"
  Delete "$SMPROGRAMS\Echelon\Echelon.lnk"
  Delete "$SMPROGRAMS\Echelon\Uninstall.lnk"
  RMDir  "$SMPROGRAMS\Echelon"
  Delete "$DESKTOP\Echelon.lnk"
  DeleteRegKey HKLM "${UNINSTALL_KEY}"
  DeleteRegKey HKLM "Software\Echelon"
  MessageBox MB_YESNO "Remove Echelon settings and saved faces?" IDNO done
    RMDir /r "$APPDATA\Echelon"
  done:
SectionEnd
