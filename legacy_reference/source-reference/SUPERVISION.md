# Collection supervision contract

`run_investment_sync.ps1` keeps its existing collection parameters. It now launches
`run_investment_sync_worker.ps1` under a separate process-tree supervisor. Do not
invoke the worker directly. No schedules or delivery actions are enabled by this change.

## Timing

- `TotalTimeoutSeconds` is the supervised work budget, starting immediately before
  worker launch. It covers worker startup, path/config initialization, worker
  `Add-Type`, source requests, checkpoint reads, result writes and worker cleanup.
- Supervisor preparation (including its own `Add-Type`) occurs before that budget.
  Its `preparation_seconds` is reported separately. A process cannot supervise its
  own bootstrap before its watchdog exists.
- Sources share the remaining budget in fractional seconds, converted to milliseconds
  at the process boundary. Up to two attempts share the same source deadline.
  Cleanup time consumes remaining time; a failure cannot reset the global deadline.
- Deadline cancellation has a fixed 500 ms cleanup confirmation grace. The helper
  queries Job Object active-process accounting, rather than treating a successful
  termination request as proof of exit. An unfinished launcher is unconfirmed.
- Supervisor final diagnostic writes and OS/kernel scheduling are not hard-real-time
  bounded. Returned JSON includes observed diagnostic and total timings. Persistent
  manifests record the supervised/preparation/cleanup measurements and explicitly
  mark the diagnostic timing as measured before their own write.
- Do not promise that the whole shell command always returns in exactly N seconds,
  or that a stalled OS/storage driver is covered by a user-mode timing guarantee.

## Status and checkpoints

- Read `work/sync-supervision-manifest.json` and `work/sync-execution-manifest.json`
  together. Require matching `collection_key` and `run_key`. The GUID-named
  `supervision-<collection_key>.json` preserves each terminal supervision result.
- Exit 0 means the worker returned normally. It does **not** prove source completeness:
  inspect per-source status and the exact-window coverage/reading gate separately.
  The supervisor deliberately never sets `business_complete=true`.
- Exit 124 / `total_timeout`: the global work deadline fired.
- Exit 125 / `cleanup_unconfirmed` or `worker_cleanup_unconfirmed`: cleanup could
  not be confirmed at one layer. The worker stops retries and subsequent sources;
  the outer supervisor independently drains its whole tree. Preserve the failure
  even when outer cleanup subsequently succeeds.
- Other nonzero exits are launch/worker failures. Do not publish a complete report.
- Exit 126 / `worker_isolation_failed`: containment/startup failed before source
  execution. No retry or subsequent source starts; no terminal completion is published.
- `check_report_coverage.py` machine-enforces the joint gate via `collection_gate.py`.
  Supply `--collection-key` from the current supervisor return, `--run-key`,
  `--supervision work/sync-supervision-manifest.json`, and
  `--execution work/sync-execution-manifest.json` in addition to existing snapshot
  and window arguments. It requires both identities to match the explicit expected
  current invocation, successful/drained supervision, completed source execution,
  and snapshot identities. Missing arguments/manifests, stale complete checkpoints,
  timeouts and unconfirmed cleanup fail closed. Exact-window/reading checks still apply.
- Worker manifests use a same-directory temporary file then rename. Partial runs
  have `execution_complete=false`; only normal completion commits the terminal
  execution marker. On forced termination the supervisor does not replace the last
  committed checkpoint with an invented empty source list. A previous collection's
  manifest can remain present, so identity matching is mandatory.
- No whole-run automatic retry occurs. Existing same-collection checkpoint retry
  stays inside the source quota. A new invocation has a new collection identity.

## Isolated acceptance

`test_global_supervision.ps1`, `test_bounded_source.ps1` and `test_sync_wrapper.ps1`
write only under project `diagnostics/acceptance`. The global test uses synthetic
scripts and explicitly gated fault JSON; there is no live source/network access.
`FaultInjectionPath` is allowed only with an acceptance root and explicit scripts
inside the project's acceptance tree. It supports finite phase delays, an actual
partial temporary manifest, a delayed launcher, and an intentionally overrunning
local wait to prove independence of the outer deadline. It is not a production mode.

The acceptance verifies actual worker/source/child/grandchild PID records, active
process count zero, no delayed writes, preservation of the previous complete
checkpoint, same-run recovery, fresh-run idempotency, retry exhaustion and later
source opportunity. Injected IO-stage delays do not claim to reproduce a stuck
kernel filesystem operation. Each run preserves its own evidence directory.

Acceptance-only `source_native_fault` accepts `job_attribute`, `resume`, or
`cleanup_query`. These are controlled local failure-branch injections, not observed
Windows API failures: no API patching, permission changes or OS fault claims.
The resume case creates a real suspended, job-contained process and prevents its
execution. The query case terminates/closes a real job but deliberately withholds
confirmation, so pipeline retry/completion must stop. Tests inspect real PIDs,
late writes, successful native handle closes and exclusive output-file reopening.

The containment uses Windows process creation's job-list attribute and kill-on-close
jobs. Cleanup confirmation uses
[QueryInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject)
and [active-process accounting](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information).
