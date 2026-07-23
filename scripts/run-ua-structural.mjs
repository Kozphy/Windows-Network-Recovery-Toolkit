#!/usr/bin/env node
/**
 * Structural-only Understand-Anything pipeline for WNRT.
 *
 * Runs UA's deterministic scan / import-map / batch / tree-sitter extract scripts,
 * converts results into batch graphs, merges them, and writes .ua/knowledge-graph.json.
 * Does NOT call an LLM — summaries are heuristic. For full semantic UA, use /understand
 * in Cursor/Claude after installing the plugin.
 *
 * Usage (from WNRT root, Node on PATH):
 *   node scripts/run-ua-structural.mjs
 *   node scripts/run-ua-structural.mjs --ua-root ../Understand-Anything
 */
import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
  readdirSync,
  rmSync,
} from "node:fs";
import { join, resolve, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, "..");

function parseArgs(argv) {
  let uaRoot = resolve(PROJECT_ROOT, "..", "Understand-Anything");
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--ua-root" && argv[i + 1]) {
      uaRoot = resolve(argv[++i]);
    }
  }
  return { uaRoot };
}

const { uaRoot } = parseArgs(process.argv.slice(2));
const PLUGIN = join(uaRoot, "understand-anything-plugin");
const SKILL = join(PLUGIN, "skills", "understand");
const UA_DIR = join(PROJECT_ROOT, ".ua");
const INTER = join(UA_DIR, "intermediate");
const TMP = join(UA_DIR, "tmp");

const EXCLUDE =
  "tests/*,**/tests/*,**/__pycache__/*,.tools/*,.venv/*,frontend/node_modules/*," +
  "node_modules/*,.pytest_tmp*/*,.audit/*,reports/*,examples/powerbi/*," +
  "**/fixtures/*,real_evidence/*,analytics/powerbi/data/*,.git/*";

function run(cmd, args, opts = {}) {
  console.error(`> ${cmd} ${args.join(" ")}`);
  const r = spawnSync(cmd, args, {
    stdio: "inherit",
    shell: false,
    cwd: opts.cwd || PROJECT_ROOT,
    env: process.env,
  });
  if (r.status !== 0) {
    throw new Error(`${cmd} exited ${r.status}`);
  }
}

function ensureDirs() {
  for (const d of [UA_DIR, INTER, TMP]) mkdirSync(d, { recursive: true });
}

function writeIgnore() {
  const p = join(UA_DIR, ".understandignore");
  if (existsSync(p)) return;
  writeFileSync(
    p,
    [
      "# Generated for structural UA run on WNRT",
      "tests/",
      "**/__pycache__/",
      ".tools/",
      ".venv/",
      "frontend/node_modules/",
      "node_modules/",
      ".pytest_tmp*/",
      ".audit/",
      "reports/",
      "**/fixtures/",
      "real_evidence/",
      "",
    ].join("\n"),
    "utf8",
  );
}

function categoryNodeType(fileCategory, path) {
  if (fileCategory === "docs") return "document";
  if (fileCategory === "config") return "config";
  if (fileCategory === "infra") {
    if (/\.github\/workflows|\.gitlab-ci|Jenkinsfile/i.test(path)) return "pipeline";
    if (/Dockerfile|docker-compose|k8s|kubernetes/i.test(path)) return "service";
    return "resource";
  }
  if (fileCategory === "data") {
    if (/\.(sql)$/i.test(path)) return "table";
    if (/\.(graphql|proto|prisma)$/i.test(path)) return "schema";
    return "schema";
  }
  return "file";
}

function complexityFromLines(n) {
  if (n < 50) return "simple";
  if (n < 200) return "moderate";
  return "complex";
}

function heuristicSummary(path, fileCategory, metrics = {}) {
  const base = basename(path);
  const parts = path.replace(/\\/g, "/").split("/");
  const area = parts.slice(0, 2).join("/");
  if (fileCategory === "docs") return `Documentation: ${base} (${area}).`;
  if (fileCategory === "config") return `Configuration file ${base} for ${area}.`;
  const fn = metrics.functionCount || 0;
  const cls = metrics.classCount || 0;
  return `Source module ${path} (${fn} functions, ${cls} classes) in ${area}.`;
}

