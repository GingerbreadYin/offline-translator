$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:PYTHONUTF8 = '1'
$pythonExe = Join-Path (Get-Location) '.venv/Scripts/python.exe'
$version = (& $pythonExe -c "from translator import __version__; print(__version__)").Trim()
New-Item -ItemType Directory -Force build | Out-Null
& $pythonExe -m pytest -q --basetemp=build/test-temp
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $pythonExe main.py --self-test
if ($LASTEXITCODE -ne 0) { throw 'Offline resource test failed' }
& $pythonExe main.py --worker-test
if ($LASTEXITCODE -ne 0) { throw 'Worker process test failed' }
& $pythonExe -m PyInstaller --noconfirm --clean --onedir --windowed --name OfflineTranslator --collect-data rapidocr_onnxruntime --collect-binaries ctranslate2 --collect-data ctranslate2 --collect-all sentencepiece --exclude-module PySide6.QtWebEngine --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets main.py
if ($LASTEXITCODE -ne 0) { throw 'Executable build failed' }
$packageRoot = Join-Path (Get-Location) 'dist/OfflineTranslator'
New-Item -ItemType Directory -Force (Join-Path $packageRoot 'resources') | Out-Null
Copy-Item -LiteralPath 'resources/dictionary.db','resources/manifest.json' -Destination (Join-Path $packageRoot 'resources')
Copy-Item -LiteralPath 'resources/translation' -Destination (Join-Path $packageRoot 'resources') -Recurse
Copy-Item -LiteralPath 'README.md','THIRD-PARTY-NOTICES.md','requirements.lock.txt','CHANGELOG.md' -Destination $packageRoot
& $pythonExe tools/collect_licenses.py $packageRoot
if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
$exePath = Join-Path $packageRoot 'OfflineTranslator.exe'
foreach ($mode in @('self-test','worker-test','ui-smoke','capture-test','window-test')) {
    $reportPath = Join-Path (Get-Location) "build/packaged-$mode.json"
    $testProcess = Start-Process -FilePath $exePath -ArgumentList "--$mode",'--report',$reportPath -WindowStyle Hidden -PassThru
    if (-not $testProcess.WaitForExit(60000)) { $testProcess.Kill(); throw "Packaged $mode timed out" }
    $testProcess.Refresh()
    if ($testProcess.ExitCode -ne 0) { throw "Packaged $mode failed; inspect $reportPath" }
    $report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($mode -eq 'ui-smoke' -and $report.stage -ne 'event-loop-exited') { throw 'UI did not reach clean shutdown' }
}
$archiveBase = "dist/OfflineTranslator-v$version-win-x64"
$archive = Join-Path (Get-Location) "$archiveBase.zip"
& $pythonExe -c "import shutil,sys; shutil.make_archive(sys.argv[1], 'zip', 'dist', 'OfflineTranslator')" $archiveBase
if ($LASTEXITCODE -ne 0) { throw 'ZIP creation failed' }
Get-FileHash -LiteralPath $archive -Algorithm SHA256 | Format-List
