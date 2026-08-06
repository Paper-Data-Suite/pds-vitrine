param(
    [Parameter(Mandatory = $true)]
    [string]$CoreWheel,
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"
$arguments = @(
    "scripts/validate_repository.py",
    "--core-wheel",
    $CoreWheel
)
if ($AllowDirty) {
    $arguments += "--allow-dirty"
}
python @arguments
exit $LASTEXITCODE