function heuristicTags(path, fileCategory) {
  const tags = [];
  const p = path.replace(/\\/g, "/").toLowerCase();
  if (fileCategory === "docs") tags.push("documentation");
  if (fileCategory === "config") tags.push("configuration");
  if (p.includes("test")) tags.push("test");
  if (p.endsWith("__init__.py") || p.endsWith("cli.py") || p.includes("__main__")) tags.push("entry-point");
  if (p.includes("proxy")) tags.push("proxy");
  if (p.includes("platform_core") || p.includes("governance")) tags.push("governance");
  if (p.includes("backend")) tags.push("api-handler");
  if (tags.length === 0) tags.push("module");
  return tags.slice(0, 5);
}

function layerIdForPath(path) {
  const p = path.replace(/\\/g, "/");
  if (p.startsWith("windows_network_toolkit/")) return "toolkit-cli";
  if (p.startsWith("src/proxy_drift/") || p.startsWith("src/proxy_guard/")) return "proxy-drift";
  if (p.startsWith("src/platform_core/")) return "platform-core";
  if (p.startsWith("backend/")) return "backend-api";
  if (p.startsWith("docs/") || p.startsWith("AGENTS.md") || p === "README.md") return "docs";
  if (p.startsWith("scripts/")) return "scripts";
  if (p.startsWith("frontend/")) return "frontend";
  return "other";
}

function convertExtractToBatch(extract, batchIndex) {
  const nodes = [];
  const edges = [];
  const seen = new Set();

  for (const file of extract.results || []) {
    const path = file.path.replace(/\\/g, "/");
    const fileId = `file:${path}`;
    const nodeType = categoryNodeType(file.fileCategory || "code", path);
    const id =
      nodeType === "file"
        ? fileId
        : `${nodeType}:${path}`;
    if (!seen.has(id)) {
      seen.add(id);
      nodes.push({
        id,
        type: nodeType,
        name: basename(path),
        filePath: path,
        summary: heuristicSummary(path, file.fileCategory || "code", file.metrics || {}),
        tags: heuristicTags(path, file.fileCategory || "code"),
        complexity: complexityFromLines(file.nonEmptyLines || file.totalLines || 0),
      });
    }

    for (const fn of file.functions || []) {
      const lines = (fn.endLine || fn.startLine || 0) - (fn.startLine || 0) + 1;
      const exported = (file.exports || []).some((e) => e.name === fn.name);
      if (lines < 10 && !exported) continue;
      const fid = `function:${path}:${fn.name}`;
      if (seen.has(fid)) continue;
      seen.add(fid);
      nodes.push({
        id: fid,
        type: "function",
        name: fn.name,
        filePath: path,
        lineRange: [fn.startLine || 1, fn.endLine || fn.startLine || 1],
        summary: `Function ${fn.name} in ${path}.`,
        tags: exported ? ["exported"] : ["function"],
        complexity: complexityFromLines(lines),
      });
      edges.push({
        source: id,
        target: fid,
        type: "contains",
        direction: "forward",
        weight: 1,
        description: `${basename(path)} contains ${fn.name}`,
      });
    }

    for (const cls of file.classes || []) {
      const lines = (cls.endLine || cls.startLine || 0) - (cls.startLine || 0) + 1;
      const methods = (cls.methods || []).length;
      const exported = (file.exports || []).some((e) => e.name === cls.name);
      if (lines < 20 && methods < 2 && !exported) continue;
      const cid = `class:${path}:${cls.name}`;
      if (seen.has(cid)) continue;
      seen.add(cid);
      nodes.push({
        id: cid,
        type: "class",
        name: cls.name,
        filePath: path,
        lineRange: [cls.startLine || 1, cls.endLine || cls.startLine || 1],
        summary: `Class ${cls.name} in ${path}.`,
        tags: exported ? ["exported", "data-model"] : ["class"],
        complexity: complexityFromLines(lines),
      });
      edges.push({
        source: id,
        target: cid,
        type: "contains",
        direction: "forward",
        weight: 1,
        description: `${basename(path)} contains class ${cls.name}`,
      });
    }

    for (const call of file.callGraph || []) {
      if (!call.caller || !call.callee) continue;
      const src = `function:${path}:${call.caller}`;
      const tgt = `function:${path}:${call.callee}`;
      if (!seen.has(src) || !seen.has(tgt)) continue;
      edges.push({
        source: src,
        target: tgt,
        type: "calls",
        direction: "forward",
        weight: 0.7,
        description: `${call.caller} calls ${call.callee}`,
      });
    }
  }

  // Import edges from batchImportData if present on extract input — added later by caller
  return { batchIndex, nodes, edges };
}

