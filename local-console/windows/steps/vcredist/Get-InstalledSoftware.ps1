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
# This file incorporates material licensed under the MIT License:
#
#     MIT License
#
#     Copyright (c) 2017 Aaron Parker
#
#     Permission is hereby granted, free of charge, to any person obtaining a copy
#     of this software and associated documentation files (the "Software"), to deal
#     in the Software without restriction, including without limitation the rights
#     to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#     copies of the Software, and to permit persons to whom the Software is
#     furnished to do so, subject to the following conditions:
#
#     The above copyright notice and this permission notice shall be included in all
#     copies or substantial portions of the Software.
#
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#     IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#     FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#     AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#     LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#     OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#     SOFTWARE.
#
# Original file:
# - https://github.com/aaronparker/vcredist/blob/42581ac57edfd5347187b03168cfcc36119edff1/VcRedist/Private/Get-InstalledSoftware.ps1
#
# SPDX-License-Identifier: Apache-2.0
function Get-InstalledSoftware {
    <#
        .SYNOPSIS
            Retrieves a list of all software installed

        .EXAMPLE
            Get-InstalledSoftware

            This example retrieves all software installed on the local computer

        .PARAMETER Name
            The software title you"d like to limit the query to.

        .NOTES
            Author: Adam Bertram
            URL: https://4sysops.com/archives/find-the-product-guid-of-installed-software-with-powershell/
    #>
    [CmdletBinding(SupportsShouldProcess = $false)]
    [OutputType([System.Management.Automation.PSObject])]
    param (
        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [System.String] $Name
    )

    process {
        $UninstallKeys = "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        $null = New-PSDrive -Name "HKU" -PSProvider "Registry" -Root "Registry::HKEY_USERS"

        $UninstallKeys += Get-ChildItem -Path "HKU:" -ErrorAction "SilentlyContinue" | `
            Where-Object { $_.Name -match "S-\d-\d+-(\d+-){1,14}\d+$" } | `
            ForEach-Object { "HKU:\$($_.PSChildName)\Software\Microsoft\Windows\CurrentVersion\Uninstall" }

        foreach ($UninstallKey in $UninstallKeys) {
            if ($PSBoundParameters.ContainsKey("Name")) {
                $WhereBlock = { ($_.PSChildName -match "^{[A-Z0-9]{8}-([A-Z0-9]{4}-){3}[A-Z0-9]{12}}$") -and ($_.GetValue("DisplayName") -like "$Name*") }
            }
            else {
                $WhereBlock = { ($_.PSChildName -match "^{[A-Z0-9]{8}-([A-Z0-9]{4}-){3}[A-Z0-9]{12}}$") -and ($_.GetValue("DisplayName")) }
            }

            $SelectProperties = @(
                @{n = "Publisher"; e = { $_.GetValue("Publisher") } },
                @{n = "Name"; e = { $_.GetValue("DisplayName") } },
                @{n = "Version"; e = { $_.GetValue("DisplayVersion") } },
                @{n = "ProductCode"; e = { $_.PSChildName } },
                @{n = "BundleCachePath"; e = { $_.GetValue("BundleCachePath") } },
                @{n = "Architecture"; e = { if ($_.GetValue("DisplayName") -like "*x64*") { "x64" } else { "x86" } } },
                @{n = "Release"; e = { if ($_.GetValue("DisplayName") -match [RegEx]"(\d{4})\s+") { $matches[0].Trim(" ") } } },
                @{n = "UninstallString"; e = { $_.GetValue("UninstallString") } },
                @{n = "QuietUninstallString"; e = { $_.GetValue("QuietUninstallString") } },
                @{n = "UninstallKey"; e = { $UninstallKey } }
            )

            $params = @{
                Path        = $UninstallKey
                ErrorAction = "SilentlyContinue"
            }
            Get-ChildItem @params | Where-Object $WhereBlock | Select-Object -Property $SelectProperties
        }
    }

    end {
        Remove-PSDrive -Name "HKU" -ErrorAction "SilentlyContinue"
    }
}
