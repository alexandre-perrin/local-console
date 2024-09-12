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
# - https://github.com/aaronparker/vcredist/blob/42581ac57edfd5347187b03168cfcc36119edff1/VcRedist/Public/Get-InstalledVcRedist.ps1
#
# SPDX-License-Identifier: Apache-2.0
function Get-InstalledVcRedist {
    <#
        .EXTERNALHELP VcRedist-help.xml
    #>
    [CmdletBinding(SupportsShouldProcess = $false, HelpURI = "https://vcredist.com/get-installedvcredist/")]
    [OutputType([System.Management.Automation.PSObject])]
    param (
        [Parameter(Mandatory = $false)]
        [System.Management.Automation.SwitchParameter] $ExportAll
    )

    if ($PSBoundParameters.ContainsKey("ExportAll")) {
        # If -ExportAll used, export everything instead of filtering for the primary Redistributable
        # Get all installed Visual C++ Redistributables installed components
        Write-Verbose -Message "-ExportAll specified. Exporting all install Visual C++ Redistributables and runtimes."
        $Filter = "(Microsoft Visual C.*).*"
    }
    else {
        $Filter = "(Microsoft Visual C.*)(\bRedistributable).*"
    }

    # Get all installed Visual C++ Redistributables installed components
    Write-Verbose -Message "Matching installed VcRedists with: '$Filter'."
    $VcRedists = Get-InstalledSoftware | Where-Object { $_.Name -match $Filter }

    # Add Architecture property to each entry
    Write-Verbose -Message "Add Architecture property to output object."
    $VcRedists | ForEach-Object { if ($_.Name -contains "x64") { $_ | Add-Member -NotePropertyName "Architecture" -NotePropertyValue "x64" } }

    # Write the installed VcRedists to the pipeline
    Write-Output -InputObject $VcRedists
}
