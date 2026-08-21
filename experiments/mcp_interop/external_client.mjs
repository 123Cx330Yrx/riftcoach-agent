import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import {
  LATEST_PROTOCOL_VERSION,
  SUPPORTED_PROTOCOL_VERSIONS,
} from "@modelcontextprotocol/sdk/types.js";


const EXPECTED_PACKAGE = "@modelcontextprotocol/sdk";
const EXPECTED_VERSION = "1.30.0";
const EXPECTED_LICENSE = "MIT";
const EXPECTED_PROTOCOL = "2025-06-18";
const EXPECTED_TOOLS = [
  "riftcoach.knowledge_search",
  "riftcoach.recent_summary",
  "riftcoach.report_evaluation",
  "riftcoach.single_match_review",
];
const SELECTED_TOOL = "riftcoach.knowledge_search";
const TIMEOUT_MS = 10_000;


function assertCondition(condition, code) {
  if (!condition) {
    throw new Error(code);
  }
}


function canonical(value) {
  if (Array.isArray(value)) {
    return value.map(canonical);
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, canonical(value[key])]),
    );
  }
  return value;
}


function digest(value) {
  return createHash("sha256")
    .update(JSON.stringify(canonical(value)), "utf8")
    .digest("hex");
}


function parseArgs(argv) {
  const values = new Map();
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    assertCondition(key?.startsWith("--") && value, "invalid_arguments");
    assertCondition(!values.has(key), "duplicate_argument");
    values.set(key, value);
  }
  assertCondition(values.size === 2, "invalid_arguments");
  const python = values.get("--python");
  const repoRoot = values.get("--repo-root");
  assertCondition(path.isAbsolute(python), "python_must_be_absolute");
  assertCondition(path.isAbsolute(repoRoot), "repo_root_must_be_absolute");
  return { python, repoRoot };
}


function minimalChildEnv() {
  const env = { PYTHONIOENCODING: "utf-8", PYTHONUTF8: "1" };
  for (const key of ["SYSTEMROOT", "WINDIR"]) {
    if (process.env[key]) {
      env[key] = process.env[key];
    }
  }
  return env;
}


class BodyFreeTraceTransport {
  constructor(delegate) {
    this.delegate = delegate;
    this.events = [];
    this.pending = new Map();
    this.negotiatedProtocol = null;
    this.serverInfo = null;
    delegate.onclose = () => this.onclose?.();
    delegate.onerror = (error) => this.onerror?.(error);
    delegate.onmessage = (message) => {
      this.observeInbound(message);
      this.onmessage?.(message);
    };
  }

  async start() {
    await this.delegate.start();
  }

  async close() {
    await this.delegate.close();
  }

  async send(message) {
    if (typeof message?.method === "string") {
      const kind = Object.hasOwn(message, "id") ? "request" : "notification";
      this.events.push({ direction: "client_to_server", kind, method: message.method });
      if (kind === "request") {
        this.pending.set(message.id, message.method);
      }
    }
    await this.delegate.send(message);
  }

  observeInbound(message) {
    if (!Object.hasOwn(message ?? {}, "id")) {
      this.events.push({ direction: "server_to_client", kind: "unexpected" });
      return;
    }
    const method = this.pending.get(message.id) ?? "unknown";
    this.pending.delete(message.id);
    const status = Object.hasOwn(message, "result") ? "success" : "error";
    this.events.push({ direction: "server_to_client", kind: "response", method, status });
    if (method === "initialize" && status === "success") {
      this.negotiatedProtocol = message.result?.protocolVersion ?? null;
      this.serverInfo = message.result?.serverInfo ?? null;
    }
  }

  counts() {
    const outbound = this.events.filter((event) => event.direction === "client_to_server");
    return {
      initialize_calls: outbound.filter((event) => event.method === "initialize").length,
      initialized_notifications: outbound.filter(
        (event) => event.method === "notifications/initialized",
      ).length,
      tools_list_calls: outbound.filter((event) => event.method === "tools/list").length,
      tools_call_calls: outbound.filter((event) => event.method === "tools/call").length,
      response_count: this.events.filter((event) => event.kind === "response").length,
    };
  }
}


function assertBodySafe(value) {
  const forbiddenKeys = new Set([
    "owner_id",
    "puuid",
    "key",
    "authorization",
    "prompt",
    "path",
    "raw_body",
  ]);
  const visit = (item) => {
    if (Array.isArray(item)) {
      item.forEach(visit);
      return;
    }
    if (item !== null && typeof item === "object") {
      for (const [key, child] of Object.entries(item)) {
        assertCondition(!forbiddenKeys.has(key.toLowerCase()), "unsafe_result_key");
        visit(child);
      }
    }
  };
  visit(value);
}


async function packageIdentity() {
  const packageJson = JSON.parse(
    await readFile(
      new URL("./node_modules/@modelcontextprotocol/sdk/package.json", import.meta.url),
      "utf8",
    ),
  );
  const lock = JSON.parse(
    await readFile(new URL("./package-lock.json", import.meta.url), "utf8"),
  );
  const locked = lock.packages?.["node_modules/@modelcontextprotocol/sdk"];
  assertCondition(packageJson.name === EXPECTED_PACKAGE, "package_identity_mismatch");
  assertCondition(packageJson.version === EXPECTED_VERSION, "package_version_mismatch");
  assertCondition(packageJson.license === EXPECTED_LICENSE, "package_license_mismatch");
  assertCondition(locked?.version === EXPECTED_VERSION, "lock_version_mismatch");
  assertCondition(typeof locked?.integrity === "string", "lock_integrity_missing");
  return { integrity: locked.integrity };
}


