; ═══════════════════════════════════════════════════════════════════
; Echelon Windows Installer — Rebuilt from scratch
; Full engineering: UAC, silent kill, wait loop, uninstall previous,
; clear dir, VC++ redist, error handling, rollback
; ═══════════════════════════════════════════════════════════════════

Unicode True
SetCompressor /SOLID lzma

!define APP_NAME        "Echelon"
!define APP_VERSION     "2.0.0"
!define APP_PUBLISHER   "Zero"
!define APP_EXE         "Echelon.exe"
!define INSTALL_DIR     "$PROGRAMFILES64\Echelon"
!define UNINSTALL_KEY   "Software\Microsoft\Windows\CurrentVersion\Uninstall\Echelon"
!define REG_INSTALL_KEY "Software\Echelon"
!define VCREDIST_KEY    "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "Echelon-Setup.exe"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey HKLM "${REG_INSTALL_KEY}" "Install_Dir"

; ── UAC: always require full Administrator rights ──
RequestExecutionLevel admin

BrandingText "Echelon by Zero"
ShowInstDetails show
ShowUninstDetails show

; Modern UI 2
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; StrContains — find substring
!macro StrContains Dest Haystack Needle
  Push "${Haystack}"
  Push "${Needle}"
  Call StrContainsFunc
  Pop "${Dest}"
!macroend
!define StrContains "!insertmacro StrContains"

Function StrContainsFunc
  Exch $R0  ; Needle
  Exch
  Exch $R1  ; Haystack
  Push $R2
  Push $R3
  Push $R4
  StrLen $R3 $R0
  StrLen $R4 $R1
  IntOp $R4 $R4 - $R3
  StrCpy $R2 ""
  ${For} $R5 0 $R4
    StrCpy $R2 $R1 $R3 $R5
    ${If} $R2 == $R0
      StrCpy $R2 $R0
      ${Break}
    ${EndIf}
    StrCpy $R2 ""
  ${Next}
  Pop $R4
  Pop $R3
  Pop $R5
  Pop $R1
  Exch $R2
  Exch
  Pop $R0
FunctionEnd

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

; ═══════════════════════════════════════════════════════════════════
; Macro: Kill Echelon silently
; - If process not found: exits silently, no error logged
; - Waits up to 10 seconds (5 × 2s) for process to fully exit
; ═══════════════════════════════════════════════════════════════════
!macro KillEchelonSilent
  ; Use nsExec::Exec (NOT ExecToLog) so output is NEVER shown in the detail log
  ; cmd /c with 2>nul suppresses "process not found" stderr entirely
  ; Return code 128 = "process not found" = perfectly fine, discard silently
  nsExec::Exec 'cmd /c taskkill /F /IM "${APP_EXE}" /T 2>nul 1>nul'
  Pop $0  ; discard — 0=killed, 128=not found, both are OK

  ; Wait loop: verify the process is truly gone (up to 5 retries × 2s = 10s max)
  StrCpy $R0 0
  ${Do}
    ${If} $R0 >= 5
      ${Break}
    ${EndIf}
    Sleep 2000
    nsExec::ExecToStack 'cmd /c tasklist /FI "IMAGENAME eq ${APP_EXE}" /NH 2>nul'
    Pop $R1
    Pop $R2
    ${If} $R2 == ""
      ${Break}
    ${EndIf}
    ${StrContains} $R3 "No tasks" $R2
    ${If} $R3 != ""
      ${Break}
    ${EndIf}
    IntOp $R0 $R0 + 1
    nsExec::Exec 'cmd /c taskkill /F /IM "${APP_EXE}" /T 2>nul 1>nul'
    Pop $0
  ${Loop}
!macroend

; ═══════════════════════════════════════════════════════════════════
; Macro: Run previous version's uninstaller silently if found
; ═══════════════════════════════════════════════════════════════════
!macro RunPreviousUninstaller
  ReadRegStr $R3 HKLM "${UNINSTALL_KEY}" "QuietUninstallString"
  ${If} $R3 != ""
    DetailPrint "Removing previous version..."
    ExecWait '$R3' $R4
    Sleep 1000
  ${Else}
    ReadRegStr $R3 HKLM "${UNINSTALL_KEY}" "UninstallString"
    ${If} $R3 != ""
      DetailPrint "Removing previous version..."
      ExecWait '"$R3" /S' $R4
      Sleep 1000
    ${EndIf}
  ${EndIf}
!macroend

; ═══════════════════════════════════════════════════════════════════
; Function: Check if VC++ 2015-2022 x64 Redistributable is installed
; Returns: 1 on stack if installed, 0 if not
; ═══════════════════════════════════════════════════════════════════
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

