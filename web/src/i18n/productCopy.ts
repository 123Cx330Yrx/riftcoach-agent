import type {
  PublicationStatusWire,
  RoutingRegionWire,
  TaskEventKindWire,
  TaskStatusWire,
  VerificationStatusWire,
} from "../api/wire"
import type { MessageKey } from "./locale"

export const eventMessageKeys: Readonly<Record<TaskEventKindWire, MessageKey>> = {
  created: "event.created",
  claimed: "event.claimed",
  execution_started: "event.execution_started",
  heartbeat: "event.heartbeat",
  cancel_requested: "event.cancel_requested",
  checkpoint_saved: "event.checkpoint_saved",
  recovery_required: "event.recovery_required",
  requeued: "event.requeued",
  succeeded: "event.succeeded",
  failed: "event.failed",
  cancelled: "event.cancelled",
}

export const taskStatusMessageKeys: Readonly<Record<TaskStatusWire, MessageKey>> = {
  queued: "status.queued",
  running: "status.running",
  recovery_required: "status.recovery_required",
  succeeded: "status.succeeded",
  failed: "status.failed",
  cancelled: "status.cancelled",
}

export const publicationMessageKeys: Readonly<Record<PublicationStatusWire, MessageKey>> = {
  published: "publication.published",
  degraded: "publication.degraded",
  rejected: "publication.rejected",
}

export const verificationMessageKeys: Readonly<Record<VerificationStatusWire, MessageKey>> = {
  unverified_claim: "profile.verification.unverified_claim",
  not_applicable: "profile.verification.not_applicable",
  rso_verified: "profile.verification.rso_verified",
}

export const regionMessageKeys: Readonly<Record<RoutingRegionWire, MessageKey>> = {
  americas: "region.americas",
  europe: "region.europe",
  asia: "region.asia",
  sea: "region.sea",
}
