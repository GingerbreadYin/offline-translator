$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:PYTHONUTF8 = '1'
$pythonExe = Join-Path (Get-Location) '.venv/Scripts/python.exe'
New-Item -ItemType Directory -Force build | Out-Null
& $pythonExe -m pytest -q --basetemp=build/test-temp
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $pythonExe main.py --self-test
if ($LASTEXITCODE -ne 0) { throw 'Offline resource test failed' }
& $pythonExe -m PyInstaller --noconfirm --clean --onedir --windowed --name OfflineTranslator --collect-data rapidocr_onnxruntime --collect-binaries ctranslate2 --collect-data ctranslate2 --collect-all sentencepiece --exclude-module PySide6.QtWebEngine --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets main.py
if ($LASTEXITCODE -ne 0) { throw 'Executable build failed' }
$packageRoot = Join-Path (Get-Location) 'dist/OfflineTranslator'
New-Item -ItemType Directory -Force (Join-Path $packageRoot 'resources') | Out-Null
Copy-Item -LiteralPath 'resources/dictionary.db','resources/manifest.json' -Destination (Join-Path $packageRoot 'resources')
Copy-Item -LiteralPath 'resources/translation' -Destination (Join-Path $packageRoot 'resources') -Recurse
Copy-Item -LiteralPath 'README.md','THIRD-PARTY-NOTICES.md','requirements.lock.txt' -Destination $packageRoot
& $pythonExe tools/collect_licenses.py $packageRoot
if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
$archive = Join-Path (Get-Location) 'dist/OfflineTranslator-v0.1.0-win-x64.zip'
& $pythonExe -c "import shutil; shutil.make_archive('dist/OfflineTranslator-v0.1.0-win-x64', 'zip', 'dist', 'OfflineTranslator')"
if ($LASTEXITCODE -ne 0) { throw 'ZIP creation failed' }
Get-FileHash -LiteralPath $archive -Algorithm SHA256 | Format-List
