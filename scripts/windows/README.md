# Scripts Windows da Stella (cópias versionadas)

Os arquivos vivos rodam a partir de `D:\VortexBrain00\` (fora do repo); estas são cópias versionadas.

## Radar de Tendências

- `stella-radar.ps1` — wrapper que roda `uv run stella radar --n <N>` e grava em `stella-radar.log`.
- `stella-run-hidden.vbs` — lançador oculto genérico (sem flash de console); repassa argumentos ao PowerShell.

### Tarefas agendadas (Task Scheduler), todas ocultas via o `.vbs`

| Tarefa | Horário | `-N` |
|--------|---------|------|
| Stella Radar 06h | 06:00 diário | 5 |
| Stella Radar 14h | 14:00 diário | 3 |
| Stella Radar 19h | 19:00 diário | 3 |

Registro (PowerShell), exemplo para um drop:

```powershell
$vbs = "D:\VortexBrain00\stella-run-hidden.vbs"
$ps1 = "D:\VortexBrain00\stella-radar.ps1"
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$action  = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$vbs`" `"$ps1`" -N 5"
$trigger = New-ScheduledTaskTrigger -Daily -At 6:00am
Register-ScheduledTask -TaskName "Stella Radar 06h" -Action $action -Trigger $trigger -Principal $principal -Force
```

Para pausar: `Disable-ScheduledTask -TaskName "Stella Radar 06h"` (idem 14h/19h).
Para remover: `Unregister-ScheduledTask -TaskName "Stella Radar 06h" -Confirm:$false`.
