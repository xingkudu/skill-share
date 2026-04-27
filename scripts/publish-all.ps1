<#
.SYNOPSIS
    一键发布全部 Primark skill 到 ClawHub (Windows PowerShell 版)。

.EXAMPLE
    .\scripts\publish-all.ps1 -Version 1.0.0 -Changelog "Initial release"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $Version,
    [Parameter(Mandatory)] [string] $Changelog
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command clawhub -ErrorAction SilentlyContinue)) {
    Write-Error "找不到 clawhub CLI。先装一下: npm i -g clawhub"
    exit 1
}

# 登录态检查
$null = clawhub whoami 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "未登录 ClawHub。先跑: clawhub login"
    exit 1
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $RepoRoot

$Skills = @(
    @{ Slug='primark-purchase-order';   Name='Primark Purchase Order Generator'; Tags='textile,primark,purchase-order,label,fashion-supply-chain,chinese,latest' }
    @{ Slug='primark-ticket-check';     Name='Primark Ticket Check';             Tags='textile,primark,ticket-check,qa,label,fashion-supply-chain,chinese,latest' }
    @{ Slug='primark-care-label-check'; Name='Primark Care Label Check';         Tags='textile,primark,care-label,qa,multilingual,fashion-supply-chain,chinese,latest' }
)

Write-Host "🚀 准备发布 $($Skills.Count) 个 skill (version=$Version) → ClawHub`n"

foreach ($s in $Skills) {
    Write-Host "── $($s.Slug) ──"
    if (-not (Test-Path $s.Slug)) {
        Write-Warning "  ⚠️  目录不存在，跳过: $($s.Slug)"
        continue
    }
    & clawhub skill publish ".\$($s.Slug)" `
        --slug $s.Slug `
        --name $s.Name `
        --version $Version `
        --changelog $Changelog `
        --tags $s.Tags
    if ($LASTEXITCODE -ne 0) { throw "发布 $($s.Slug) 失败" }
    Write-Host "  ✅ $($s.Slug) @ $Version 已上架`n"
}

Write-Host "🎉 全部完成。查看: https://clawhub.ai/skills?q=primark"
