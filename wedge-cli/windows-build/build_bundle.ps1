# Define the relative path to the virtual environment from the script's location
$RelativeVenvPath = ".\venv"

# Construct the absolute path to the virtual environment
$VenvPath = Join-Path -Path $PSScriptRoot -ChildPath $RelativeVenvPath
$ActivateScriptPath = Join-Path -Path $VenvPath -ChildPath "Scripts\Activate.ps1"
$WedgeCLIRootPath = Join-Path -Path $PSScriptRoot -ChildPath "..\..\wedge-cli" | Resolve-Path | select -ExpandProperty Path

# Check if the virtual environment exists; if not, create it and install dependencies
if (-not (Test-Path $VenvPath)) {
    Write-Host "Virtual environment not found. Creating one at $VenvPath..."
    python -m venv $VenvPath

    # Install required packages using pip
    . $ActivateScriptPath

    pip install $WedgeCLIRootPath
    pip install pyinstaller
}
else {
    # Activate the virtual environment
    . $ActivateScriptPath
}

# Change the CWD to the PyInstaller spec dir
Set-Location -Path $WedgeCLIRootPath

# Run the PyInstaller build
$CommandToRun = "pyinstaller --clean --noconfirm .\pyinstaller.spec"
Invoke-Expression $CommandToRun
