# Restore inherited access only on workspace ACLs matching Python's creator-only directories.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string[]]$WorkspaceRoots,
    [Parameter(Mandatory=$true)][string]$BackupFile,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$snapshots = [System.Collections.Generic.List[object]]::new()
$targets = [System.Collections.Generic.List[string]]::new()
$roots = @($WorkspaceRoots | ForEach-Object { (Get-Item -LiteralPath $_ -Force).FullName })
foreach ($root in $roots) {
    if (-not (Test-Path -LiteralPath (Join-Path $root '.authoring-workspace.json') -PathType Leaf)) {
        throw "Not an authoring workspace: $root"
    }
    $queue = [System.Collections.Generic.Queue[string]]::new()
    $queue.Enqueue($root)
    while ($queue.Count -gt 0) {
        $current = $queue.Dequeue()
        $item = Get-Item -LiteralPath $current -Force
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { continue }
        $resolved = $item.FullName
        if ($resolved -ne $root -and -not $resolved.StartsWith($root.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) {
            throw "Path escaped workspace: $resolved"
        }
        $acl = Get-Acl -LiteralPath $resolved
        $snapshots.Add([pscustomobject]@{Path=$resolved;Sddl=$acl.Sddl})
        $hasCreatorRule = $false
        $hasDeny = $false
        foreach ($rule in $acl.Access) {
            $sid = $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
            if ($sid -eq 'S-1-3-4') { $hasCreatorRule=$true }
            if ($rule.AccessControlType -eq [Security.AccessControl.AccessControlType]::Deny) { $hasDeny=$true }
        }
        if ($acl.AreAccessRulesProtected -and $hasCreatorRule -and -not $hasDeny) { $targets.Add($resolved) }
        if ($item.PSIsContainer) {
            foreach ($child in Get-ChildItem -LiteralPath $resolved -Force) { $queue.Enqueue($child.FullName) }
        }
    }
}
$backup = [IO.Path]::GetFullPath($BackupFile)
if (Test-Path -LiteralPath $backup) { throw "Backup already exists: $backup" }
$body = [pscustomobject]@{SchemaVersion=1;Roots=$roots;Targets=@($targets);Entries=@($snapshots)} | ConvertTo-Json -Depth 5
$stream = [IO.File]::Open($backup,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes($body)
    $stream.Write($bytes,0,$bytes.Length)
} finally { $stream.Dispose() }
$changed = 0
if ($Apply) {
    # Parents first, so children can inherit restored access. Explicit rules are retained.
    foreach ($target in $targets) {
        # Change inheritance only; keep owner, audit metadata and explicit access rules.
        & icacls.exe $target /inheritance:e | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not enable inheritance: $target" }
        if ((Get-Acl -LiteralPath $target).AreAccessRulesProtected) { throw "Inheritance still disabled: $target" }
        $changed++
    }
}
[pscustomobject]@{Inspected=$snapshots.Count;Matched=$targets.Count;Changed=$changed;Backup=$backup} | ConvertTo-Json -Compress
