# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
$rootPath = Split-Path $MyInvocation.MyCommand.Path -parent
$utils = Join-Path -Path $rootPath -ChildPath "utils.ps1"
. $utils

function Main
{
    Set-TemporalExecutionPolicy

    Write-LogMessage "Uninstalling Local Console"

    # Construct the full path to the new directory within APPDATA
    $fullPath = $DefaultInstallPath
    if (Test-Path -Path $fullPath)
    {
        Write-LogMessage "Removing program files"
        Remove-Item -Path $fullPath -Recurse -Force
    }

    $WshShell = New-Object -comObject WScript.Shell
    $IconPath = Join-Path -Path $WshShell.SpecialFolders("Desktop") -ChildPath "Local Console.lnk"
    if (Test-Path -Path $IconPath)
    {
        Write-LogMessage "Removing desktop shortcut"
        Remove-Item -Path $IconPath -Force
    }

    Write-LogMessage "Removing configuration directory"
    $ConfigPath = Join-Path $env:APPDATA -ChildPath "local-console"
    Remove-Item -Path $ConfigPath -Recurse -Force

    Restore-DefaultExecutionPolicy
    Wait-UserInput
}

Main
