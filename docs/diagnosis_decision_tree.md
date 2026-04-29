# Diagnosis Decision Tree

This guide explains how the automatic diagnosis scripts choose a recommendation.

The goal is simple: collect a few safe test results, then point the user toward the smallest useful fix.

## Start Here

Run:

```bat
scripts\auto_diagnose.bat
```

The script is read-only. It does not change network settings.

It checks:

- Current network adapters
- DNS lookup with `nslookup google.com`
- TCP port 443 with `Test-NetConnection`
- HTTPS with `curl https://www.google.com`
- WinHTTP proxy settings
- User proxy registry values

It saves the full output to:

```text
logs\network_diagnosis_YYYYMMDD_HHMMSS.txt
```

## Decision Tree

```text
Start
  |
  v
Does DNS work?
  |
  +-- No --> Likely DNS problem
  |          Recommendation: run reset_dns.bat
  |
  +-- Yes
        |
        v
Are proxy settings enabled or suspicious?
        |
        +-- Yes, and HTTPS fails --> Likely proxy problem
        |                           Recommendation: run reset_proxy.bat
        |
        +-- No or not clearly related
              |
              v
Does TCP 443 work?
              |
              +-- No --> Likely TCP/IP, Winsock, firewall, VPN, or antivirus issue
              |          Recommendation: run one_click_fix.bat and restart
              |
              +-- Yes
                    |
                    v
Does HTTPS work with curl?
                    |
                    +-- No --> Likely HTTPS/TLS/application-layer problem
                    |          Recommendation: check VPN, antivirus, proxy inspection, or firewall software
                    |
                    +-- Yes --> Network path looks healthy
                               If browser fails only after time, run check_connection_exhaustion.bat
                               Otherwise try another browser or reset browser settings
```

## Case: Ping Works But Curl Fails

This usually means the computer has basic internet reachability, but something above basic IP connectivity is broken.

Possible causes:

- DNS problem
- Proxy problem
- Winsock or TCP/IP stack problem
- VPN or antivirus filtering
- Firewall rule problem
- Browser or application-specific configuration

Recommended flow:

1. Run `auto_diagnose.bat`.
2. If DNS fails, run `reset_dns.bat`.
3. If proxy settings look wrong, run `reset_proxy.bat`.
4. If TCP 443 fails or the result is unclear, run `one_click_fix.bat` and restart.
5. If only one browser fails, try another browser or reset browser settings.

## Case: DNS OK But TCP Fails

If DNS works but TCP port 443 fails, Windows can resolve the website name but cannot complete the connection.

Possible causes:

- Winsock corruption
- TCP/IP stack problem
- VPN software blocking traffic
- Antivirus web protection blocking traffic
- Firewall software blocking outbound HTTPS
- Router or network policy blocking the connection

Recommended action:

- Run `one_click_fix.bat` and restart.
- If it still fails, check VPN, antivirus, firewall software, router settings, or network policy.

## Case: TCP 443 OK But HTTPS Fails

If TCP port 443 works but `curl https://www.google.com` fails, the connection can open but the HTTPS request does not complete.

Possible causes:

- TLS inspection by antivirus or security software
- VPN or proxy interception
- Broken certificate handling
- Incorrect system date or time
- Application-layer filtering

Recommended action:

1. Check whether VPN or antivirus web protection is enabled.
2. Check the Windows date and time.
3. Try another network, such as a mobile hotspot.
4. If unsure, run `one_click_fix.bat` and restart.

## Case: Ping, DNS, And HTTPS Work But Browser Fails After Time

If ping, DNS, TCP 443, and HTTPS checks all work, but browsers start failing after the computer has been running for a while, check for connection exhaustion.

Possible signs:

- Browser works after reboot, then times out later.
- API clients, scripts, bots, Docker, WSL, or browser tabs use many network connections.
- `curl` may work during diagnosis, but browsers become unreliable during heavy activity.
- Restarting the heavy application temporarily fixes the issue.

Recommended action:

```bat
scripts\check_connection_exhaustion.bat
```

This read-only script checks:

- `TIME_WAIT` connection count
- `ESTABLISHED` connection count
- Top processes using TCP connections
- Ephemeral TCP port range

If connection exhaustion is detected, restart the application using the network heavily and check for connection reuse bugs, such as missing `requests.Session` usage in Python.

## Case: Reboot Works But Later Timeout Returns

If the network works after reboot but times out again later, the issue may be caused by something that starts after Windows boots.

Possible causes:

- VPN reconnecting automatically
- Antivirus web filtering
- Proxy auto-config returning bad settings
- Browser extension changing proxy settings
- Socket leaks or ephemeral port exhaustion
- Router or DNS instability

Recommended action:

1. Run `auto_diagnose.bat` when the issue is happening.
2. Check the log for proxy values or failed HTTPS tests.
3. Run `check_connection_exhaustion.bat` if browser failures appear after long uptime or heavy app usage.
4. Temporarily disable VPN or antivirus web filtering for testing.
5. Try a different network, such as a mobile hotspot.
6. Review startup apps that may change network settings.

## Proxy Auto-Config, VPN, And Antivirus Notes

Proxy auto-config, VPN clients, and antivirus tools can change how traffic leaves the computer.

They may:

- Add a proxy server
- Add an auto-config URL
- Intercept HTTPS traffic
- Block outbound connections
- Reapply settings after a reboot

The toolkit does not remove VPN or antivirus software. It only resets common Windows network settings.

If proxy settings keep coming back after `reset_proxy.bat`, check:

- VPN client settings
- Work or school device policies
- Antivirus web protection settings
- Browser extensions
- Startup applications

## Safety Rules

- Do not disable network adapter bindings.
- Do not reset firewall rules automatically.
- Use `reset_firewall.bat` only as a manual last step.
- Restart after `one_click_fix.bat`.
- Keep the generated log if you need help from another person.
