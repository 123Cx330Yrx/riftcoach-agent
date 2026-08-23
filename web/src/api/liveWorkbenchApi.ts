import {
  decodeEvidence,
  decodeLatestProfileReview,
  decodePlayerProfilePage,
  decodeProductState,
  decodeRecentSummary,
  decodeReport,
  decodeRun,
  decodeTask,
  decodeTaskEventPage,
  decodeTrainingPlanPage,
  decodeTrainingProgressPage,
} from "./decoders"
import { ApiClient } from "./client"
import type { LiveWorkbenchDataApi } from "../workbench/liveController"

function segment(value: string): string {
  return encodeURIComponent(value)
}

export class LiveWorkbenchHttpApi implements LiveWorkbenchDataApi {
  constructor(private readonly client: ApiClient) {}

  listProfiles(signal: AbortSignal) {
    return this.client.getJson("/player-profiles?limit=50", decodePlayerProfilePage, signal)
  }

  getLatest(profileId: string, signal: AbortSignal) {
    return this.client.getJson(
      `/player-profiles/${segment(profileId)}/reviews/recent/latest`,
      (value) => decodeLatestProfileReview(value, profileId),
      signal,
    )
  }

  getTask(taskId: string, runId: string, signal: AbortSignal) {
    return this.client.getJson(
      `/tasks/${segment(taskId)}`,
      (value) => decodeTask(value, { taskId, runId }),
      signal,
    )
  }

  getEvents(taskId: string, runId: string, signal: AbortSignal) {
    return this.client.getJson(
      `/tasks/${segment(taskId)}/events?after_cursor=0&limit=50`,
      (value) => decodeTaskEventPage(value, { taskId, runId }),
      signal,
    )
  }

  getProductState(taskId: string, runId: string, signal: AbortSignal) {
    return this.client.getJson(
      `/runs/${segment(runId)}/product-state`,
      (value) => decodeProductState(value, { taskId, runId }),
      signal,
    )
  }

  getRun(runId: string, signal: AbortSignal) {
    return this.client.getJson(
      `/runs/${segment(runId)}`,
      (value) => decodeRun(value, runId),
      signal,
    )
  }

  getSummary(runId: string, signal: AbortSignal) {
    return this.client.getJson(
      `/runs/${segment(runId)}/recent-summary`,
      (value) => decodeRecentSummary(value, runId),
      signal,
    )
  }

  getReport(runId: string, signal: AbortSignal) {
    return this.client.getText(`/runs/${segment(runId)}/report`, decodeReport, signal)
  }

  getEvidence(taskId: string, runId: string, signal: AbortSignal) {
    return this.client.getJson(
      `/runs/${segment(runId)}/evidence`,
      (value) => decodeEvidence(value, { taskId, runId }),
      signal,
    )
  }

  getTrainingPlans(profileId: string, signal: AbortSignal) {
    return this.client.getJson(
      `/memory/players/${segment(profileId)}/training-plan?include_history=false&limit=50`,
      (value) => decodeTrainingPlanPage(value, profileId),
      signal,
    )
  }

  getTrainingProgress(profileId: string, signal: AbortSignal) {
    return this.client.getJson(
      `/memory/players/${segment(profileId)}/training-progress?include_history=false&limit=50`,
      (value) => decodeTrainingProgressPage(value, profileId),
      signal,
    )
  }
}
