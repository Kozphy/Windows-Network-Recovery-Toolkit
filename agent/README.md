# Agent (Python)

## Run once

```bash
pip install -r requirements.txt
python agent/agent.py --api http://localhost:8000 --token <SUPABASE_ACCESS_TOKEN> --project-id <PROJECT_ID>
```

## Loop mode

```bash
python agent/agent.py --api http://localhost:8000 --token <SUPABASE_ACCESS_TOKEN> --project-id <PROJECT_ID> --loop --interval 10
```

The agent collects:

- ping
- DNS
- HTTPS
- proxy state
- TIME_WAIT / ESTABLISHED

And sends data to `/diagnose` and `/monitor`.
