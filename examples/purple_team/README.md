# Purple Team quick demo

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m src.purple_team scenarios list
python -m src.purple_team validate proxy-drift-001
python -m src.purple_team run proxy-drift-001
python -m src.purple_team benchmark --no-evidence --json
python -m src.purple_team baselines
```

Responsible use: lab/fixture only; no malware, MITM, credential theft, or production targeting.
