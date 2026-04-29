# Ping Works But Browser Fails

Sometimes `ping 8.8.8.8` works, but browsers, `curl`, or other apps cannot open websites.

This means the machine can reach the internet at a basic IP level, but something higher in the network stack is failing.

## Why Ping Can Work While Browsers Fail

Ping uses ICMP. Browsers use DNS, TCP, TLS, HTTP, proxy settings, certificate validation, and firewall rules.

Because of that, ping can succeed even when:

- DNS is broken
- Proxy settings are wrong
- Winsock is corrupted
- HTTP or HTTPS traffic is blocked
- Firewall rules are damaged
- A VPN or security tool is intercepting traffic incorrectly

## Quick Diagnosis

Run:

```bat
scripts\check_network.bat
```

Then read the result:

- If ping fails, start with physical connection, Wi-Fi, adapter, router, or ISP checks.
- If ping works but DNS fails, run `reset_dns.bat`.
- If ping and DNS work but `curl` fails, check proxy, firewall, VPN, or Winsock.
- If proxy settings are enabled unexpectedly, run `reset_proxy.bat`.
- If the issue is unclear, run `one_click_fix.bat` and restart Windows.

## Common Causes

### Broken DNS Cache

Windows may have stale or invalid DNS records cached.

Fix:

```bat
scripts\reset_dns.bat
```

### Broken Proxy Settings

Browsers and command-line tools may try to route traffic through a proxy that does not exist.

Fix:

```bat
scripts\reset_proxy.bat
```

### Winsock Corruption

Winsock is the Windows networking catalog used by applications. VPNs, proxy tools, security software, and malware cleanup can leave it in a bad state.

Fix:

```bat
scripts\one_click_fix.bat
```

Restart Windows after running the full repair.

### Firewall Problems

Firewall rules can block applications even when the internet connection works.

Fix:

```bat
scripts\reset_firewall.bat
```

Use this carefully. It resets custom firewall rules to Windows defaults.

## Recommended Repair Order

1. Run `check_network.bat`.
2. Run `reset_dns.bat` if DNS failed.
3. Run `reset_proxy.bat` if proxy settings look wrong.
4. Run `one_click_fix.bat` if browser or `curl` still fails.
5. Restart Windows.
6. Run `reset_firewall.bat` only if firewall rules are likely involved.

## After Restarting

Test again:

```bat
ping 8.8.8.8
nslookup google.com
curl http://example.com
```

Then open a browser and visit a normal website.
