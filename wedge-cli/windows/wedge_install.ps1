# Current limitations:
# - This script assumes a 64-bit windows installation

# URLs of binary dependencies
$DepURLMosquitto = 'https://mosquitto.org/files/binary/win64/mosquitto-2.0.9-install-windows-x64.exe'
$DepURLPython = 'https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe'
$DepURLGit = 'https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe'
$DepURLFlatc = 'https://github.com/google/flatbuffers/releases/download/v24.3.25/Windows.flatc.binary.zip'

function Main
{
    Write-LogMessage "Installing system dependencies"

    Grant-Privileges
    Get-Mosquitto
    Initialize-Mosquitto
    Get-Git
    Get-Python311

    Write-LogMessage "Installing Wedge CLI"

    Refresh-Path
    $appDataDir = Create-AppDataDirectory -DirectoryName "WedgeCLI"
    $virtualenvDir = Join-Path -Path $appDataDir -ChildPath "virtualenv"
    Create-PythonEnvWithExecutable -VirtualenvDir $virtualenvDir

    $binPath = Join-Path -Path $VirtualenvDir -ChildPath "Scripts"
    Get-FlatcBinary -ScriptsDir $binPath
    Create-DesktopShortcut -VirtualenvDir $virtualenvDir

    Restore-ExecutionPolicy
    Wait-UserInput
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

function Wait-UserInput {
    $wait = 20
    Write-LogMessage "Will close in $wait seconds or on Enter keypress..."
    Start-Sleep -milliseconds 100;
    $Host.ui.RawUI.FlushInputBuffer();
    $counter = 0
    while(!$Host.UI.RawUI.KeyAvailable -and ($counter++ -lt $wait))
    {
        [Threading.Thread]::Sleep( 1000 )
    }
}

function Get-ScriptPath
{
    $Script:MyInvocation.MyCommand.Path
}

function Get-Mosquitto {

    $mosquittoExecPath = "$(Get-ProgramFilesPath)\mosquitto\mosquitto.exe"
    if (Test-ExecutablePath -Path $mosquittoExecPath)
    {
        Write-LogMessage "Mosquitto is already installed."
        return
    }

    # Download the installer
    Write-LogMessage "Downloading installer for the Mosquitto MQTT broker..."

    # Temporary target
    $downloadPath = "$env:TEMP\mosquitto-installer.exe"
    Invoke-WebRequest -Uri $DepURLMosquitto -OutFile $downloadPath

    # Install silently
    Write-LogMessage "Installing the Mosquitto MQTT broker..."
    Start-Process -FilePath $downloadPath -ArgumentList '/S' -Wait

    # Cleanup downloaded installer
    Remove-Item -Path $downloadPath

    Write-LogMessage "Mosquitto installation complete."
}

function Initialize-Mosquitto {
    # Check if the Mosquitto service has been added and remove it if found
    $service = Get-Service -DisplayName "*mosquitto*" -ErrorAction SilentlyContinue

    # Check if the service was found
    if ($service -ne $null) {
        Write-LogMessage "Found Windows Service for Mosquitto. Preparing to remove..."
        Write-Host "DisplayName: $($service.DisplayName)"
        Write-Host "Status: $($service.Status)"
        Write-Host "ServiceName: $($service.Name)"
        Write-Host "StartType: $($service.StartType)"

        # Stop the service if it's running
        if ($service.Status -eq 'Running') {
            Write-Host "Stopping the Mosquitto service..."
            Stop-Service -Name $service.Name -Force
            # Ensure the service has stopped
            $service.WaitForStatus('Stopped', '00:00:30')
        }

        # Remove the service
        Write-Host "Removing the Mosquitto service..."
        $deleteCmd = "sc.exe delete $($service.Name)"
        Invoke-Expression $deleteCmd

        Write-LogMessage "Mosquitto service removed successfully."
    } else {
        Write-LogMessage "Windows Service for Mosquitto is not installed or does not exist. Continuing."
    }
}

function Get-ProgramFilesPath {
    # Get the path to the Program Files directory
    $folderSpec = [System.Environment+SpecialFolder]::ProgramFiles
    return [System.Environment]::GetFolderPath($folderSpec)
}

function Test-ExecutablePath {
    param(
        [string]$Path
    )

    # Check if the path exists and is a file
    if (Test-Path $Path -PathType Leaf) {
        # Get the item and check if its extension is '.exe'
        $item = Get-Item $Path
        if ($item.Extension -eq '.exe') {
            return $true
        } else {
            Write-Debug "The path is not an executable file (.exe)."
            return $false
        }
    } else {
        Write-Debug "The path does not exist or is not a file."
        return $false
    }
}

function Get-Python311 {
    # Check if Python 3.11 is installed
    try {
        $PythonVersion = python --version 2>&1
        if ($PythonVersion -like "*Python 3.11*") {
            Write-LogMessage "Python 3.11 is already installed."
            return
        } else {
            Write-LogMessage "Python 3.11 is not installed. Current version: $PythonVersion"
        }
    } catch {
        Write-LogMessage "Python is not installed."
    }

    # Temporary target
    $installerPath = "$env:TEMP\python-3.11-installer.exe"

    # Download the installer
    Write-LogMessage "Downloading installer for Python 3.11..."
    Invoke-WebRequest -Uri $DepURLPython -OutFile $installerPath

    # Install Python 3.11
    Write-LogMessage "Installing Python 3.11..."
    Start-Process -FilePath $installerPath -Args "/quiet InstallAllUsers=1 PrependPath=1" -Wait -NoNewWindow

    # Cleanup the installer
    Remove-Item -Path $installerPath

    Write-LogMessage "Python 3.11 installation complete."
}

function Refresh-Path {
    $systemPath = [System.Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::Machine)
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::User)
    $combinedPath = $systemPath + ";" + $userPath

    # Remove duplicate entries to clean up the PATH
    $uniquePath = $combinedPath -split ';' | Select-Object -Unique | Where-Object { $_ -ne '' }

    [System.Environment]::SetEnvironmentVariable("Path", ($uniquePath -join ';'), [System.EnvironmentVariableTarget]::Process)
}

