# Alternative management of the Wedge CLI+GUI for Windows

Follow this procedure in case your Windows installation rejects the executable installer (e.g. Windows Defender throws a virus false-positive or unsigned installers are disallowed).

## Installing

Prior to starting, make sure you have either cloned the [wedge-cli repository](https://github.com/midokura/wedge-cli) or you have unpacked a source tarball into your machine. We shall refer to its location at `$wedge-cli_repository_root`. Now, open a PowerShell window at that location and proceed with the steps below:

1. First, set the shell at the location of this README, and allow execution of the helper script for this step:
```powershell
> cd $wedge-cli_repository_root\wedge-cli\windows
> Unblock-File -Path .\wedge_install.ps1
```

2. Then, enable executing local scripts only for the current shell. You may be asked to confirm the action.
```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

Execution Policy Change
The execution policy helps protect you from scripts that you do not trust. Changing the execution policy might expose
you to the security risks described in the about_Execution_Policies help topic at
https:/go.microsoft.com/fwlink/?LinkID=135170. Do you want to change the execution policy?
[Y] Yes  [A] Yes to All  [N] No  [L] No to All  [S] Suspend  [?] Help (default is "N"): Y
```

2. Execute the installer script. It will download all prerequisites, install them, and then install the CLI+GUI from the repository root.
```powershell
> .\wedge_install.ps1

> .\wedge_install.ps1
[2024-04-02 09:31:58] Downloading installer for the Mosquitto MQTT broker...
[2024-04-02 09:32:00] Installing the Mosquitto MQTT broker...
[2024-04-02 09:32:04] Mosquitto installation complete.
[2024-04-02 09:32:04] Found Windows Service for Mosquitto. Preparing to remove...
DisplayName: Mosquitto Broker
Status: Stopped
ServiceName: mosquitto
StartType: Automatic
Removing the Mosquitto service...
[SC] DeleteService SUCCESS
[2024-04-02 09:32:04] Mosquitto service removed successfully.
[2024-04-02 09:32:04] Downloading Git installer...
[2024-04-02 09:34:14] Installing Git...
[2024-04-02 09:35:25] Git installation complete.
[2024-04-02 09:35:25] Python is not installed.
[2024-04-02 09:35:25] Downloading installer for Python 3.11...
[2024-04-02 09:36:11] Installing Python 3.11...
[2024-04-02 09:36:55] Python 3.11 installation complete.
[2024-04-02 09:36:55] Directory created successfully: C:\Users\User\AppData\Roaming\WedgeCLI
Virtual environment will be created in C:\Users\User\AppData\Roaming\WedgeCLI\virtualenv
Virtual environment created.
Requirement already satisfied: pip in c:\users\user\appdata\roaming\wedgecli\virtualenv\lib\site-packages (24.0)
Processing z:\wedge-cli
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... done
  ...
  ...
Successfully built wedge-cli paho-mqtt kivymd
Installing collected packages: types-retry...
Successfully installed Kivy-2.3.0 ... wedge-cli-1.6.7 ...
[2024-04-02 09:38:47] Wedge CLI has been installed.
[2024-04-02 09:38:47] Virtual environment has been updated.
[2024-04-02 09:38:50] Flatc Zipball downloaded.
[2024-04-02 09:38:51] Flatc Executable unpacked into C:\Users\User\AppData\Roaming\WedgeCLI\virtualenv\Scripts
Created desktop shortcut at: C:\Users\User\Desktop\Wedge GUI.lnk
```

3. The script created a shortcut icon at your Windows desktop. Please click on it, and if asked allow network connections through the Windows firewall. You are now ready to use the GUI.
