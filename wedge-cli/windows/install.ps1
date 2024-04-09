$rootPath = Split-Path $MyInvocation.MyCommand.Path -parent
$utils = Join-Path $rootPath "utils.ps1"
. $utils

function Main
{
    $stepsPath = Join-Path $rootPath "steps"
    $scriptSys = Join-Path $stepsPath "sys.ps1"
    $scriptApp = Join-Path $stepsPath "app.ps1"

    Write-LogMessage "Installing system dependencies"
    $SysRedirectArgs = ""
    $SysLogFile = "$RedirectLogPath-sys"
    if ($DoRedirect) {
        $SysRedirectArgs = "-TranscriptPath `"$SysLogFile`""
    }
    Run-Privileged "$scriptSys" "$SysRedirectArgs"
    if ($DoRedirect) {
        cat "$SysLogFile" >> $RedirectLogPath
        rm "$SysLogFile"
    }
    Write-LogMessage "Done installing system dependencies"

    Write-LogMessage "Installing Offline Tool"
    $AppRedirectArgs = ""
    $AppLogFile = "$RedirectLogPath-app"
    if ($DoRedirect) {
        $AppRedirectArgs = "-TranscriptPath `"$AppLogFile`""
    }
    Run-Unprivileged "$scriptApp" "$AppRedirectArgs"
    if ($DoRedirect) {
        cat "$AppLogFile" >> $RedirectLogPath
        rm "$AppLogFile"
    }
    Write-LogMessage "Done installing Offline Tool"

    Restore-DefaultExecutionPolicy
    Wait-UserInput
}

Main
