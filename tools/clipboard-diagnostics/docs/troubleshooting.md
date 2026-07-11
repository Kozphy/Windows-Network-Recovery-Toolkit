# Troubleshooting

## The diagnostic passes, but Ctrl+C or Ctrl+V fails

Test copy and paste in Notepad. If Notepad works, investigate the affected application's permissions, focus state, keyboard shortcuts, extensions, remote-session settings, or clipboard integration.

## Clipboard history does not open

Press `Win + V`. Windows may ask you to enable clipboard history. Clipboard history is optional and is not required for ordinary copy/paste.

## Remote Desktop or virtual machine

Clipboard redirection can be disabled by Remote Desktop, Group Policy, virtualization software, or security policy even when the local Windows clipboard works.

## Reset Windows Explorer

```powershell
Stop-Process -Name explorer -Force
Start-Process explorer.exe
```

This interrupts the desktop shell briefly. Save work before using it.

## Security interpretation

Clipboard failure alone does not establish malware, data theft, monitoring, or compromise. Treat it as a reliability symptom until supported by additional evidence.
