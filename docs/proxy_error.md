# ERR_PROXY_CONNECTION_FAILED

`ERR_PROXY_CONNECTION_FAILED` usually means the browser is trying to use a proxy server that is missing, unreachable, or incorrectly configured.

This can happen after:

- Installing or removing a VPN
- Using a corporate proxy
- Malware or adware changing proxy settings
- Browser extensions changing network settings
- A proxy auto-config script becoming unavailable
- Manual proxy settings being left enabled

## Common Symptoms

- Chrome or Edge shows `ERR_PROXY_CONNECTION_FAILED`
- Ping still works
- Some apps connect while browsers fail
- `curl` may fail with connection or proxy errors
- Windows proxy settings show a proxy you do not recognize

## What To Check

Run:

```bat
scripts\check_network.bat
```

Look for:

- WinHTTP proxy settings
- `ProxyEnable`
- `ProxyServer`
- `AutoConfigURL`

If you do not intentionally use a proxy, these values should usually be disabled or empty.

## How To Fix It

Run:

```bat
scripts\reset_proxy.bat
```

This script:

- Resets WinHTTP proxy settings
- Sets `ProxyEnable` to `0`
- Deletes `ProxyServer` if it exists
- Deletes `AutoConfigURL` if it exists

Close and reopen your browser after running the script.

## When Proxy Reset Is Not Enough

If proxy reset does not fix the problem, run:

```bat
scripts\one_click_fix.bat
```

Then restart Windows.

The full repair also resets Winsock and TCP/IP, which can help when network components are corrupted.

## Why Winsock Reset Can Help

Winsock is the Windows networking interface used by many applications. Some VPNs, proxies, security tools, and malware cleanup tools can leave broken network providers or catalog entries behind.

`netsh winsock reset` rebuilds that catalog to a clean default state. This can fix cases where the proxy setting is not the only problem.

## Prevention Tips

- Remove unused VPN or proxy tools cleanly.
- Avoid unknown browser extensions that change traffic settings.
- Check Windows proxy settings after malware cleanup.
- Keep a note of required corporate proxy settings before resetting them.