function addImportEdges(batch, batchImportData) {
  for (const [srcPath, targets] of Object.entries(batchImportData || {})) {
    const srcId = `file:${srcPath.replace(/\\/g, "/")}`;
    for (const t of targets || []) {
      const tgtId = `file:${String(t).replace(/\\/g, "/")}`;
      batch.edges.push({
        source: srcId,
        target: tgtId,
        type: "imports",
        direction: "forward",
        weight: 0.8,
        description: `${srcPath} imports ${t}`,
      });
    }
  }
}

function finalizeGraph(assembled, scan) {
  const nodes = assembled.nodes || [];
  const edges = assembled.edges || [];
  const layerMap = new Map();
  const layerMeta = {
    "toolkit-cli": {
      name: "Toolkit CLI",
      description: "Primary windows_network_toolkit CLI and diagnostics",
    },
    "proxy-drift": {
      name: "Proxy Drift",
      description: "Startup observability, guardian, auto-fix, and proxy guard",
    },
    "platform-core": {
      name: "Platform Core",
      description: "Policy, classification, governance, and audit",
    },
    "backend-api": {
      name: "Backend API",
      description: "FastAPI /trisk and platform endpoints",
    },
    docs: { name: "Docs", description: "Operator and contributor documentation" },
    scripts: { name: "Scripts", description: "PowerShell/CMD operator wrappers" },
    frontend: { name: "Frontend", description: "Optional Next.js UI" },
    other: { name: "Other", description: "Remaining project files" },
  };

  for (const n of nodes) {
    if (!n.filePath) continue;
    const lid = layerIdForPath(n.filePath);
    if (!layerMap.has(lid)) layerMap.set(lid, []);
    layerMap.get(lid).push(n.id);
  }

  const layers = [...layerMap.entries()].map(([id, nodeIds]) => ({
    id,
    name: layerMeta[id]?.name || id,
    description: layerMeta[id]?.description || id,
    nodeIds,
  }));

  const pick = (pred) => nodes.find((n) => n.filePath && pred(n.filePath))?.id;
  const tour = [
    {
      order: 1,
      title: "Project overview",
      description: "Start with the README — evidence pipeline for Windows endpoint reliability.",
      nodeIds: [pick((p) => p === "README.md")].filter(Boolean),
    },
    {
      order: 2,
      title: "Proxy drift & auto-fix",
      description: "Active-but-broken detection and prefer-direct clear path live here.",
      nodeIds: [
        pick((p) => p.includes("proxy_drift/auto_fix.py")),
        pick((p) => p.includes("proxy_drift/classify.py")),
        pick((p) => p.includes("proxy_drift/ensure_health.py")),
      ].filter(Boolean),
    },
    {
      order: 3,
      title: "Safety & policy",
      description: "Policy gates and safety contracts keep remediation preview-only by default.",
      nodeIds: [
        pick((p) => p.includes("safety.py")),
        pick((p) => p.includes("platform_core") && p.includes("policy")),
      ].filter(Boolean),
    },
  ].filter((t) => t.nodeIds.length > 0);

  let commit = "unknown";
  try {
    const r = spawnSync("git", ["rev-parse", "HEAD"], { cwd: PROJECT_ROOT, encoding: "utf8" });
    if (r.status === 0) commit = r.stdout.trim();
  } catch {
    /* ignore */
  }

  const byLang = scan.stats?.byLanguage || {};
  const languages = Object.keys(byLang).length
    ? Object.keys(byLang)
    : ["python", "powershell", "markdown"];

  return {
    version: "1.0.0",
    kind: "codebase",
    project: {
      name: "windows-network-recovery-toolkit",
      languages,
      frameworks: ["fastapi", "pytest", "nicegui"],
      description:
        "Technology Risk & Control Analytics Platform for Windows endpoint evidence — proxy drift, TLS-path comparison, policy-gated remediation (structural UA graph).",
      analyzedAt: new Date().toISOString(),
      gitCommitHash: commit,
    },
    nodes,
    edges,
    layers,
    tour,
  };
}

