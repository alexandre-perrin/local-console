$rootPath = Split-Path $MyInvocation.MyCommand.Path -parent
$utils = Join-Path -Path $rootPath -ChildPath "utils.ps1"
. $utils

function Main
{
    Set-TemporalExecutionPolicy

    Write-LogMessage "Uninstalling Offline Tool"

    # Construct the full path to the new directory within APPDATA
    $fullPath = Join-Path -Path $env:APPDATA -ChildPath "OfflineTool"
    if (Test-Path -Path $fullPath)
    {
        Write-LogMessage "Removing program files"
        Remove-Item -Path $fullPath -Recurse -Force
    }

    $WshShell = New-Object -comObject WScript.Shell
    $IconPath = Join-Path -Path $WshShell.SpecialFolders("Desktop") -ChildPath "Wedge GUI.lnk"
    if (Test-Path -Path $IconPath)
    {
        Write-LogMessage "Removing desktop shortcut"
        Remove-Item -Path $IconPath -Force
    }

    Restore-DefaultExecutionPolicy
    Wait-UserInput
}

Main