async function run() {
  const startedAt = new Date().toISOString();
  const { python, repoRoot } = parseArgs(process.argv.slice(2));
  const identity = await packageIdentity();
  assertCondition(
    SUPPORTED_PROTOCOL_VERSIONS.includes(EXPECTED_PROTOCOL),
    "sdk_protocol_support_missing",
  );

  const base = new StdioClientTransport({
    command: python,
    args: ["-m", "scripts.run_riftcoach_mcp_stdio_server"],
    cwd: repoRoot,
    env: minimalChildEnv(),
    stderr: "pipe",
    maxBufferSize: 256 * 1024,
  });
  let stderrBytes = 0;
  base.stderr?.on("data", (chunk) => {
    stderrBytes += chunk.length;
  });
  const transport = new BodyFreeTraceTransport(base);
  const client = new Client(
    { name: "riftcoach-stage7-external-client", version: "1.0.0" },
    { capabilities: {} },
  );

  let tools;
  let call;
  try {
    await client.connect(transport, { timeout: TIMEOUT_MS, maxTotalTimeout: TIMEOUT_MS });
    assertCondition(transport.negotiatedProtocol === EXPECTED_PROTOCOL, "protocol_mismatch");
    assertCondition(
      transport.serverInfo?.name === "RiftCoach MCP Server" &&
        transport.serverInfo?.version === "1.0.0",
      "server_identity_mismatch",
    );
    tools = await client.listTools({}, { timeout: TIMEOUT_MS, maxTotalTimeout: TIMEOUT_MS });
    const names = tools.tools.map((tool) => tool.name).sort();
    assertCondition(JSON.stringify(names) === JSON.stringify(EXPECTED_TOOLS), "catalog_mismatch");
    const selected = tools.tools.find((tool) => tool.name === SELECTED_TOOL);
    assertCondition(selected !== undefined, "selected_tool_missing");
    call = await client.callTool(
      {
        name: SELECTED_TOOL,
        arguments: { query: "bounded interop query", top_k: 1 },
      },
      undefined,
      { timeout: TIMEOUT_MS, maxTotalTimeout: TIMEOUT_MS },
    );
    assertCondition(call.isError !== true, "tool_call_failed");
    assertCondition(call.structuredContent?.provider === "interop-fixture", "result_invalid");
    assertCondition(call.structuredContent?.count === 1, "result_invalid");
    assertBodySafe(call.structuredContent);
  } finally {
    await client.close();
  }

  assertCondition(stderrBytes === 0, "server_stderr_not_empty");
  const counts = transport.counts();
  assertCondition(
    counts.initialize_calls === 1 &&
      counts.initialized_notifications === 1 &&
      counts.tools_list_calls === 1 &&
      counts.tools_call_calls === 1 &&
      counts.response_count === 3,
    "unexpected_protocol_call_count",
  );
  const selected = tools.tools.find((tool) => tool.name === SELECTED_TOOL);
  return {
    schema_version: "1.0",
    result: "passed",
    body_free: true,
    observed_window_utc: { started_at: startedAt, ended_at: new Date().toISOString() },
    client: {
      package: EXPECTED_PACKAGE,
      version: EXPECTED_VERSION,
      integrity: identity.integrity,
      license: EXPECTED_LICENSE,
      implementation_name: "riftcoach-stage7-external-client",
      transport: "stdio",
      offered_protocol_version: LATEST_PROTOCOL_VERSION,
    },
    server: {
      name: transport.serverInfo.name,
      version: transport.serverInfo.version,
      protocol_version: transport.negotiatedProtocol,
    },
    catalog: {
      tool_count: tools.tools.length,
      digest: digest(
        tools.tools.map((tool) => ({
          name: tool.name,
          inputSchema: tool.inputSchema,
          outputSchema: tool.outputSchema ?? null,
          annotations: tool.annotations ?? null,
        })),
      ),
      selected_tool: SELECTED_TOOL,
      selected_tool_schema_digest: digest({
        inputSchema: selected.inputSchema,
        outputSchema: selected.outputSchema ?? null,
      }),
    },
    call: {
      tool: SELECTED_TOOL,
      result_digest: digest(call.structuredContent),
      is_error: false,
      attribution_count: call.structuredContent.count,
    },
    trace: { digest: digest(transport.events), ...counts },
    external_io: {
      riftcoach_tools_call_calls: 1,
      opgg_tools_call_calls: 0,
      riot_calls: 0,
      llm_provider_calls: 0,
      key_reads: 0,
    },
    limitations: [
      "no_public_network_deployment",
      "no_production_auth_or_actor_bootstrap",
      "no_database_or_provider_io",
    ],
  };
}


try {
  const summary = await run();
  process.stdout.write(`${JSON.stringify(summary)}\n`);
} catch {
  process.stderr.write("mcp_interop_external_client_failed\n");
  process.exitCode = 1;
}
