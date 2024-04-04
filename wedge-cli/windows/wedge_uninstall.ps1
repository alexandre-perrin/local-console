
function Main
{
    Grant-Privileges

    Write-LogMessage "Uninstalling Wedge CLI & GUI"

    # Construct the full path to the new directory within APPDATA
    $fullPath = Join-Path -Path $env:APPDATA -ChildPath "OfflineTool"
    if (Test-Path -Path $fullPath)
    {
        Remove-Item -Path $fullPath -Recurse -Force
    }

    $WshShell = New-Object -comObject WScript.Shell
    $IconPath = Join-Path -Path $WshShell.SpecialFolders("Desktop") -ChildPath "Wedge GUI.lnk"
    if (Test-Path -Path $IconPath)
    {
        Remove-Item -Path $IconPath -Force
    }

    Restore-ExecutionPolicy
}

function Grant-Privileges {

    # Get the ID and security principal of the current user account
    $myWindowsID = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $myWindowsPrincipal = new-object System.Security.Principal.WindowsPrincipal($myWindowsID)

    # Get the security principal for the Administrator role
    $adminRole = [System.Security.Principal.WindowsBuiltInRole]::Administrator

    # Check to see if we are currently running "as Administrator"
    if ($myWindowsPrincipal.IsInRole($adminRole)) {
        # We are running "as Administrator" - so change the title and background color to indicate this
        $Host.UI.RawUI.WindowTitle = $Script:MyInvocation.MyCommand.Name + "(Elevated)"
        $Host.UI.RawUI.BackgroundColor = "DarkBlue"
    }
    else {
        # We are not running "as Administrator" - so relaunch as administrator

        # First ensure we can run a script, then actually run this script as Administrator
        $cmdLine = Get-ScriptPath
        Start-Process -FilePath "powershell" -Verb RunAs -Wait -ArgumentList "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser; `"$cmdLine`""

        # Exit from the current, unelevated, process
        Exit
    }
}

function Restore-ExecutionPolicy {
    Write-Host "Restoring default execution policy"
    Set-ExecutionPolicy -ExecutionPolicy Default -Scope CurrentUser
}

function Write-LogMessage {
    param(
        [string]$Message
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Write-Host $logMessage
}

function Get-ScriptPath
{
    $Script:MyInvocation.MyCommand.Path
}

Main
