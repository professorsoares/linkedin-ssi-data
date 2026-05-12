# setup_task.ps1
# Registra o run_daily.bat no Agendador de Tarefas do Windows.
#
# Uso:
#   .\setup_task.ps1              # agenda para 09:00 (padrão)
#   .\setup_task.ps1 -At "08:30"  # agenda para outro horário
#   .\setup_task.ps1 -Remove      # remove a tarefa
#
# Deve ser executado uma única vez (como Administrador, se necessário).

param(
    [string] $At     = "08:00",
    [switch] $Remove
)

# ── Auto-elevação ─────────────────────────────────────────────────────────────
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
           ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    $argList = "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($At)     { $argList += " -At `"$At`"" }
    if ($Remove) { $argList += " -Remove" }
    Start-Process powershell -Verb RunAs -ArgumentList $argList
    exit
}

$TaskName  = "LinkedIn-SSI-Daily"
$TaskPath  = "\Bruno\"
$ScriptDir = $PSScriptRoot
$PythonExe = Join-Path $ScriptDir ".venvSSIData\Scripts\python.exe"
$Script    = Join-Path $ScriptDir "run_daily.py"

# ── Remover ───────────────────────────────────────────────────────────────────
if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Tarefa '$TaskName' removida."
    exit 0
}

# ── Validar ───────────────────────────────────────────────────────────────────
if (-not (Test-Path $PythonExe)) {
    Write-Error "Python do venv nao encontrado: $PythonExe"
    exit 1
}
if (-not (Test-Path $Script)) {
    Write-Error "Script nao encontrado: $Script"
    exit 1
}

# ── Criar tarefa ──────────────────────────────────────────────────────────────
$action = New-ScheduledTaskAction `
    -Execute          $PythonExe `
    -Argument         "`"$Script`"" `
    -WorkingDirectory $ScriptDir

$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At $At

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances  IgnoreNew `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName   $TaskName `
    -TaskPath   $TaskPath `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -RunLevel   Highest `
    -Force | Out-Null

Write-Host ""
Write-Host "Tarefa '$TaskName' registrada com sucesso."
Write-Host "  Pasta          : $TaskPath"
Write-Host "  Horario diario : $At"
Write-Host "  Python         : $PythonExe"
Write-Host "  Script         : $Script"
Write-Host "  Log            : $ScriptDir\logs\run_daily.log"
Write-Host ""

$info = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath | Get-ScheduledTaskInfo
Write-Host "Confirmacao:"
Write-Host "  Status         : $((Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath).State)"
Write-Host "  Proxima exec.  : $($info.NextRunTime)"
Write-Host ""
Write-Host "Outros comandos uteis:"
Write-Host "  Executar agora  : Start-ScheduledTask -TaskName '$TaskName' -TaskPath '$TaskPath'"
Write-Host "  Ver status      : Get-ScheduledTask -TaskName '$TaskName' -TaskPath '$TaskPath' | Get-ScheduledTaskInfo"
Write-Host "  Remover tarefa  : .\setup_task.ps1 -Remove"