async function main() {
  if (!existsSync(join(PLUGIN, "package.json"))) {
    throw new Error(`UA plugin not found at ${PLUGIN}`);
  }
  if (!existsSync(join(PLUGIN, "packages/core/dist/index.js"))) {
    throw new Error("Build UA core first: pnpm --filter @understand-anything/core build");
  }

  console.error(`[ua-structural] PROJECT_ROOT=${PROJECT_ROOT}`);
  console.error(`[ua-structural] UA plugin=${PLUGIN}`);
  ensureDirs();
  writeIgnore();

  // Phase 1 — scan
  const scanRawPath = join(TMP, "scan-raw.json");
  run("node", [
    join(SKILL, "scan-project.mjs"),
    PROJECT_ROOT,
    scanRawPath,
    "--exclude",
    EXCLUDE,
    "--exclude-analysis-data",
  ]);
  const scanRaw = JSON.parse(readFileSync(scanRawPath, "utf8"));
  console.error(`[ua-structural] scanned ${scanRaw.totalFiles} files (filtered ${scanRaw.filteredByIgnore})`);

  // Import map
  const importIn = join(TMP, "import-map-input.json");
  const importOut = join(TMP, "import-map-output.json");
  writeFileSync(
    importIn,
    JSON.stringify({ projectRoot: PROJECT_ROOT, files: scanRaw.files }, null, 2),
  );
  run("node", [join(SKILL, "extract-import-map.mjs"), importIn, importOut]);
  const importMapPayload = JSON.parse(readFileSync(importOut, "utf8"));
  const importMap = importMapPayload.importMap || {};

  const scanResult = {
    ...scanRaw,
    name: "windows-network-recovery-toolkit",
    description:
      "Windows endpoint reliability / technology risk evidence toolkit (structural analysis).",
    frameworks: ["fastapi", "pytest"],
    languages: Object.keys(scanRaw.stats?.byLanguage || { python: 1 }),
    importMap,
  };
  writeFileSync(join(INTER, "scan-result.json"), JSON.stringify(scanResult, null, 2));

  // Phase 1.5 — batches
  run("node", [join(SKILL, "compute-batches.mjs"), PROJECT_ROOT]);
  const batches = JSON.parse(readFileSync(join(INTER, "batches.json"), "utf8"));
  const batchList = batches.batches || [];
  console.error(`[ua-structural] ${batchList.length} batches, ${batches.totalFiles} files`);

  // Clear old batch files
  for (const f of readdirSync(INTER)) {
    if (/^batch-\d+/.test(f)) rmSync(join(INTER, f));
  }

  // Phase 2 — extract + convert
  for (const batch of batchList) {
    const idx = batch.batchIndex;
    const inputPath = join(TMP, `ua-file-analyzer-input-${idx}.json`);
    const extractPath = join(TMP, `ua-file-extract-results-${idx}.json`);
    writeFileSync(
      inputPath,
      JSON.stringify(
        {
          projectRoot: PROJECT_ROOT,
          batchFiles: batch.files || batch.batchFiles || [],
          batchImportData: batch.batchImportData || {},
        },
        null,
        2,
      ),
    );
    run("node", [join(SKILL, "extract-structure.mjs"), inputPath, extractPath]);
    const extract = JSON.parse(readFileSync(extractPath, "utf8"));
    const converted = convertExtractToBatch(extract, idx);
    addImportEdges(converted, batch.batchImportData || {});
    writeFileSync(join(INTER, `batch-${idx}.json`), JSON.stringify(converted, null, 2));
    console.error(
      `[ua-structural] batch ${idx}: ${converted.nodes.length} nodes, ${converted.edges.length} edges`,
    );
  }

  // Merge
  const pyCandidates = [
    join(PROJECT_ROOT, ".tools", "python312", "python.exe"),
    "python",
  ];
  let py = null;
  for (const c of pyCandidates) {
    const r = spawnSync(c, ["--version"], { encoding: "utf8" });
    if (r.status === 0) {
      py = c;
      break;
    }
  }
  if (!py) throw new Error("Python not found for merge-batch-graphs.py");
  run(py, [join(SKILL, "merge-batch-graphs.py"), PROJECT_ROOT]);

  const assembled = JSON.parse(readFileSync(join(INTER, "assembled-graph.json"), "utf8"));
  const graph = finalizeGraph(assembled, scanResult);
  writeFileSync(join(UA_DIR, "knowledge-graph.json"), JSON.stringify(graph, null, 2));
  writeFileSync(
    join(UA_DIR, "meta.json"),
    JSON.stringify(
      {
        gitCommitHash: graph.project.gitCommitHash,
        analyzedAt: graph.project.analyzedAt,
        mode: "structural-only",
        limitations: [
          "Generated without LLM semantic analysis — summaries/tags are heuristic.",
          "Re-run /understand in Cursor for full UA narrative quality.",
        ],
      },
      null,
      2,
    ),
  );

  console.error(
    `[ua-structural] Wrote ${graph.nodes.length} nodes, ${graph.edges.length} edges → .ua/knowledge-graph.json`,
  );
  console.error(`[ua-structural] Launch dashboard with:`);
  console.error(
    `  GRAPH_DIR=${PROJECT_ROOT} pnpm --dir ${uaRoot} --filter @understand-anything/dashboard dev`,
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
