# Wrapper para o Agendador de Tarefas do Windows.
# Vai para a raiz do repositório, roda a coleta diária e grava um log
# datado. Sai com o mesmo código de saída do Python (0 = ok).
#
# O log detalhado da coleta é gravado pelo próprio Python em
# <BASE_DIR>/logs/coleta_AAAA-MM-DD.log (ver logging_setup.py).
# Este arquivo grava um log de "bootstrap" — serve para o caso de o
# Python nem chegar a iniciar (Python errado, erro de import, G: fora).

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

# Preferência: mesma pasta de logs da coleta (Google Drive). Se o G: não
# estiver acessível, cai para ./logs dentro do repositório.
$driveLogs = "G:\Meu Drive\book-trends\logs"
try {
    New-Item -ItemType Directory -Force -Path $driveLogs -ErrorAction Stop | Out-Null
    $logDir = $driveLogs
} catch {
    $logDir = Join-Path $repo "logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}
$log = Join-Path $logDir ("run_daily_{0:yyyy-MM-dd}.log" -f (Get-Date))

# Escolhe o Python: venv do projeto, senão o Python 3.14 instalado, senão o do PATH.
# (O Agendador de Tarefas nem sempre herda o mesmo PATH da sua sessão.)
$venvPy = Join-Path $repo ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    $py = $venvPy
} elseif (Test-Path "C:\Python314\python.exe") {
    $py = "C:\Python314\python.exe"
} else {
    $py = "python"
}

# Carimbo de início e execução. Junta stdout+stderr e anexa ao log num
# único fluxo (redirecionar o mesmo arquivo duas vezes trava o arquivo).
"=== run_daily {0:yyyy-MM-dd HH:mm:ss} | python: $py ===" -f (Get-Date) | Out-File -FilePath $log -Append -Encoding utf8
& $py run_diario.py *>> $log
exit $LASTEXITCODE
