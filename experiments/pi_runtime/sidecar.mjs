import { createInterface } from "node:readline";

import { Agent } from "@earendil-works/pi-agent-core";
import { createAssistantMessageEventStream } from "@earendil-works/pi-ai";

const PROTOCOL_VERSION = "1.0";
const PI_AGENT_CORE_VERSION = "0.84.2";
const MAX_FRAME_BYTES = 256 * 1024;
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const SAFE_CODE = /^[a-z0-9]+(?:[._-][a-z0-9]+)*$/;

const model = {
  id: "riftcoach-scripted-model",
  name: "RiftCoach Scripted Model",
  api: "pi-messages",
  provider: "riftcoach-scripted",
  baseUrl: "",
  reasoning: false,
  input: ["text"],
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
  contextWindow: 2_000_000,
  maxTokens: 16_000,
};

const input = createInterface({ input: process.stdin, crlfDelay: Infinity });
const inputIterator = input[Symbol.asyncIterator]();

let runId = null;
let request = null;
let scriptIndex = 0;
let providerAttempts = 0;
let responseUsages = [];
let toolOrdinal = 0;
let seenToolCalls = new Set();
let toolExecutions = [];
let forcedStop = null;

function stableStringify(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
}

function safeCode(value, fallback = "protocol_error") {
  return typeof value === "string" && SAFE_CODE.test(value) ? value : fallback;
}

function writeFrame(type, payload = {}) {
  if (!runId || !SAFE_ID.test(runId)) throw new Error("invalid_run_id");
  const frame = {
    protocol_version: PROTOCOL_VERSION,
    type,
    run_id: runId,
    ...payload,
  };
  const encoded = Buffer.from(`${stableStringify(frame)}\n`, "utf8");
  if (encoded.length > MAX_FRAME_BYTES) throw new Error("frame_too_large");
  process.stdout.write(encoded);
}

function parseFrame(line) {
  const encoded = Buffer.from(`${line}\n`, "utf8");
  if (encoded.length > MAX_FRAME_BYTES) throw new Error("frame_too_large");
  let frame;
  try {
    frame = JSON.parse(line);
  } catch {
    throw new Error("invalid_json");
  }
  if (!frame || typeof frame !== "object" || Array.isArray(frame)) throw new Error("invalid_frame");
  if (frame.protocol_version !== PROTOCOL_VERSION) throw new Error("protocol_version_mismatch");
  if (typeof frame.type !== "string") throw new Error("invalid_frame");
  if (typeof frame.run_id !== "string" || !SAFE_ID.test(frame.run_id)) throw new Error("invalid_run_id");
  if (runId !== null && frame.run_id !== runId) throw new Error("run_id_mismatch");
  return frame;
}

async function readFrame() {
  const next = await inputIterator.next();
  if (next.done) throw new Error("process_error");
  return parseFrame(next.value);
}

function usageFrom(value) {
  if (!value) return {
    input: 0,
    output: 0,
    cacheRead: 0,
    cacheWrite: 0,
    totalTokens: 0,
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
  };
  return {
    input: value.input_tokens,
    output: value.output_tokens,
    cacheRead: 0,
    cacheWrite: 0,
    totalTokens: value.input_tokens + value.output_tokens,
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
  };
}

function emptyAssistant(stopReason, errorCode = null) {
  return {
    role: "assistant",
    content: [{ type: "text", text: "" }],
    api: model.api,
    provider: model.provider,
    model: model.id,
    usage: usageFrom(null),
    stopReason,
    errorMessage: errorCode,
    timestamp: Date.now(),
  };
}

function emitFailure(stream, reason, errorCode) {
  const stopReason = reason === "provider_aborted" ? "aborted" : "error";
  const message = emptyAssistant(stopReason, errorCode);
  stream.push({ type: "start", partial: message });
  stream.push({
    type: "error",
    reason: stopReason,
    error: message,
  });
}

function emitProviderEvent(
  type,
  ordinal,
  iteration,
  success,
  failureCode = null,
  usage = null,
  finishReason = null,
) {
  writeFrame("event", {
    event: {
      event_type: type,
      ordinal,
      iteration,
      success,
      failure_code: failureCode,
      token_observation: usage ? "complete" : "unknown",
      finish_reason: finishReason,
      input_tokens: usage ? usage.input_tokens : null,
      output_tokens: usage ? usage.output_tokens : null,
    },
  });
}

function validateKnowledgeArguments(argumentsValue) {
  if (!argumentsValue || typeof argumentsValue !== "object" || Array.isArray(argumentsValue)) return false;
  if (typeof argumentsValue.query !== "string" || argumentsValue.query.trim().length === 0) return false;
  if (!Number.isInteger(argumentsValue.top_k) || argumentsValue.top_k < 1 || argumentsValue.top_k > 20) return false;
  const extra = Object.keys(argumentsValue).filter((key) => !["query", "top_k"].includes(key));
  return extra.length === 0;
}

