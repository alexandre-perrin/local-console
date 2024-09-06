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
