import type {
  EvidenceSnapshotWire,
  LatestProfileReviewWire,
  PlayerProfilePageWire,
  PlayerProfileWire,
  ProductStateWire,
  RecentSummaryWire,
  RunWire,
  RunTimelineWire,
  TaskEventPageWire,
  TaskWire,
  TrainingPlanPageWire,
  TrainingProgressPageWire,
} from "../api/wire"
import type {
  TaskEventStreamCallbacks,
  TaskEventStreamHandle,
  TaskEventStreamState,
} from "../api/taskEventStream"
import {
  adaptEvidence,
  adaptPlayerProfile,
  adaptProductState,
  adaptRecentSummary,
  adaptRun,
  adaptTimeline,
  adaptTask,
  adaptTaskEvent,
  adaptTraining,
} from "./adapters"
import type {
  LiveWorkbenchScreenState,
  LiveWorkbenchView,
  WorkbenchClientMessageCode,
  WorkbenchCoachReport,
  WorkbenchEvidence,
  WorkbenchRecentSummary,
  WorkbenchRun,
  WorkbenchTimeline,
  WorkbenchTraining,
} from "./model"

const TERMINAL_STATUSES = new Set(["succeeded", "failed", "cancelled"])

export interface LiveWorkbenchDataApi {
  listProfiles(signal: AbortSignal): Promise<PlayerProfilePageWire>
  getLatest(profileId: string, signal: AbortSignal): Promise<LatestProfileReviewWire>
  getTask(taskId: string, runId: string, signal: AbortSignal): Promise<TaskWire>
  getEvents(taskId: string, runId: string, signal: AbortSignal): Promise<TaskEventPageWire>
  getProductState(taskId: string, runId: string, signal: AbortSignal): Promise<ProductStateWire>
  getRun(runId: string, signal: AbortSignal): Promise<RunWire | void>
  getSummary(runId: string, signal: AbortSignal): Promise<RecentSummaryWire | void>
  getTimeline(runId: string, signal: AbortSignal): Promise<RunTimelineWire | void>
  getReport(runId: string, signal: AbortSignal): Promise<string | void>
  getEvidence(taskId: string, runId: string, signal: AbortSignal): Promise<EvidenceSnapshotWire | void>
  getTrainingPlans(profileId: string, signal: AbortSignal): Promise<TrainingPlanPageWire>
  getTrainingProgress(profileId: string, signal: AbortSignal): Promise<TrainingProgressPageWire>
}

export interface LiveWorkbenchStreamBinding {
  readonly taskId: string
  readonly runId: string
  readonly afterCursor: number
}

export type LiveWorkbenchStreamFactory = (
  binding: LiveWorkbenchStreamBinding,
  callbacks: TaskEventStreamCallbacks,
) => TaskEventStreamHandle

export type LiveUpdateState = TaskEventStreamState

export interface LiveWorkbenchSnapshot {
  readonly state: LiveWorkbenchScreenState
  readonly liveUpdates: LiveUpdateState
}

export interface LiveWorkbenchControllerOptions {
  readonly api: LiveWorkbenchDataApi
  readonly streamFactory: LiveWorkbenchStreamFactory
  readonly initialProfileId?: string
}

interface SelectionBinding {
  readonly generation: number
  readonly profileId: string
  readonly taskId: string
  readonly runId: string
}

type Listener = () => void

function safeErrorCode(error: unknown): string {
  if (error !== null && typeof error === "object" && "code" in error) {
    const code = (error as { code?: unknown }).code
    if (typeof code === "string" && /^[a-z][a-z0-9_]{0,63}$/.test(code)) return code
  }
  return "live_workbench_unavailable"
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError"
}

export class LiveWorkbenchController {
  private readonly api: LiveWorkbenchDataApi
  private readonly streamFactory: LiveWorkbenchStreamFactory
  private readonly initialProfileId: string | undefined
  private readonly listeners = new Set<Listener>()
  private generation = 0
  private abortController: AbortController | undefined
  private stream: TaskEventStreamHandle | undefined
  private profiles: readonly PlayerProfileWire[] = []
  private binding: SelectionBinding | undefined
  private disposed = false
  private current: LiveWorkbenchSnapshot = {
    state: { client: "loading", messageCode: "profiles_loading" },
    liveUpdates: "closed",
  }

  constructor(options: LiveWorkbenchControllerOptions) {
    this.api = options.api
    this.streamFactory = options.streamFactory
    this.initialProfileId = options.initialProfileId
  }