function preflightToolBatch(step) {
  const calls = step.tool_calls ?? [];
  if (calls.length > 0 && providerAttempts >= request.policy.max_iterations) {
    return ["max_iterations", "max_iterations"];
  }
  if (toolExecutions.length + calls.length > request.policy.max_tool_calls) {
    return ["max_tool_calls", "max_tool_calls"];
  }
  const batch = new Set();
  for (const call of calls) {
    if (typeof call.id !== "string" || !SAFE_ID.test(call.id)) return ["protocol_error", "invalid_tool_call_id"];
    if (call.name !== "knowledge.search") return ["tool_not_allowed", "tool_not_allowed"];
    const signature = stableStringify({ name: call.name, arguments: call.arguments });
    if (batch.has(signature) || seenToolCalls.has(signature)) return ["duplicate_tool_call", "duplicate_tool_call"];
    if (!validateKnowledgeArguments(call.arguments)) return ["invalid_tool_input", "invalid_tool_input"];
    batch.add(signature);
  }
  return null;
}

function scriptedStreamFn(_model, context, options = {}) {
  const stream = createAssistantMessageEventStream();
  queueMicrotask(async () => {
    try {
      if (options.signal?.aborted) {
        forcedStop = ["provider_aborted", "scripted_provider_abort"];
        emitFailure(stream, forcedStop[0], forcedStop[1]);
        return;
      }
      if (forcedStop) {
        emitFailure(stream, forcedStop[0], forcedStop[1]);
        return;
      }
      if (providerAttempts >= request.policy.max_iterations) {
        forcedStop = ["max_iterations", "max_iterations"];
        emitFailure(stream, forcedStop[0], forcedStop[1]);
        return;
      }
      providerAttempts += 1;
      const ordinal = providerAttempts;
      const step = request.script[scriptIndex++];
      emitProviderEvent(
        "provider_started",
        ordinal,
        ordinal,
        true,
        null,
        null,
        null,
      );
      if (!step) {
        responseUsages.push(null);
        emitProviderEvent(
          "provider_completed",
          ordinal,
          ordinal,
          false,
          "scripted_provider_error",
          null,
          null,
        );
        forcedStop = ["provider_error", "scripted_provider_error"];
        emitFailure(stream, forcedStop[0], forcedStop[1]);
        return;
      }
      if (step.kind === "provider_error" || step.kind === "provider_abort") {
        responseUsages.push(null);
        const reason = step.kind === "provider_abort" ? "provider_aborted" : "provider_error";
        emitProviderEvent(
          "provider_completed",
          ordinal,
          ordinal,
          false,
          step.error_code,
          null,
          null,
        );
        forcedStop = [reason, step.error_code];
        emitFailure(stream, forcedStop[0], forcedStop[1]);
        return;
      }

      responseUsages.push(step.usage ?? null);
      const preflightError = preflightToolBatch(step);
      if (preflightError) {
        emitProviderEvent(
          "provider_completed",
          ordinal,
          ordinal,
          true,
          preflightError[1],
          step.usage ?? null,
          step.tool_calls?.length ? "tool_calls" : "stop",
        );
        forcedStop = preflightError;
        emitFailure(stream, forcedStop[0], forcedStop[1]);
        return;
      }
      for (const call of step.tool_calls ?? []) {
        seenToolCalls.add(stableStringify({ name: call.name, arguments: call.arguments }));
      }
      emitProviderEvent(
        "provider_completed",
        ordinal,
        ordinal,
        true,
        null,
        step.usage ?? null,
        step.tool_calls?.length ? "tool_calls" : "stop",
      );
      const content = [];
      if (step.content) content.push({ type: "text", text: step.content });
      for (const call of step.tool_calls ?? []) {
        content.push({
          type: "toolCall",
          id: call.id,
          name: call.name,
          arguments: call.arguments,
        });
      }
      const message = {
        role: "assistant",
        content,
        api: model.api,
        provider: model.provider,
        model: model.id,
        usage: usageFrom(step.usage),
        stopReason: step.tool_calls?.length ? "toolUse" : "stop",
        timestamp: Date.now(),
      };
      stream.push({ type: "start", partial: message });
      stream.push({
        type: "done",
        reason: message.stopReason,
        message,
      });
    } catch (error) {
      forcedStop = ["process_error", "process_error"];
      emitFailure(stream, "provider_error", "process_error");
    }
  });
  return stream;
}

