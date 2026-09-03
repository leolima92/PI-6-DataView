# Wrapper para o Agendador de Tarefas do Windows.
# Vai para a raiz do repositório, roda a coleta diária e grava um log
# datado em logs/. Sai com o mesmo código de saída do Python (0 = ok).

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$logDir = Join-Path $repo "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("coleta_{0:yyyy-MM-dd}.log" -f (Get-Date))

# Se você usa venv, troque "python" pelo caminho do python do venv,
# ex.: $py = Join-Path $repo ".venv\Scripts\python.exe"
$py = "python"

& $py run_diario.py 1>> $log 2>> $log
exit $LASTEXITCODE
