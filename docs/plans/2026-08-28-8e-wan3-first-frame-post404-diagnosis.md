# Wan 3.0 first-frame reopen: HTTP 404 diagnosis

Date: 2026-08-28  
Checkpoint: `8e-productization / portal-motion-polish / Wan3 official first-frame reopen`

## Observed result

The user launched the frozen runner with the correct source and prompt digests,
but pasted the OpenAI-compatible text endpoint
`https://dashscope.aliyuncs.com/compatible-mode/v1` as the video endpoint. The
runner appended the Wan video path to that URL and received HTTP 404. The local
status record is `post_failed`, contains no `task_id`, and no result file exists.
This is a request-routing failure before model execution, not a Wan visual
result and not evidence about prompt quality.

## Root cause and fix

Model Studio exposes different protocol paths under the same API Host. The
OpenAI-compatible path is for compatible text APIs; Wan 3.0 uses the asynchronous
`/api/v1/services/aigc/video-generation/video-synthesis` path and polls
`/api/v1/tasks/{task_id}`. The first runner accepted a full URL but did not
normalize a compatible-mode URL back to the API Host.

The corrected runner now parses the supplied URL, rejects non-HTTPS and
non-Alibaba hosts, keeps only the scheme and authority, and reconstructs both
the exact video POST path and the task GET path. It also accepts Markdown link
syntax because the first pasted value included a rendered link. PowerShell
parse errors are 0, task-creation POST paths are exactly 1, and the corrected
runner SHA is
`9853a289b9e1e05c06d9aee14044e6d7212599d4fbfde031ebd813dea00a9924`.

Before the corrected POST, the prompt was rechecked against the official Wan
image-to-video prompt guide. The image remains responsible for entity, scene
and style; the text focuses on motion plus a fixed camera. The brief now starts
with the guide's explicit `Generate single shot. Fixed camera.` wording and
expresses the 12-second rhythm as one continuous action instead of timestamped
segments that could be mistaken for a multi-shot prompt. `prompt_extend=false`
remains intentional because this is already a structured precision prompt.

## Retry boundary

One corrected task-creation POST is allowed after this diagnosis obtains its
exact-SHA public gate. It is not a duplicate model task because the first
attempt returned 404 with no task ID. The corrected run must use the same
source, prompt and parameters; it may not silently change model, duration,
resolution or motion contract. A second task ID or any successful result must
enter the normal visual audit before runtime adoption.