async function makeKnowledgeTool() {
  const declared = request.allowed_tools[0];
  return {
    name: declared.name,
    label: "RiftCoach Knowledge Search",
    description: declared.description,
    parameters: declared.input_schema,
    executionMode: "sequential",
    execute: async (toolCallId, argumentsValue, signal) => {
      if (signal?.aborted) throw new Error("timeout");
      const ordinal = ++toolOrdinal;
      writeFrame("event", {
        event: {
          event_type: "tool_started",
          ordinal,
          iteration: providerAttempts,
          success: null,
          tool_name: "knowledge.search",
          tool_version: "2.0.0",
        },
      });
      writeFrame("tool.request", {
        request_id: toolCallId,
        ordinal,
        name: "knowledge.search",
        arguments: argumentsValue,
      });
      const response = await readFrame();
      if (response.type !== "tool.response" || response.request_id !== toolCallId || response.ordinal !== ordinal) {
        throw new Error("tool_response_mismatch");
      }
      const result = response.result;
      if (!result || typeof result !== "object") throw new Error("invalid_tool_response");
      const projection = {
        tool_name: result.tool_name,
        tool_version: result.tool_version,
        ordinal,
        success: Boolean(result.success),
        failure_code: result.error_code ? safeCode(result.error_code, "tool_failed") : null,
        attempts: Number.isInteger(result.attempts) ? result.attempts : 0,
        latency_ms: typeof result.latency_ms === "number" ? result.latency_ms : 0,
        cached: Boolean(result.cached),
        fallback_used: Boolean(result.fallback_used),
      };
      toolExecutions.push(projection);
      emitToolEvent("tool_completed", projection);
      if (!projection.success) throw new Error(projection.failure_code || "tool_failed");
      return {
        content: [{ type: "text", text: JSON.stringify({ success: true, data: result.data ?? null }) }],
        details: { success: true },
      };
    },
  };
}

function emitToolEvent(type, projection) {
  writeFrame("event", {
    event: {
      event_type: type,
      ordinal: projection.ordinal,
      iteration: providerAttempts,
      success: projection.success,
      tool_name: projection.tool_name,
      tool_version: projection.tool_version,
      failure_code: projection.failure_code,
    },
  });
}

function assistantText(message) {
  if (!message || message.role !== "assistant" || !Array.isArray(message.content)) return null;
  const text = message.content.filter((part) => part.type === "text").map((part) => part.text).join("").trim();
  return text || null;
}

async function run() {
  const start = await readFrame();
  if (start.type !== "run.start" || !start.request || typeof start.request !== "object") throw new Error("invalid_start");
  runId = start.run_id;
  request = start.request;
  if (request.protocol_version !== PROTOCOL_VERSION || request.pi_agent_core_version !== PI_AGENT_CORE_VERSION) throw new Error("protocol_version_mismatch");
  if (!Array.isArray(request.allowed_tools) || request.allowed_tools.length !== 1 || request.allowed_tools[0].name !== "knowledge.search") throw new Error("tool_not_allowed");
  if (!Array.isArray(request.messages) || request.messages.length !== 1 || request.messages[0].role !== "user") throw new Error("invalid_start");

  const knowledgeTool = await makeKnowledgeTool();
  const agent = new Agent({
    initialState: {
      systemPrompt: request.system_prompt,
      model,
      messages: [],
      tools: [knowledgeTool],
    },
    streamFn: scriptedStreamFn,
    toolExecution: "sequential",
    transformContext: async (messages) => {
      const chars = JSON.stringify({ systemPrompt: request.system_prompt, messages }).length;
      if (chars > request.policy.max_context_chars && !forcedStop) forcedStop = ["context_budget_exceeded", "context_budget_exceeded"];
      return messages;
    },
  });
  agent.subscribe(async (event) => {
    if (event.type === "agent_end") {
      const final = event.messages[event.messages.length - 1];
      const success = final?.role === "assistant" && final.stopReason === "stop";
      writeFrame("event", {
        event: {
          event_type: "agent_completed",
          ordinal: 1,
          iteration: providerAttempts,
          success,
          failure_code: success ? null : safeCode(forcedStop?.[1] ?? "process_error"),
        },
      });
    }
  });

  await agent.prompt({
    role: "user",
    content: [{ type: "text", text: request.messages[0].content }],
    timestamp: Date.now(),
  });
  const final = agent.state.messages[agent.state.messages.length - 1];
  const forced = forcedStop;
  const text = assistantText(final);
  const status = forced
    ? (forced[0] === "max_tool_calls" || forced[0] === "max_iterations" || forced[0] === "duplicate_tool_call" || forced[0] === "context_budget_exceeded" || forced[0] === "provider_aborted" ? "stopped" : "failed")
    : (final?.stopReason === "stop" ? "completed" : final?.stopReason === "aborted" ? "stopped" : "failed");
  const stopReason = forced?.[0]
    ?? (status === "completed" ? "final_response" : final?.stopReason === "aborted" ? "provider_aborted" : "provider_error");
  writeFrame("run.result", {
    result: {
      status,
      stop_reason: stopReason,
      iterations: providerAttempts,
      final_text: status === "completed" ? text : null,
      error_code: status === "completed" ? null : safeCode(forced?.[1] ?? "provider_error"),
      provider_calls_attempted: providerAttempts,
      response_usages: responseUsages,
      tool_executions: toolExecutions,
    },
  });
}

run().catch((error) => {
  const code = safeCode(error?.message, "process_error");
  if (runId && SAFE_ID.test(runId)) {
    try {
      writeFrame("protocol.error", { error_code: code });
    } catch {
      // The parent will classify a missing/invalid frame as process_error.
    }
  }
  process.exitCode = 1;
});
