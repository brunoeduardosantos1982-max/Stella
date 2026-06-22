param([int]$N = 5)
# Drop do Radar de Tendencias da Stella. Roda: uv run stella radar --n N
# Resultado (card) vai pro Telegram; este log guarda a saida e o exit code.
# Copia versionada. O arquivo vivo fica em D:\VortexBrain00\stella-radar.ps1.
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$log = "D:\VortexBrain00\stella-radar.log"
Set-Location "D:\VortexBrain00\stella"
"=== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | radar --n $N | inicio ===" | Out-File $log -Append -Encoding utf8
$saida = & uv run stella radar --n $N 2>&1 | Out-String
$saida | Out-File $log -Append -Encoding utf8
"=== exit: $LASTEXITCODE ===" | Out-File $log -Append -Encoding utf8