function Create-PythonEnvWithExecutable
{
    param(
        [string]$VirtualenvDir
    )

    try {
        New-Item -Path $VirtualenvDir -ItemType Directory -ErrorAction Stop | Out-Null
    } catch [System.IO.IOException] {
        # Do nothing if the error is due to the directory already existing
        if (Test-Path -Path $VirtualenvDir -PathType Container) {
            Write-LogMessage "Virtualenv folder already exists at $fullPath. Continuing."
        } else {
            Write-LogMessage "Unhandled Exception: $($_.Exception.Message)"
            # Re-throw the exception if it's not an expected type
            throw
        }
    }

    $activateScript = Join-Path -Path $VirtualenvDir -ChildPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript -PathType Leaf)
    {
        Write-Host "Skipped creation."
    }
    else
    {
        Write-Host "Virtual environment will be created in $VirtualenvDir"
        python -m venv $VirtualenvDir
        Write-Host "Virtual environment created."
    }
    # Activate the virtual environment
    . $activateScript

    # Update pip and Install the repo within the virtual environment
    python -m pip install --upgrade pip
    $repoPath = Get-RepoPathFromHere
    python -m pip install "$repoPath\wedge-cli"
    Write-LogMessage "Wedge CLI has been installed."

    Write-LogMessage "Virtual environment has been updated."
}

function Get-RepoPathFromHere {
    # Get the script's directory
    $parentOnce = Split-Path -Path $PSScriptRoot -Parent
    $parentTwice = Split-Path -Path $parentOnce -Parent

    return $parentTwice
}

function Get-FlatcBinary {
    param (
        [string]$ScriptsDir
    )

    $flatcPath = Join-Path -Path $ScriptsDir -ChildPath "flatc.exe"

    if (Test-Path $flatcPath -PathType Leaf) {
        Write-LogMessage "Flatc already installed at $ScriptsDir"
        return
    }

    # Download the zip file
    $zipPath = Join-Path -Path $env:TEMP -ChildPath "tempExecutable.zip"
    Invoke-WebRequest -Uri $DepURLFlatc -OutFile $zipPath
    Write-LogMessage "Flatc Zipball downloaded."

    # Unpack the zip file directly into the virtual environment's bin/ directory
    Expand-Archive -Path $zipPath -DestinationPath $ScriptsDir -Force
    Write-LogMessage "Flatc Executable unpacked into $ScriptsDir"

    # Cleanup the downloaded zip file
    Remove-Item -Path $zipPath
}

function Create-AppDataDirectory {
    param(
        [string]$DirectoryName
    )

    # Construct the full path to the new directory within APPDATA
    $fullPath = Join-Path -Path $env:APPDATA -ChildPath $DirectoryName

    # Check if the directory already exists
    if (Test-Path -Path $fullPath) {
        Write-LogMessage "Directory already exists: $fullPath"
    } else {
        # Attempt to create the directory
        try {
            New-Item -Path $fullPath -ItemType Directory | Out-Null
            Write-LogMessage "Directory created successfully: $fullPath"
        } catch {
            Write-LogMessage "Failed to create directory: $_"
        }
    }
    return $fullPath
}

function Get-Git {

    $GitExecPath = "$(Get-ProgramFilesPath)\Git\bin\git.exe"
    if (Test-ExecutablePath -Path $GitExecPath)
    {
        Write-LogMessage "Git is already installed."
        return
    }

    # Download the installer
    Write-LogMessage "Downloading Git installer..."

    # Temporary target
    $downloadPath = Join-Path -Path $env:TEMP -ChildPath "Git-Installer.exe"
    Invoke-WebRequest -Uri $DepURLGit -OutFile $downloadPath

    # Install silently
    Write-LogMessage "Installing Git..."
    Start-Process -FilePath $downloadPath -Args '/SILENT' -Wait -NoNewWindow

    # Cleanup
    Remove-Item -Path $downloadPath

    Write-LogMessage "Git installation complete."
}

function Create-DesktopShortcut {
    param(
        [string]$VirtualenvDir
    )

    $WshShell = New-Object -comObject WScript.Shell
    $DestinationPath = $WshShell.SpecialFolders("Desktop") + "\Wedge GUI.lnk"

    # If icon already exists, just remove it so that we make sure it is
    # kept up to date since recreating has zero cost.
    if (Test-Path $DestinationPath -PathType Leaf) {
        Remove-Item -Path $DestinationPath
    }

    $SourceExe = Join-Path -Path $VirtualenvDir -ChildPath "Scripts\python.exe"
    $Command = '-m wedge_cli gui'

    $Shortcut = $WshShell.CreateShortcut($DestinationPath)
    $Shortcut.TargetPath = $SourceExe
    $Shortcut.Arguments = $Command
    $Shortcut.WorkingDirectory = $HOME
    $Shortcut.Description = "Starts the GUI mode of the Wedge CLI"
    #$Shortcut.IconLocation = ""
    $Shortcut.Save()

    Write-Host "Created desktop shortcut at: $DestinationPath"
}

function Write-LogMessage {
    param(
        [string]$Message
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Write-Host $logMessage
}

Main
