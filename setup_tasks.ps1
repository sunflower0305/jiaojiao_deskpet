# 注册角角桌宠的 Windows 定时任务
# 以管理员身份运行：Right-click → "以管理员身份运行"

$PythonPath = (Get-Command python).Source
$ScriptDir  = "D:\workplace\角角桌宠"

# ── 午饭触发器 ────────────────────────────────────────────────────────────────
# 每天 11:45 触发 eating 状态，持续 60 秒后自动恢复
$LunchAction  = New-ScheduledTaskAction -Execute $PythonPath `
                    -Argument "`"$ScriptDir\lunch_trigger.py`""
$LunchTrigger = New-ScheduledTaskTrigger -Daily -At "11:45"
$LunchSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
                    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName   "角角桌宠_午饭触发" `
    -Action     $LunchAction `
    -Trigger    $LunchTrigger `
    -Settings   $LunchSettings `
    -Description "每天 11:45 让角角进入吃饭状态，持续 60 秒后恢复" `
    -Force

Write-Host "✓ 午饭触发任务已注册（每天 11:45）"

Write-Host ""
Write-Host "报错情绪积累已通过 ~/.claude/settings.json hooks 配置，无需单独注册任务。"
Write-Host "连续 3 次 PostToolUseFailure 后，角角将维持 error 状态 15 秒。"
