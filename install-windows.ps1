param(
    [Parameter(Mandatory = $true)]
    [string]$PublicIp,
    [string]$PythonExe = 'C:\Python313\python.exe'
)

# First installation only. Run in Administrator Windows PowerShell 5.1+.
# No cloud API or billing calls; downloads only the user's public repositories.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Root = 'C:\Calculator'
$TaskName = 'CalculatorHomework'
$Python = Join-Path $Root 'venv\Scripts\python.exe'
$account = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($account)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Open Windows PowerShell using Run as administrator, then try again.'
}
if ($PSVersionTable.PSVersion -lt [version]'5.1') {
    throw 'Windows PowerShell 5.1 or newer is required.'
}
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "Python not found at $PythonExe. Install Python 3.13 for all users first."
}
& $PythonExe -c "import ipaddress,sys; assert (3,12)<=sys.version_info[:2]<(3,14), 'Use Python 3.12 or 3.13'; a=ipaddress.IPv4Address(sys.argv[1]); assert a.is_global, 'Enter the actual public IPv4 from Tencent Cloud'" $PublicIp
if ($LASTEXITCODE -ne 0) { throw 'Python version or public IPv4 validation failed.' }
if (Test-Path -LiteralPath $Root) {
    throw "$Root already exists. Stop here to avoid replacing an existing installation."
}
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    throw "Scheduled task $TaskName already exists. No changes made."
}
if (Get-NetTCPConnection -LocalPort 80 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 80 is already in use. Do not stop other services without checking.'
}

Write-Host '1/7 Preparing folders and downloading the two repositories...'
New-Item -ItemType Directory -Path $Root, "$Root\downloads", "$Root\data", "$Root\logs" | Out-Null
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
foreach ($kind in @('backend', 'frontend')) {
    $repository = '832401321_calculator_' + $kind
    $archive = "$Root\downloads\$kind.zip"
    Invoke-WebRequest -UseBasicParsing `
        -Uri "https://codeload.github.com/Remisuki/$repository/zip/refs/heads/main" `
        -OutFile $archive -TimeoutSec 180
    $extracted = "$Root\downloads\$kind"
    Expand-Archive -LiteralPath $archive -DestinationPath $extracted
    Move-Item -LiteralPath (Join-Path $extracted ($repository + '-main')) `
        -Destination "$Root\$kind"
}
foreach ($relative in @('backend\windows_server.py', 'backend\wsgi.py',
        'backend\storage.py', 'backend\calculator.py', 'frontend\index.html',
        'frontend\app.js', 'frontend\styles.css')) {
    if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) {
        throw "Missing $relative. Upload the Windows files to GitHub before installing."
    }
}

Write-Host '2/7 Creating a private Python environment and installing Windows dependencies...'
& $PythonExe -m venv "$Root\venv"
if ($LASTEXITCODE -ne 0) { throw 'Creating the Python environment failed.' }
& $Python -m pip install --disable-pip-version-check `
    'Flask==3.1.3' 'psycopg[binary]==3.3.6' 'waitress==3.0.2'
if ($LASTEXITCODE -ne 0) { throw 'Installing Python dependencies failed.' }

Write-Host '3/7 Saving the public origin and configuring file permissions...'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$settings = @{ public_origin = "http://$PublicIp" } | ConvertTo-Json
[IO.File]::WriteAllText("$Root\settings.json", $settings, $utf8)
# LOCAL SERVICE can read the application and write only the data/log folders.
& icacls.exe $Root /grant '*S-1-5-19:(OI)(CI)RX'
if ($LASTEXITCODE -ne 0) { throw 'Setting application read permissions failed.' }
& icacls.exe "$Root\data" /grant '*S-1-5-19:(OI)(CI)M'
if ($LASTEXITCODE -ne 0) { throw 'Setting database permissions failed.' }
& icacls.exe "$Root\logs" /grant '*S-1-5-19:(OI)(CI)M'
if ($LASTEXITCODE -ne 0) { throw 'Setting log permissions failed.' }
$pythonFolder = Split-Path -Parent $PythonExe
& icacls.exe $pythonFolder /grant '*S-1-5-19:(OI)(CI)RX'
if ($LASTEXITCODE -ne 0) { throw 'Setting Python read permissions failed.' }

Write-Host '4/7 Running the repository tests and checking the Windows entry point...'
Push-Location "$Root\backend"
try {
    & $Python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Repository tests failed. Deployment stopped.' }
    & $Python -c "import windows_server; a=windows_server.create_app(); c=a.test_client(); assert c.get('/').status_code==200; assert c.get('/api/health').json=={'status':'ok'}; assert c.get('/config.js').status_code==200; assert c.get('/settings.json').status_code==404; print('Windows entry-point checks passed.')"
    if ($LASTEXITCODE -ne 0) { throw 'Windows entry-point checks failed.' }
} finally {
    Pop-Location
}

Write-Host '5/7 Allowing HTTP through Windows Firewall...'
if (-not (Get-NetFirewallRule -Name 'CalculatorHomework-HTTP' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name 'CalculatorHomework-HTTP' `
        -DisplayName 'Calculator homework HTTP (TCP 80)' `
        -Direction Inbound -Protocol TCP -LocalPort 80 `
        -Action Allow -Profile Any | Out-Null
}

Write-Host '6/7 Creating an automatic background task under LOCAL SERVICE...'
$serviceSid = [Security.Principal.SecurityIdentifier]::new('S-1-5-19')
$serviceAccount = $serviceSid.Translate([Security.Principal.NTAccount]).Value
$taskPrincipal = New-ScheduledTaskPrincipal -UserId $serviceAccount `
    -LogonType ServiceAccount -RunLevel Limited
$action = New-ScheduledTaskAction -Execute $Python `
    -Argument '"C:\Calculator\backend\windows_server.py"' `
    -WorkingDirectory "$Root\backend"
$trigger = New-ScheduledTaskTrigger -AtStartup
$taskSettings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action `
    -Trigger $trigger -Principal $taskPrincipal -Settings $taskSettings `
    -Description 'Course calculator: Waitress, HTTP API, persistent SQLite.' | Out-Null
Start-ScheduledTask -TaskName $TaskName

Write-Host '7/7 Waiting for the local health check...'
$healthy = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1/api/health' -TimeoutSec 2
        if ($health.status -eq 'ok') { $healthy = $true; break }
    } catch { }
    Start-Sleep -Seconds 2
}
if (-not $healthy) {
    throw "Health check failed. Read $Root\logs\server.log and the scheduled task status."
}
Write-Host ''
Write-Host 'Local installation checks passed. Now test public access from another device.'
Write-Host "Website: http://$PublicIp/"
Write-Host "Health:  http://$PublicIp/api/health"
Write-Host "Database: $Root\data\calculator.db"
Write-Host "Logs: $Root\logs\server.log"
Write-Host 'Also allow TCP 80 in the Tencent Cloud firewall/security group.'
Write-Host 'Do not run this first-install script again to restart the service.'