; ═══════════════════════════════════════════════════════════════════
; MAIN INSTALL SECTION
; Phase 1: Pre-install cleanup (kill, uninstall old, clear dir)
; Phase 2: VC++ Redistributable (check registry, install if needed)
; Phase 3: Extract app files (with error check + rollback)
; Phase 4: Registry + shortcuts
; ═══════════════════════════════════════════════════════════════════
Section "Echelon" SecMain
  SectionIn RO

  ; ── PHASE 1: Pre-installation cleanup ──────────────────────────

  ; Kill any running Echelon — silently, NO output logged
  !insertmacro KillEchelonSilent


  ; Run previous version's uninstaller silently if found
  !insertmacro RunPreviousUninstaller

  ; Clear the entire install directory to guarantee no stale locked files
  ${If} ${FileExists} "$INSTDIR\*.*"
    DetailPrint "Clearing previous installation directory..."
    RMDir /r "$INSTDIR"
    ; Brief wait after delete for filesystem to settle
    Sleep 500
  ${EndIf}

  ; ── PHASE 2: VC++ Redistributable ──────────────────────────────

  DetailPrint "Checking Visual C++ 2015-2022 Runtime..."
  Call CheckVCRedistInstalled
  Pop $0
  ${If} $0 != 1
    DetailPrint "Installing Visual C++ 2015-2022 Redistributable..."
    ; Extract to temp to keep installer dir clean
    SetOutPath "$TEMP\EchelonSetup"
    ClearErrors
    File "vc_redist.x64.exe"
    ${If} ${Errors}
      MessageBox MB_OK|MB_ICONEXCLAMATION "Could not extract VC++ installer. Continuing — the app may not work if runtime is missing."
    ${Else}
      ExecWait '"$TEMP\EchelonSetup\vc_redist.x64.exe" /quiet /norestart' $1
      ${If} $1 != 0
      ${AndIf} $1 != 3010  ; 3010 = success, reboot required — acceptable
        MessageBox MB_OK|MB_ICONEXCLAMATION "Visual C++ Runtime installation returned code $1.$\nThe app may not work correctly.$\nIf you have issues, run vc_redist.x64.exe from Microsoft manually."
      ${EndIf}
      Delete "$TEMP\EchelonSetup\vc_redist.x64.exe"
      RMDir "$TEMP\EchelonSetup"
    ${EndIf}
  ${Else}
    DetailPrint "Visual C++ Runtime already installed — skipping."
  ${EndIf}

  ; ── PHASE 3: Extract application files ─────────────────────────

  DetailPrint "Installing Echelon ${APP_VERSION}..."
  SetOverwrite on
  ClearErrors
  SetOutPath "$INSTDIR"
  File /r "dist\Echelon\*.*"

  ; Check for extraction errors — rollback if any
  ${If} ${Errors}
    DetailPrint "ERROR: File extraction failed. Rolling back..."
    RMDir /r "$INSTDIR"
    MessageBox MB_OK|MB_ICONSTOP \
      "Installation failed: could not write files to $INSTDIR.$\r$\n$\r$\nMake sure you are running as Administrator and no antivirus is blocking the install.$\r$\n$\r$\nInstallation has been rolled back."
    Abort
  ${EndIf}

  ; ── PHASE 4: Registry — Add/Remove Programs ────────────────────

  WriteRegStr   HKLM "${REG_INSTALL_KEY}"   "Install_Dir"           "$INSTDIR"
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "DisplayName"           "${APP_NAME}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "UninstallString"       '"$INSTDIR\uninstall.exe"'
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "QuietUninstallString"  '"$INSTDIR\uninstall.exe" /S'
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "InstallLocation"       "$INSTDIR"
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "DisplayIcon"           "$INSTDIR\${APP_EXE},0"
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "Publisher"             "${APP_PUBLISHER}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "DisplayVersion"        "${APP_VERSION}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}"     "URLInfoAbout"          "https://github.com/gengenesix/echelon"
  WriteRegDWORD HKLM "${UNINSTALL_KEY}"     "NoModify"              1
  WriteRegDWORD HKLM "${UNINSTALL_KEY}"     "NoRepair"              1

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "EstimatedSize" "$0"

  WriteUninstaller "$INSTDIR\uninstall.exe"
  DetailPrint "Echelon installed successfully."
SectionEnd

; ── Start Menu Shortcuts ──────────────────────────────────────────
Section "Start Menu Shortcuts"
  CreateDirectory "$SMPROGRAMS\Echelon"
  CreateShortcut  "$SMPROGRAMS\Echelon\Echelon.lnk"   "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortcut  "$SMPROGRAMS\Echelon\Uninstall.lnk" "$INSTDIR\uninstall.exe"
SectionEnd

; ── Desktop Shortcut ─────────────────────────────────────────────
Section "Desktop Shortcut"
  CreateShortcut "$DESKTOP\Echelon.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
SectionEnd

; ═══════════════════════════════════════════════════════════════════
; UNINSTALLER
; ═══════════════════════════════════════════════════════════════════
Section "Uninstall"
  ; Kill process silently — no output, no "not found" error shown
  nsExec::Exec 'cmd /c taskkill /F /IM "${APP_EXE}" /T 2>nul 1>nul'
  Pop $0
  Sleep 1500

  ; Remove all application files
  RMDir /r "$INSTDIR"

  ; Remove shortcuts
  Delete "$SMPROGRAMS\Echelon\Echelon.lnk"
  Delete "$SMPROGRAMS\Echelon\Uninstall.lnk"
  RMDir  "$SMPROGRAMS\Echelon"
  Delete "$DESKTOP\Echelon.lnk"

  ; Clean up registry
  DeleteRegKey HKLM "${UNINSTALL_KEY}"
  DeleteRegKey HKLM "${REG_INSTALL_KEY}"

  ; Offer to remove user data
  MessageBox MB_YESNO "Remove Echelon settings and saved faces?" IDNO done
    RMDir /r "$APPDATA\Echelon"
  done:
SectionEnd
