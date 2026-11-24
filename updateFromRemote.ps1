#Requires -Version 5.1
# Discards local changes to tracked files and syncs with origin/master.
# Untracked/ignored files such as logs/ are not touched (no `git clean`).
param([switch]$Force)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $Force) {
    Write-Host "This overwrites all local changes to tracked files with origin/master."
    $answer = Read-Host "Continue? (y/N)"
    if ($answer -notmatch '^[yY]') { Write-Host "Aborted."; exit 1 }
}

git fetch origin master
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

git checkout master
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

git reset --hard origin/master
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Updated to origin/master. logs/ was left untouched."