  get snapshot(): LiveWorkbenchSnapshot {
    return this.current
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private update(next: LiveWorkbenchSnapshot): void {
    if (this.disposed) return
    this.current = next
    for (const listener of this.listeners) listener()
  }

  private updateLive(liveUpdates: LiveUpdateState): void {
    this.update({ ...this.current, liveUpdates })
  }

  private begin(messageCode: WorkbenchClientMessageCode): { generation: number; signal: AbortSignal } {
    this.generation += 1
    this.abortController?.abort()
    this.stream?.close()
    this.stream = undefined
    this.binding = undefined
    this.abortController = new AbortController()
    this.update({
      state: { client: "loading", messageCode },
      liveUpdates: "closed",
    })
    return { generation: this.generation, signal: this.abortController.signal }
  }

  private isCurrent(generation: number, profileId?: string): boolean {
    return !this.disposed
      && generation === this.generation
      && (profileId === undefined || this.binding?.profileId === profileId || this.binding === undefined)
  }

  private owns(binding: SelectionBinding): boolean {
    const current = this.binding
    return this.isCurrent(binding.generation)
      && current?.generation === binding.generation
      && current.profileId === binding.profileId
      && current.taskId === binding.taskId
      && current.runId === binding.runId
  }

  async start(): Promise<void> {
    const { generation, signal } = this.begin("profiles_loading")
    try {
      const page = await this.api.listProfiles(signal)
      if (!this.isCurrent(generation)) return
      this.profiles = page.profiles
      if (this.profiles.length === 0) {
        this.update({
          state: { client: "empty", messageCode: "profiles_empty" },
          liveUpdates: "closed",
        })
        return
      }
      const requested = this.initialProfileId === undefined
        ? undefined
        : this.profiles.find((profile) => profile.player_profile_id === this.initialProfileId)
      if (this.initialProfileId !== undefined && requested === undefined) {
        this.update({
          state: { client: "error", code: "player_profile_not_found", messageCode: "selected_profile_unavailable" },
          liveUpdates: "closed",
        })
        return
      }
      await this.loadProfile(requested ?? this.profiles[0]!, generation, signal)
    } catch (error) {
      this.handleFailure(error, generation)
    }
  }

  async selectProfile(profileId: string): Promise<void> {
    const { generation, signal } = this.begin("selected_review_loading")
    const profile = this.profiles.find((item) => item.player_profile_id === profileId)
    if (profile === undefined) {
      this.update({
        state: { client: "error", code: "player_profile_not_found", messageCode: "selected_profile_unavailable" },
        liveUpdates: "closed",
      })
      return
    }
    try {
      await this.loadProfile(profile, generation, signal)
    } catch (error) {
      this.handleFailure(error, generation)
    }
  }

  private async loadProfile(
    profile: PlayerProfileWire,
    generation: number,
    signal: AbortSignal,
  ): Promise<void> {
    const latest = await this.api.getLatest(profile.player_profile_id, signal)
    if (!this.isCurrent(generation)) return
    const adaptedProfiles = this.profiles.map(adaptPlayerProfile)
    const base: LiveWorkbenchView = {
      profiles: adaptedProfiles,
      selectedProfileId: profile.player_profile_id,
      events: [],
    }
    if (latest.latest_review === null) {
      const training = await this.loadTraining(profile, signal)
      if (!this.isCurrent(generation)) return
      this.update({
        state: { client: "ready", data: { ...base, ...(training === undefined ? {} : { training }) } },
        liveUpdates: "closed",
      })
      return
    }

    const binding: SelectionBinding = {
      generation,
      profileId: profile.player_profile_id,
      taskId: latest.latest_review.task_id,
      runId: latest.latest_review.run_id,
    }
    this.binding = binding
    const taskPromise = this.api.getTask(binding.taskId, binding.runId, signal)
    const productPromise = this.api.getProductState(binding.taskId, binding.runId, signal)
    const eventsPromise = this.api.getEvents(binding.taskId, binding.runId, signal)
    const trainingPromise = this.loadTraining(profile, signal)
    const [task, productState, eventPage, training] = await Promise.all([
      taskPromise,
      productPromise,
      eventsPromise,
      trainingPromise,
    ])
    if (!this.owns(binding)) return

    const controlView: LiveWorkbenchView = {
      ...base,
      task: adaptTask(task),
      productState: adaptProductState(productState),
      events: eventPage.events.map(adaptTaskEvent),
      ...(training === undefined ? {} : { training }),
    }
    const completeView = TERMINAL_STATUSES.has(task.status)
      ? await this.loadTerminalContent(binding, controlView, productState, signal)
      : controlView
    if (!this.owns(binding)) return
    this.update({ state: { client: "ready", data: completeView }, liveUpdates: "closed" })
    if (!TERMINAL_STATUSES.has(task.status)) this.openStream(binding, eventPage.next_cursor)
  }

  private async loadTraining(
    profile: PlayerProfileWire,
    signal: AbortSignal,
  ): Promise<WorkbenchTraining | undefined> {
    if (profile.relationship_role === "observed") return adaptTraining(profile, undefined, undefined)
    const plansPromise = this.api.getTrainingPlans(profile.player_profile_id, signal)
    const progressPromise = this.api.getTrainingProgress(profile.player_profile_id, signal)
    const [plans, progress] = await Promise.all([plansPromise, progressPromise])
    return adaptTraining(profile, plans, progress)
  }

  private async loadTerminalContent(
    binding: SelectionBinding,
    view: LiveWorkbenchView,
    productState: ProductStateWire,
    signal: AbortSignal,
  ): Promise<LiveWorkbenchView> {
    if (productState.state === "rejected" || productState.state === "not_ready") return view
    const runPromise = this.api.getRun(binding.runId, signal)
    const summaryPromise = this.api.getSummary(binding.runId, signal)
    const timelinePromise = this.api.getTimeline(binding.runId, signal)
    const reportPromise = this.api.getReport(binding.runId, signal)
    const evidencePromise = this.api.getEvidence(binding.taskId, binding.runId, signal).catch((error: unknown) => {
      if (
        productState.state === "degraded"
        && (safeErrorCode(error) === "evidence_not_available" || safeErrorCode(error) === "evidence_unavailable")
      ) {
        return undefined
      }
      throw error
    })
    const [run, summary, timeline, report, evidence] = await Promise.all([
      runPromise,
      summaryPromise,
      timelinePromise,
      reportPromise,
      evidencePromise,
    ])
    if (!this.owns(binding)) return view
    if (run === undefined || summary === undefined || timeline === undefined || report === undefined) {
      throw new Error("terminal content is unavailable")
    }
    if (productState.state === "published" && evidence === undefined) {
      throw new Error("published evidence is unavailable")
    }
    return {
      ...view,
      run: adaptRun(run) satisfies WorkbenchRun,
      summary: adaptRecentSummary(summary) satisfies WorkbenchRecentSummary,
      timeline: adaptTimeline(timeline) satisfies WorkbenchTimeline,
      report: { markdown: report } satisfies WorkbenchCoachReport,
      ...(evidence === undefined ? {} : { evidence: adaptEvidence(evidence) satisfies WorkbenchEvidence }),
    }
  }

  private openStream(binding: SelectionBinding, afterCursor: number): void {
    if (!this.owns(binding)) return
    this.stream?.close()
    const callbacks: TaskEventStreamCallbacks = {
      onEvent: (event) => {
        if (!this.owns(binding) || event.task_id !== binding.taskId || event.run_id !== binding.runId) return
        const state = this.current.state
        if (state.client !== "ready") return
        this.update({
          ...this.current,
          state: {
            client: "ready",
            data: { ...state.data, events: [...state.data.events, adaptTaskEvent(event)] },
          },
        })
      },
      onState: (state) => {
        if (this.owns(binding)) this.updateLive(state)
      },
      onTerminal: async (event) => {
        if (!this.owns(binding) || event.task_id !== binding.taskId || event.run_id !== binding.runId) return
        this.stream?.close()
        this.stream = undefined
        this.updateLive("closed")
        await this.reloadTerminal(binding)
      },
    }
    this.stream = this.streamFactory({
      taskId: binding.taskId,
      runId: binding.runId,
      afterCursor,
    }, callbacks)
  }

  private async reloadTerminal(binding: SelectionBinding): Promise<void> {
    const signal = this.abortController?.signal
    const state = this.current.state
    if (signal === undefined || state.client !== "ready" || !this.owns(binding)) return
    try {
      const taskPromise = this.api.getTask(binding.taskId, binding.runId, signal)
      const productPromise = this.api.getProductState(binding.taskId, binding.runId, signal)
      const [task, productState] = await Promise.all([taskPromise, productPromise])
      if (!this.owns(binding)) return
      const controlView: LiveWorkbenchView = {
        ...state.data,
        task: adaptTask(task),
        productState: adaptProductState(productState),
      }
      const completeView = await this.loadTerminalContent(binding, controlView, productState, signal)
      if (!this.owns(binding)) return
      this.update({ state: { client: "ready", data: completeView }, liveUpdates: "closed" })
    } catch (error) {
      this.handleFailure(error, binding.generation)
    }
  }

  private handleFailure(error: unknown, generation: number): void {
    if (!this.isCurrent(generation) || isAbort(error)) return
    this.update({
      state: {
        client: "error",
        code: safeErrorCode(error),
        messageCode: "workbench_load_failed",
      },
      liveUpdates: "closed",
    })
  }

  dispose(): void {
    if (this.disposed) return
    this.generation += 1
    this.abortController?.abort()
    this.stream?.close()
    this.stream = undefined
    this.binding = undefined
    this.current = { ...this.current, liveUpdates: "closed" }
    this.disposed = true
    this.listeners.clear()
  }
}
