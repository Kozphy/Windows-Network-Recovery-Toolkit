# Benchmark Design

## Unit of analysis
One purple scenario execution (fixture-driven).

## Labels
- Positive class: `expect_detection=true`
- Negative class: benign controls (`expect_detection=false`)

## Metrics
TP/FP/TN/FN, Precision, Recall, F1, FPR, FNR, MTTD (T0→T3), remediation success, verification success.

## Baselines
0. No detection  
1. Static ProxyEnable==1 && authorized!=true  
2. DET-PROXY-001 only  
3. Proposed full purple pipeline  

## CI constraints
Generic CI runs dry-run fixture benchmarks only — no privileged host mutation.
