' Lancador oculto para scripts da Stella (sem flash de console).
' Uso: wscript.exe "stella-run-hidden.vbs" "C:\caminho\para\script.ps1" [args...]
' wscript e' GUI-subsystem (nao abre console) e roda o PowerShell em janela oculta (estilo 0).
' Argumentos extras (apos o script) sao repassados ao PowerShell; sem extras, comportamento identico ao original.
' Copia versionada. O arquivo vivo fica em D:\VortexBrain00\stella-run-hidden.vbs (compartilhado por todas as tarefas ocultas da Stella).
Set sh = CreateObject("WScript.Shell")
ps1 = WScript.Arguments(0)
extra = ""
For i = 1 To WScript.Arguments.Count - 1
  extra = extra & " " & WScript.Arguments(i)
Next
sh.Run "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File """ & ps1 & """" & extra, 0, False
