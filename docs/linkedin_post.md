# LinkedIn post draft

**Title:** I upgraded a Windows proxy repair script into an endpoint causation platform.

---

I started with a simple problem: my browser failed because Windows proxy settings silently changed to `127.0.0.1:<port>`.

The first version could detect the proxy drift and find a process listening on the localhost port.

But that was only **correlation**.

The upgrade adds:

- Sysmon registry-writer attribution
- Process lineage
- Proxy causation analysis
- Process classification
- Policy-gated decisions
- Evidence tree
- Timeline replay
- Read-only safety model

The key lesson:

**Observation is not proof.**  
A listener is not necessarily the writer.  
A repair tool should not become a destructive tool.

This project now behaves more like a local-first endpoint reliability and security telemetry platform than a simple repair script.

#Windows #Python #SRE #CyberSecurity #EndpointSecurity #Observability #Sysmon #DevTools #PlatformEngineering #IncidentResponse
