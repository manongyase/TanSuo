# 手动执行方式：
#   1. 弹窗输入模式（运行后弹出窗口输入推送日志）：
#      powershell -ExecutionPolicy Bypass -File .\push.ps1
#   2. 参数模式（直接通过 -Log 传入推送日志）：
#      powershell -ExecutionPolicy Bypass -File .\push.ps1 -Log "这里写推送日志"
#   3. 默认模式（不弹窗，自动使用默认日志）：
#      powershell -ExecutionPolicy Bypass -File .\push.ps1 -Log ""

param(
    [string]$Log = ""
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Continue"

$RepoPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $RepoPath ".push-logs"
$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$TempLogFile = Join-Path $LogDir "push-$Timestamp.log"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$LogFile = $TempLogFile

function Show-InputBox {
    param(
        [string]$Prompt,
        [string]$Title,
        [string]$DefaultText = ""
    )
    Add-Type -AssemblyName Microsoft.VisualBasic
    return [Microsoft.VisualBasic.Interaction]::InputBox($Prompt, $Title, $DefaultText)
}

function Write-Log {
    param([string]$Msg)
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $Msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

Set-Location $RepoPath

Write-Host ""
Write-Host "========== TanSuo 仓库推送 ==========" -ForegroundColor Cyan
Write-Host ""

$changes = git status --porcelain 2>&1
if (-not $changes) {
    Write-Host "没有检测到任何改动，跳过推送。" -ForegroundColor Yellow
    exit 0
}

Write-Host "本次改动：" -ForegroundColor Cyan
foreach ($c in $changes) {
    Write-Host "  $c"
}
Write-Host ""

Write-Host "========== 文件详情 ==========" -ForegroundColor Cyan
$gitDiff = git diff HEAD 2>&1
if ($gitDiff) {
    Write-Host $gitDiff
} else {
    Write-Host "（无已跟踪文件的内容变更）" -ForegroundColor Gray
}
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

if ($PSBoundParameters.ContainsKey('Log')) {
    $userLog = $Log
} else {
    $logLines = $changes -join "`n"
    $promptText = "本次改动：`n$logLines`n`n请输入本次推送日志（留空则使用默认时间戳）："
    $result = Show-InputBox -Prompt $promptText -Title "TanSuo 仓库推送日志" -DefaultText ""
    if ($null -eq $result) {
        Write-Host "用户取消，已中止推送。" -ForegroundColor Yellow
        exit 0
    } elseif ([string]::IsNullOrWhiteSpace($result)) {
        $userLog = "更新于 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    } else {
        $userLog = $result
    }
}

if ([string]::IsNullOrWhiteSpace($userLog)) {
    $userLog = "更新于 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}
$commitMsg = "feat: " + $userLog

"" | Out-File -FilePath $LogFile -Encoding UTF8
Add-Content -Path $LogFile -Value "========================================" -Encoding UTF8
Add-Content -Path $LogFile -Value "  推送日志：$userLog" -Encoding UTF8
Add-Content -Path $LogFile -Value "  时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -Encoding UTF8
Add-Content -Path $LogFile -Value "========================================" -Encoding UTF8
Add-Content -Path $LogFile -Value "" -Encoding UTF8

Write-Host ""
Write-Host "推送日志：$userLog" -ForegroundColor Green
Write-Host ""

Write-Log "执行 git add ."
git add . 2>&1 | ForEach-Object { Write-Log "  $_" }

Write-Log "执行 git commit"
git commit -m $commitMsg 2>&1 | ForEach-Object { Write-Log "  $_" }

Write-Log "设置 sslVerify=false 并推送"
git config --global http.sslVerify false
$pushResult = git push -u origin master 2>&1
$pushExit = $LASTEXITCODE
git config --global http.sslVerify true

foreach ($line in $pushResult) {
    Write-Log "  $line"
}

if ($pushExit -eq 0) {
    Write-Log "推送成功！"
    Write-Host ""
    Write-Host "========== 推送成功 ==========" -ForegroundColor Green
    Write-Host "推送日志：$userLog" -ForegroundColor Green
    Write-Host ""
    Write-Host "日志文件：$LogFile" -ForegroundColor Gray
    $FinalLogFile = Join-Path $LogDir "push-$Timestamp-成功.log"
} else {
    Write-Log "推送失败！退出码: $pushExit"
    Write-Host ""
    Write-Host "========== 推送失败 ==========" -ForegroundColor Red
    Write-Host "推送日志：$userLog" -ForegroundColor Red
    Write-Host ""
    Write-Host "日志文件：$LogFile" -ForegroundColor Yellow
    $FinalLogFile = Join-Path $LogDir "push-$Timestamp-失败.log"
}

Write-Log "========== 推送结束 =========="

if ($TempLogFile -ne $FinalLogFile) {
    Move-Item -Path $TempLogFile -Destination $FinalLogFile -Force
}

exit $pushExit