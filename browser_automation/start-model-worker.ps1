param(
    [ValidateSet('Worker','Display','RegisterWindow','SelfTest')][string]$Mode = 'Worker',
    [string]$SshTarget = 'aliyun-dev',
    [ValidateSet('gpt','claude')][string]$Role = 'claude',
    [string]$SessionId = '',
    [int]$DisplayOwnerProcessId = 0
)
$ErrorActionPreference = 'Stop'
$workerRoot = Join-Path $env:LOCALAPPDATA 'LLM-Authoring-Automation'
$workerJobsRoot = Join-Path $workerRoot 'jobs'
$workerServerRoot = '/srv/llm-authoring-staging/20261025-browser-workflow-design/integration'
$workerGptSession = '01a16f20-a0cf-79a2-bd0a-048a3d72824a'
$workerGptJobs = @{}
$workerUtf8 = New-Object System.Text.UTF8Encoding($false)
function Write-WorkerJson($Path, $Value) {
    [IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 25 -Compress), $workerUtf8)
}
function Assert-WorkerId([string]$Value) {
    if ($Value -notmatch '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$') { throw 'A UUID is required.' }
}
function Quote-WorkerArg([string]$Value) {
    if ($Value.Length -eq 0) { return '""' }
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}
function Assert-WorkerRequest($Request) {
    if (-not $Request) { throw 'Missing request.' }
    Assert-WorkerId ([string]$Request.id)
    $allowed = @('capabilities','claude_start','status','display','capture','gpt_register','navigate','stop')
    if ([string]$Request.action -notin $allowed) { throw 'Unsupported operation.' }
    $extra = @($Request.PSObject.Properties.Name | Where-Object { $_ -notin @('id','action','job_id','role','prompt','session_id','prompt_sha256','navigation') })
    if ($extra.Count -gt 0) { throw 'Unknown request fields are not accepted.' }
    if ($Request.action -in @('status','display','capture','navigate')) { Assert-WorkerId ([string]$Request.job_id) }
    if ($Request.action -eq 'gpt_register') {
        Assert-WorkerId ([string]$Request.session_id)
        if ([string]$Request.prompt_sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Prompt SHA256 required.' }
    }
    if ($Request.action -eq 'navigate' -and $Request.navigation -notin @('open_transcript','page_up','page_down')) { throw 'Unsupported display navigation.' }
    if ($Request.action -eq 'claude_start') {
        if (-not ($Request.prompt -is [string]) -or $Request.prompt.Length -lt 1 -or $Request.prompt.Length -gt 20000) { throw 'Prompt length is invalid.' }
    }
    if ($Request.action -eq 'display') {
        if ($Request.role -notin @('claude','gpt')) { throw 'Unknown client role.' }
        Assert-WorkerId ([string]$Request.session_id)
    }
}
function Find-WorkerClaude {
    $extensionRoot = Join-Path $env:USERPROFILE '.vscode\extensions'
    $candidate = @(Get-ChildItem -LiteralPath $extensionRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like 'anthropic.claude-code-*-win32-x64' } |
        Sort-Object { try { [version](($_.Name -replace '^anthropic.claude-code-','') -replace '-win32-x64$','') } catch { [version]'0.0' } } -Descending |
        ForEach-Object { Join-Path $_.FullName 'resources\native-binary\claude.exe' } |
        Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
    if ($candidate.Count -gt 0) { return $candidate[0] }
    $command = Get-Command claude.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) { return $command.Source }
    throw 'Native Claude Code executable was not found.'
}
function Test-WorkerPolicy {
    $passed = 0
    if ((Quote-WorkerArg '') -ne '""') { throw 'Empty argument quoting failed.' }; $passed++
    if ((Quote-WorkerArg 'a b') -ne '"a b"') { throw 'Space quoting failed.' }; $passed++
    if ((Quote-WorkerArg 'a"b') -ne '"a\"b"') { throw 'Quote escaping failed.' }; $passed++
    if ((Quote-WorkerArg 'C:\x\') -ne '"C:\x\\"') { throw 'Trailing slash escaping failed.' }; $passed++
    $good = [pscustomobject]@{ id='00000000-0000-4000-8000-000000000001'; action='claude_start'; prompt='test' }
    Assert-WorkerRequest $good; $passed++
    foreach ($bad in @(
        [pscustomobject]@{ id='bad; whoami'; action='capabilities' },
        [pscustomobject]@{ id=$good.id; action='exec'; command='whoami' },
        [pscustomobject]@{ id=$good.id; action='claude_start'; prompt='' },
        [pscustomobject]@{ id=$good.id; action='capabilities'; path='C:\secret' },
        [pscustomobject]@{ id=$good.id; action='capture'; job_id='..\..' }
    )) {
        $rejected = $false
        try { Assert-WorkerRequest $bad } catch { $rejected = $true }
        if (-not $rejected) { throw 'A forbidden request was accepted.' }; $passed++
    }
    Assert-WorkerRequest ([pscustomobject]@{id=$good.id;action='gpt_register';session_id=$good.id;prompt_sha256=('a'*64)});$passed++
    Assert-WorkerRequest ([pscustomobject]@{id=$good.id;action='navigate';job_id=$good.id;navigation='page_down'});$passed++
    foreach($bad in @(
        [pscustomobject]@{id=$good.id;action='gpt_register';session_id='bad';prompt_sha256=('a'*64)},
        [pscustomobject]@{id=$good.id;action='gpt_register';session_id=$good.id;prompt_sha256='not-a-hash'},
        [pscustomobject]@{id=$good.id;action='navigate';job_id=$good.id;navigation='ENTER'},
        [pscustomobject]@{id=$good.id;action='navigate';job_id='..\..';navigation='page_up'},
        [pscustomobject]@{id=$good.id;action='gpt_register';session_id=$good.id;prompt_sha256=('a'*64);command='whoami'}
    )){
        $rejected=$false;try{Assert-WorkerRequest $bad}catch{$rejected=$true}
        if(-not $rejected){throw 'A forbidden client operation was accepted.'};$passed++
    }
    return $passed
}
$workerPolicyTests = Test-WorkerPolicy
if ($Mode -eq 'SelfTest') { Write-Output ('Policy tests passed: ' + $workerPolicyTests); return }
if ([string]::IsNullOrWhiteSpace($SshTarget) -or $SshTarget.StartsWith('-') -or $SshTarget -match '\s') { throw 'Invalid SSH target.' }
New-Item -ItemType Directory -Path $workerJobsRoot -Force | Out-Null
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ModelWorkerWindow {
 [StructLayout(LayoutKind.Sequential)] public struct RECT {public int Left; public int Top; public int Right; public int Bottom;}
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int command);
 [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr hWnd);
 [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr value);
 [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
}
'@
[void][ModelWorkerWindow]::SetProcessDpiAwarenessContext([IntPtr](-4))
if ($Mode -eq 'RegisterWindow') {
    Assert-WorkerId $SessionId
    if($DisplayOwnerProcessId -le 0){throw 'A display owner is required.'}
    $registeredDirectory=Join-Path $workerJobsRoot $SessionId
    if(-not(Test-Path -LiteralPath $registeredDirectory -PathType Container)){throw 'Unknown display directory.'}
    Write-WorkerJson (Join-Path $registeredDirectory ('window-'+$Role+'.json')) @{
        window_handle=[ModelWorkerWindow]::GetConsoleWindow().ToInt64();process_id=$DisplayOwnerProcessId;
        registration_process_id=$PID;role=$Role;session_id=$SessionId;host='cmd.exe'
    }
    return
}
if ($Mode -eq 'Display') {
    Assert-WorkerId $SessionId
    $displayDirectory = Join-Path $workerJobsRoot $SessionId
    New-Item -ItemType Directory -Path $displayDirectory -Force | Out-Null
    $clientWorkingDirectory=$displayDirectory
    $registerArguments=@('-NoProfile','-File',$PSCommandPath,'-Mode','RegisterWindow','-Role',$Role,'-SessionId',$SessionId,'-DisplayOwnerProcessId',([string]$PID))
    $registerCommand='powershell.exe '+(($registerArguments|ForEach-Object{Quote-WorkerArg $_}) -join ' ')
    if ($Role -eq 'claude') {
        $nativeClaude = Find-WorkerClaude
        $workingFile=Join-Path $displayDirectory 'client-working-directory.json'
        if(Test-Path -LiteralPath $workingFile -PathType Leaf){
            $working=Get-Content -LiteralPath $workingFile -Raw -Encoding UTF8|ConvertFrom-Json
            if($working.kind -eq 'clean_shared'){$clientWorkingDirectory=Join-Path $workerRoot 'claude-clean'}
        }
        $clientCommand='"'+$nativeClaude+'" --safe-mode --resume '+$SessionId+' --model claude-opus-4-6 --effort high --tools ""'
    } else {
        if($SessionId -eq $workerGptSession) {
            $clientCommand='ssh.exe -tt "'+$SshTarget+'" /srv/llm-authoring-staging/20261025-browser-workflow-design/integration/gpt-smoke-002/show-session.sh'
        } else {
            $gptRegistration=Join-Path $displayDirectory 'gpt-registration.json'
            if(-not(Test-Path -LiteralPath $gptRegistration -PathType Leaf)){throw 'Unknown GPT display registration.'}
            $gptRecord=Get-Content -LiteralPath $gptRegistration -Raw -Encoding UTF8|ConvertFrom-Json
            if($gptRecord.session_id -ne $SessionId -or $gptRecord.model -ne 'gpt-5.6-sol' -or $gptRecord.effort -ne 'high'){throw 'GPT display registration mismatch.'}
            $clientCommand='ssh.exe -tt "'+$SshTarget+'" /srv/llm-authoring-staging/20261025-browser-workflow-design/workflow/browser_automation/show-gpt-session.py '+$SessionId
        }
    }
    $batchPath=Join-Path $displayDirectory ('show-'+$Role+'.cmd')
    $batchLines=@('@echo off','chcp 65001 >nul',('title LLM-Authoring-'+$Role+'-'+$SessionId),$registerCommand,'color 07','cls',('cd /d "'+$clientWorkingDirectory+'"'),$clientCommand)
    [IO.File]::WriteAllText($batchPath,($batchLines -join "`r`n")+"`r`n",$workerUtf8)
    $cmdProcess=Start-Process -FilePath 'cmd.exe' -ArgumentList ('/D /Q /T:07 /C ""'+$batchPath+'""') -PassThru
    # The parent worker tracks this bootstrap. RegisterWindow supplies its real CMD child window.
    $registrationPath=Join-Path $displayDirectory ('window-'+$Role+'.json')
    for($registrationAttempt=0;$registrationAttempt -lt 100 -and -not $cmdProcess.HasExited;$registrationAttempt++){
        try{$registered=Get-Content -LiteralPath $registrationPath -Raw -Encoding UTF8|ConvertFrom-Json;if($registered.process_id -eq $PID -and $registered.host -eq 'cmd.exe'){[void][ModelWorkerWindow]::ShowWindow([IntPtr]([long]$registered.window_handle),3);[void][ModelWorkerWindow]::ShowWindow([ModelWorkerWindow]::GetConsoleWindow(),0);break}}catch{}
        Start-Sleep -Milliseconds 100
    }
    $cmdProcess.WaitForExit()
    return
}

Write-Host 'Preparing the local model worker. No model prompt has been sent by this script.'
$workerClaude = Find-WorkerClaude
$workerVersion = (& $workerClaude --version | Out-String).Trim()
$workerHelp = (& $workerClaude --help | Out-String)
$workerSafeMode = $workerHelp.Contains('--safe-mode')
$workerModelJobs = @{}
$workerDisplays = @{}
$workerRequestCache = @{}
# Restore completed original results only. An interrupted/incomplete result is never rerun.
foreach ($savedDirectory in @(Get-ChildItem -LiteralPath $workerJobsRoot -Directory -ErrorAction SilentlyContinue)) {
    if($savedDirectory.Name -notmatch '^[0-9a-fA-F-]{36}$' -or ($savedDirectory.Attributes -band [IO.FileAttributes]::ReparsePoint)){continue}
    $savedId=$savedDirectory.Name
    try{Assert-WorkerId $savedId}catch{continue}
    $gptFile=Join-Path $savedDirectory.FullName 'gpt-registration.json'
    if(Test-Path -LiteralPath $gptFile -PathType Leaf){
        try{
            $record=Get-Content -LiteralPath $gptFile -Raw -Encoding UTF8|ConvertFrom-Json
            if($record.session_id -eq $savedId -and $record.model -eq 'gpt-5.6-sol' -and $record.effort -eq 'high' -and $record.prompt_sha256 -cmatch '^[a-f0-9]{64}$'){$workerGptJobs[$savedId]=$record}
        }catch{}
    }
    $savedStatus=Join-Path $savedDirectory.FullName 'status.json'
    if(-not(Test-Path -LiteralPath $savedStatus -PathType Leaf)){continue}
    try{
        $record=Get-Content -LiteralPath $savedStatus -Raw -Encoding UTF8|ConvertFrom-Json
        $raw=Get-Content -LiteralPath (Join-Path $savedDirectory.FullName 'stdout.json') -Raw -Encoding UTF8|ConvertFrom-Json
        $reply=[IO.File]::ReadAllText((Join-Path $savedDirectory.FullName 'reply.md'),$workerUtf8)
        if($record.state -eq 'completed' -and $record.exit_code -eq 0 -and $record.session_id -eq $savedId -and $record.returned_session_id -eq $savedId -and
           $raw.session_id -eq $savedId -and $raw.is_error -eq $false -and $raw.result -ceq $reply -and
           @($raw.modelUsage.PSObject.Properties.Name) -contains 'claude-opus-4-6'){
            $workerModelJobs[$savedId]=@{id=$savedId;directory=$savedDirectory.FullName;state='completed';returned_session_id=$savedId;restored=$true}
        }
    }catch{}
}
function Update-WorkerJobs {
    foreach ($job in @($workerModelJobs.Values)) {
        if ($job.state -ne 'running') { continue }
        $job.process.Refresh()
        if (-not $job.process.HasExited) { continue }
        $job.exit_code = $job.process.ExitCode
        $job.state = 'failed'
        try {
            $result = Get-Content -LiteralPath (Join-Path $job.directory 'stdout.json') -Encoding UTF8 -Raw | ConvertFrom-Json
            if ($job.exit_code -eq 0 -and -not $result.is_error -and $result.result -is [string] -and $result.result.Length -gt 0) {
                $job.state = 'completed'
                $job.result = $result.result
                $job.returned_session_id = $result.session_id
                $job.model_usage = $result.modelUsage
                [IO.File]::WriteAllText((Join-Path $job.directory 'reply.md'), $result.result, $workerUtf8)
            } else { $job.error = [string]$result.result }
        } catch { $job.error = 'The client did not return a complete JSON result.' }
        $job.completed_at_utc = [DateTime]::UtcNow.ToString('o')
        Write-WorkerJson (Join-Path $job.directory 'status.json') @{
            state=$job.state; exit_code=$job.exit_code; session_id=$job.id; returned_session_id=$job.returned_session_id;
            requested_model='claude-opus-4-6'; requested_effort='high'; tools_disabled=$true; result=$job.result;
            error=$job.error; model_usage=$job.model_usage; completed_at_utc=$job.completed_at_utc
        }
    }
}
function Invoke-WorkerRequest($Request) {
    Assert-WorkerRequest $Request
    Update-WorkerJobs
    switch ($Request.action) {
        'capabilities' {
            return @{ client='native_claude_code'; executable=$workerClaude; version=$workerVersion;
                safe_mode_supported=$workerSafeMode; effort_flag_supported=$workerHelp.Contains('--effort');
                policy_tests_passed=$workerPolicyTests; desktop_capture_available=[Environment]::UserInteractive;
                arbitrary_shell_supported=$false; credentials_returned=$false; worker_protocol=2;
                registered_gpt_display_supported=$true; bounded_transcript_navigation_supported=$true;
                restored_completed_jobs=@($workerModelJobs.Keys).Count }
        }
        'claude_start' {
            if (-not $workerSafeMode) { throw 'This client lacks safe mode; it will not be run with unverified custom instructions.' }
            if (@($workerModelJobs.Values | Where-Object { $_.state -eq 'running' }).Count -gt 0) { throw 'A model request is already running.' }
            $id = [string]$Request.id
            $directory = Join-Path $workerJobsRoot $id
            if (Test-Path -LiteralPath $directory) {
                $oldPrompt=Join-Path $directory 'prompt.md'
                if($workerModelJobs.ContainsKey($id) -and (Test-Path -LiteralPath $oldPrompt -PathType Leaf) -and [IO.File]::ReadAllText($oldPrompt,$workerUtf8) -ceq $Request.prompt){return @{job_id=$id;state=$workerModelJobs[$id].state;restored=$true}}
                throw 'Existing job is incomplete or different; preserve it, inspect status, do not repeat.'
            }
            New-Item -ItemType Directory -Path $directory | Out-Null
            $cleanDirectory=Join-Path $workerRoot 'claude-clean'
            New-Item -ItemType Directory -Path $cleanDirectory -Force|Out-Null
            $cleanInfo=Get-Item -LiteralPath $cleanDirectory
            if(($cleanInfo.Attributes -band [IO.FileAttributes]::ReparsePoint) -or @(Get-ChildItem -LiteralPath $cleanDirectory -Force).Count -gt 0){throw 'The dedicated Claude working directory must be empty and ordinary.'}
            Write-WorkerJson (Join-Path $directory 'client-working-directory.json') @{kind='clean_shared'}
            $inputPath = Join-Path $directory 'prompt.md'
            [IO.File]::WriteAllText($inputPath, $Request.prompt, $workerUtf8)
            $arguments = @('--safe-mode','--model','claude-opus-4-6','--effort','high','--tools','','--session-id',$id,'--output-format','json','-p')
            $argumentString = ($arguments | ForEach-Object { Quote-WorkerArg $_ }) -join ' '
            $process = Start-Process -FilePath $workerClaude -ArgumentList $argumentString -WorkingDirectory $cleanDirectory -PassThru `
                -RedirectStandardInput $inputPath -RedirectStandardOutput (Join-Path $directory 'stdout.json') -RedirectStandardError (Join-Path $directory 'stderr.log')
            $process.Handle | Out-Null
            $workerModelJobs[$id] = @{ id=$id; directory=$directory; process=$process; state='running'; requested_effort='high'; requested_model='claude-opus-4-6' }
            return @{ job_id=$id; state='running'; model='claude-opus-4-6'; effort='high'; local_working_directory=$cleanDirectory }
        }
        'status' {
            $id = [string]$Request.job_id
            if (-not $workerModelJobs.ContainsKey($id)) {
                if(Test-Path -LiteralPath (Join-Path $workerJobsRoot $id) -PathType Container){return @{job_id=$id;state='unconfirmed';next='Existing local evidence was preserved; reconcile it before any new generation.'}}
                throw 'Unknown worker-owned model job.'
            }
            $job=$workerModelJobs[$id]
            if ($job.state -eq 'running') { return @{job_id=$id; state='running'} }
            $record=Get-Content -LiteralPath (Join-Path $job.directory 'status.json') -Raw -Encoding UTF8 | ConvertFrom-Json
            if($record.state -eq 'completed'){
                $record|Add-Member -NotePropertyName 'original_stdout_base64' -NotePropertyValue ([Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $job.directory 'stdout.json')))) -Force
            }
            return $record
        }
        'gpt_register' {
            $session=[string]$Request.session_id
            $registration=@{schema_version=1;session_id=$session;model='gpt-5.6-sol';effort='high';prompt_sha256=[string]$Request.prompt_sha256;source='server_official_codex_registration'}
            $directory=Join-Path $workerJobsRoot $session
            New-Item -ItemType Directory -Path $directory -Force|Out-Null
            $file=Join-Path $directory 'gpt-registration.json'
            if(Test-Path -LiteralPath $file){
                $old=Get-Content -LiteralPath $file -Raw -Encoding UTF8|ConvertFrom-Json
                if($old.session_id -ne $session -or $old.prompt_sha256 -cne $registration.prompt_sha256){throw 'Existing GPT registration differs.'}
            }else{Write-WorkerJson $file $registration}
            $workerGptJobs[$session]=$registration
            return @{session_id=$session;state='registered_for_display';generation_requested=$false}
        }
        'display' {
            $id=[string]$Request.job_id; $session=[string]$Request.session_id; $role=[string]$Request.role
            if ($workerDisplays.ContainsKey($id)) { throw 'A display is already registered for this job.' }
            if ($role -eq 'claude') {
                if (-not $workerModelJobs.ContainsKey($session) -or $workerModelJobs[$session].state -ne 'completed') { throw 'Only a completed worker-owned Claude session can be displayed.' }
                if ($workerModelJobs[$session].returned_session_id -and $workerModelJobs[$session].returned_session_id -ne $session) { throw 'Claude returned another session; stop.' }
            } elseif ($session -ne $workerGptSession -and -not $workerGptJobs.ContainsKey($session)) {
                throw 'Only the registered GPT integration test session can be displayed.'
            }
            $displayArguments=@('-NoProfile','-File',$PSCommandPath,'-Mode','Display','-Role',$role,'-SessionId',$session,'-SshTarget',$SshTarget)
            $displayProcess=Start-Process -FilePath 'powershell.exe' -ArgumentList (($displayArguments|ForEach-Object{Quote-WorkerArg $_}) -join ' ') -PassThru
            $workerDisplays[$id]=@{ process=$displayProcess; role=$role; session=$session; transcript_opened=$false }
            return @{job_id=$id; role=$role; session_id=$session; state='opening_real_client'}
        }
        'capture' {
            $id=[string]$Request.job_id
            if (-not $workerDisplays.ContainsKey($id)) { throw 'Screenshots are limited to worker-opened client windows.' }
            $display=$workerDisplays[$id]; $display.process.Refresh()
            if ($display.process.HasExited) { throw 'The registered client window has closed.' }
            $file=Join-Path (Join-Path $workerJobsRoot $display.session) ('window-'+$display.role+'.json')
            if (-not (Test-Path -LiteralPath $file)) { throw 'Client console window is not ready.' }
            $registration=Get-Content -LiteralPath $file -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($registration.process_id -ne $display.process.Id) { throw 'Window registration owner mismatch.' }
            $handle=[IntPtr]([long]$registration.window_handle)
            if (-not [ModelWorkerWindow]::IsWindow($handle)) { throw 'Registered console window is no longer available.' }
            [void][ModelWorkerWindow]::ShowWindow($handle,9)
            [void][ModelWorkerWindow]::SetForegroundWindow($handle)
            Start-Sleep -Milliseconds 350
            if ([ModelWorkerWindow]::GetForegroundWindow() -ne $handle) { throw 'Could not activate the specific client window; screenshot cancelled.' }
            $rect=New-Object ModelWorkerWindow+RECT
            if (-not [ModelWorkerWindow]::GetWindowRect($handle,[ref]$rect)) { throw 'Window bounds unavailable.' }
            $width=$rect.Right-$rect.Left; $height=$rect.Bottom-$rect.Top
            if ($width -le 0 -or $height -le 0 -or $width -gt 8000 -or $height -gt 8000) { throw 'Invalid window size.' }
            $bitmap=New-Object Drawing.Bitmap($width,$height)
            $graphics=[Drawing.Graphics]::FromImage($bitmap)
            $stream=New-Object IO.MemoryStream
            try {
                $graphics.CopyFromScreen($rect.Left,$rect.Top,0,0,(New-Object Drawing.Size($width,$height)))
                $bitmap.Save($stream,[Drawing.Imaging.ImageFormat]::Png)
                $bytes=$stream.ToArray()
                $path=Join-Path (Join-Path $workerJobsRoot $display.session) ('capture-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmssfff')+'.png')
                [IO.File]::WriteAllBytes($path,$bytes)
                return @{role=$display.role;session_id=$display.session;width=$width;height=$height;png_base64=[Convert]::ToBase64String($bytes);local_file=$path;source='real_official_client_console_window'}
            } finally { $stream.Dispose();$graphics.Dispose();$bitmap.Dispose() }
        }
        'navigate' {
            $id=[string]$Request.job_id
            if(-not $workerDisplays.ContainsKey($id)){throw 'Unknown owned client display.'}
            $display=$workerDisplays[$id];$display.process.Refresh()
            if($display.process.HasExited){throw 'Client display closed.'}
            $file=Join-Path (Join-Path $workerJobsRoot $display.session) ('window-'+$display.role+'.json')
            $registration=Get-Content -LiteralPath $file -Raw -Encoding UTF8|ConvertFrom-Json
            if($registration.process_id -ne $display.process.Id){throw 'Window owner changed.'}
            $handle=[IntPtr]([long]$registration.window_handle)
            if(-not [ModelWorkerWindow]::IsWindow($handle)){throw 'Client window no longer exists.'}
            [void][ModelWorkerWindow]::ShowWindow($handle,9)
            [void][ModelWorkerWindow]::SetForegroundWindow($handle)
            Start-Sleep -Milliseconds 250
            if([ModelWorkerWindow]::GetForegroundWindow() -ne $handle){throw 'Could not activate the owned client; navigation cancelled.'}
            if($Request.navigation -eq 'open_transcript'){
                if(-not $display.transcript_opened){
                    $keys=if($display.role -eq 'gpt'){'^t'}else{'^o'}
                    [System.Windows.Forms.SendKeys]::SendWait($keys);$display.transcript_opened=$true
                }
            }elseif($Request.navigation -eq 'page_up'){[System.Windows.Forms.SendKeys]::SendWait('{PGUP}')}
            elseif($Request.navigation -eq 'page_down'){[System.Windows.Forms.SendKeys]::SendWait('{PGDN}')}
            Start-Sleep -Milliseconds 250
            if([ModelWorkerWindow]::GetForegroundWindow() -ne $handle){throw 'Foreground changed during display navigation; inspect before continuing.'}
            return @{job_id=$id;navigation=$Request.navigation;source='real_official_client_console_window';prompt_sent=$false}
        }
        'stop' { $script:workerKeepRunning=$false; return @{stopped=$true} }
    }
}

if (-not (Get-Command ssh.exe -ErrorAction SilentlyContinue) -or -not (Get-Command scp.exe -ErrorAction SilentlyContinue)) { throw 'Windows OpenSSH is required.' }
$workerChromeProfile=Join-Path $env:LOCALAPPDATA 'LLM-Authoring-Pilot-Chrome'
$workerChromeListener=Get-NetTCPConnection -LocalPort 9226 -State Listen -ErrorAction SilentlyContinue
if($workerChromeListener){
    $workerChromeOwner=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$workerChromeListener[0].OwningProcess)
    if($workerChromeOwner.CommandLine -notlike ('*'+$workerChromeProfile+'*')){throw 'Port 9226 belongs to another browser or application; no attachment was attempted.'}
} else {
    $workerChromeRoots=@($env:ProgramFiles,${env:ProgramFiles(x86)},$env:LOCALAPPDATA)|Where-Object{-not [string]::IsNullOrWhiteSpace($_)}
    $workerChromePath=@($workerChromeRoots|ForEach-Object{Join-Path $_ 'Google\Chrome\Application\chrome.exe'}|Where-Object{Test-Path -LiteralPath $_ -PathType Leaf})|Select-Object -First 1
    if(-not $workerChromePath){throw 'Google Chrome was not found.'}
    $workerChromeArguments=@('--remote-debugging-port=9226','--remote-debugging-address=127.0.0.1',('--user-data-dir="'+$workerChromeProfile+'"'),'--no-first-run','--no-default-browser-check','--new-window','https://www.doubao.com/chat/')
    Start-Process -FilePath $workerChromePath -ArgumentList $workerChromeArguments|Out-Null
    $workerChromeReady=$false
    for($workerChromeAttempt=0;$workerChromeAttempt -lt 30;$workerChromeAttempt++){
        try{$workerChromeVersion=Invoke-RestMethod -Uri 'http://127.0.0.1:9226/json/version' -TimeoutSec 2;if($workerChromeVersion.Browser -like 'Chrome/*'){$workerChromeReady=$true;break}}catch{}
        Start-Sleep -Milliseconds 500
    }
    if(-not $workerChromeReady){throw 'Dedicated Chrome did not start.'}
}
$workerListener=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback,9227)
$workerListener.Start()
$workerTunnel=$null
try {
    $random=New-Object byte[] 32
    $rng=[Security.Cryptography.RandomNumberGenerator]::Create();$rng.GetBytes($random);$rng.Dispose()
    $workerToken=([BitConverter]::ToString($random)).Replace('-','').ToLowerInvariant()
    $ports=@(19227)
    $existingChrome=@(& ssh.exe -o BatchMode=yes $SshTarget "ss -ltnH '( sport = :19226 )'")
    if ($LASTEXITCODE -ne 0) { throw 'SSH preflight failed.' }
    if ($existingChrome.Count -eq 0) {
        try { $version=Invoke-RestMethod -Uri 'http://127.0.0.1:9226/json/version' -TimeoutSec 3 } catch { throw 'The dedicated Chrome on port 9226 is closed. Reopen the existing dedicated Chrome first.' }
        if ($version.Browser -notlike 'Chrome/*') { throw 'The local debugging endpoint is not Chrome.' }
        $ports+=19226
    }
    $tunnelArgs=@('-N','-T','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=30','-o','ServerAliveCountMax=3','-R','127.0.0.1:19227:127.0.0.1:9227')
    if ($ports -contains 19226) { $tunnelArgs+=@('-R','127.0.0.1:19226:127.0.0.1:9226') }
    $tunnelArgs+=$SshTarget
    $workerTunnel=Start-Process -FilePath 'ssh.exe' -ArgumentList (($tunnelArgs|ForEach-Object{Quote-WorkerArg $_}) -join ' ') -PassThru -NoNewWindow
    Start-Sleep -Milliseconds 700
    if ($workerTunnel.HasExited) { throw 'Private SSH tunnel could not start; no model was called.' }
    $handshake=Join-Path $workerRoot 'worker-connection.json'
    Write-WorkerJson $handshake @{schema_version=1;endpoint='http://127.0.0.1:19227';token=$workerToken;started_at_utc=[DateTime]::UtcNow.ToString('o');client_version=$workerVersion;policy_tests_passed=$workerPolicyTests;chrome_forwarded=($ports -contains 19226)}
    & scp.exe -q -- $handshake ($SshTarget+':'+$workerServerRoot+'/private/worker-connection.json')
    if ($LASTEXITCODE -ne 0) { throw 'Private worker handshake upload failed.' }
    Write-Host 'Local model worker connected. Leave this window open; Ctrl+C disconnects it.'
    Write-Host 'Only fixed model test, own session display, and own client window screenshots are supported.'
    Write-Host 'Tell Codex: model worker is connected.'
    $script:workerKeepRunning=$true
    while ($script:workerKeepRunning) {
        Update-WorkerJobs
        if ($workerTunnel.HasExited) { throw 'SSH tunnel disconnected. Existing model processes have not been repeated.' }
        if (-not $workerListener.Pending()) { Start-Sleep -Milliseconds 150;continue }
        $client=$workerListener.AcceptTcpClient();$client.ReceiveTimeout=7000;$client.SendTimeout=10000
        try {
            $network=$client.GetStream();$headerBytes=New-Object 'Collections.Generic.List[byte]'
            while ($true) {
                $next=$network.ReadByte();if($next -lt 0){throw 'Incomplete HTTP request.'};$headerBytes.Add([byte]$next)
                $n=$headerBytes.Count;if($n -gt 16384){throw 'Request header too large.'}
                if($n -ge 4 -and $headerBytes[$n-4] -eq 13 -and $headerBytes[$n-3] -eq 10 -and $headerBytes[$n-2] -eq 13 -and $headerBytes[$n-1] -eq 10){break}
            }
            $header=[Text.Encoding]::ASCII.GetString($headerBytes.ToArray())
            if($header -notmatch '^POST /rpc HTTP/1\.[01]\r\n'){throw 'Only POST /rpc is supported.'}
            $tokenMatch=[regex]::Match($header,'(?im)^X-LLM-Token:\s*([^\r\n]+)\r?$')
            if(-not $tokenMatch.Success -or $tokenMatch.Groups[1].Value.Trim() -cne $workerToken){throw 'Unauthorized worker request.'}
            $lengthMatch=[regex]::Match($header,'(?im)^Content-Length:\s*(\d+)\r?$')
            if(-not $lengthMatch.Success){throw 'Content-Length required.'}
            $length=[int]$lengthMatch.Groups[1].Value
            if($length -le 0 -or $length -gt 262144){throw 'Request body length invalid.'}
            $body=New-Object byte[] $length;$offset=0
            while($offset -lt $length){$read=$network.Read($body,$offset,$length-$offset);if($read -le 0){throw 'Incomplete request body.'};$offset+=$read}
            $raw=$workerUtf8.GetString($body);$request=$raw|ConvertFrom-Json
            Assert-WorkerRequest $request
            $hash=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($body))).Replace('-','')
            if($workerRequestCache.ContainsKey([string]$request.id)){
                $cached=$workerRequestCache[[string]$request.id]
                if($cached.hash -cne $hash){throw 'Request ID reused with different content.'}
                $response=$cached.response
            } else {
                $response=@{ok=$true;result=(Invoke-WorkerRequest $request)}
                if($request.action -in @('claude_start','display','stop')){$workerRequestCache[[string]$request.id]=@{hash=$hash;response=$response}}
            }
        } catch { $response=@{ok=$false;error=$_.Exception.Message} }
        try {
            $payload=$workerUtf8.GetBytes(($response|ConvertTo-Json -Depth 25 -Compress))
            $prefix=[Text.Encoding]::ASCII.GetBytes("HTTP/1.1 200 OK`r`nContent-Type: application/json; charset=utf-8`r`nContent-Length: $($payload.Length)`r`nConnection: close`r`n`r`n")
            $client.GetStream().Write($prefix,0,$prefix.Length);$client.GetStream().Write($payload,0,$payload.Length);$client.GetStream().Flush()
        } finally { $client.Close() }
    }
} finally {
    $workerListener.Stop()
    if($workerTunnel -and -not $workerTunnel.HasExited){$workerTunnel.Kill()}
    Write-Host 'Model worker disconnected.'
}
