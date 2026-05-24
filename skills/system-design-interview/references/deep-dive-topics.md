# Universal Backend System Design — Deep Dive Only Prompt (L6/Senior)

> **Scope:** This is **ONLY** the deep-dive portion of a system design interview.
> **Out of scope:** requirements gathering, product clarification, high-level architecture exploration.
> **Goal:** stress-test the candidate's *already-proposed* design with production-grade engineering depth.

---

## 1) Read-Aloud Deep Dive Prompt (Interviewer Script)

> "Let's assume your high-level design is decided. We won't spend time on requirements or redesigning the architecture.
> From here, we'll do a **deep dive**: I'll pick one **critical path** in your design (read / write / async) and pressure-test it like a production system.
> I'll ask for concrete, implementable details on: **data persistence**, **correctness (idempotency/ordering/consistency)**, **failure recovery**, **P99 stability**, and **observability/evolution**.
> I'll also change assumptions (retries, out-of-order, partial failures, hotspots, backlog, AZ failure). Explain how your system stays correct and stable."

**Lock the deep-dive target:**
> "Pick the single most critical and failure-prone path in your design:
> - a typical **write path**, or
> - a typical **read path**, or
> - an **async processing** path
> We'll deep dive on that end-to-end."

---

## 2) Universal Deep Dive Backbone (Applies to Any Backend Design)

### Step A — Define Correctness Contracts (30–60s)
Ask the candidate to state **3 invariants** for the chosen path:
- **Uniqueness / no double-effects:** Is duplicate processing allowed? What breaks if it happens?
- **Consistency / freshness:** How stale can reads be? What's the convergence SLA?
- **Ordering / causality:** Do events/state transitions require ordering? What happens under reordering?

> If invariants aren't explicit, you can't evaluate trade-offs.

### Step B — End-to-End Walkthrough (2–4 min)
Force a time-ordered explanation:
1. Request enters (ignore auth unless it impacts isolation)
2. **Where does state land**? (DB/table, KV/doc, topic/partition, index)
3. Synchronous boundaries: what must happen before returning
4. Side effects: cache/index updates, events, audit logs

Anchor question to repeat:
> "What's the input/output of this hop, where does it persist, and what happens on failure?"

### Step C — Fault Injection (5–10 min)
Inject these failure classes (MECE) on the **same path**:
1. **Retry/duplicate**: same request twice
2. **Out-of-order/late**: old update arrives after new
3. **Out-of-order/late**: old update arrives after new
4. **Partial failure**: DB success but publish fails (or vice versa)
5. **Dependency slowdown**: 1% downstream becomes 10x slower
6. **Backlog/backpressure**: queue grows 10x, recovery path
7. **Shard/leader/AZ failure**: failover, rebalancing, consistency

For each, demand:
- **Detect:** what metrics/alerts show it
- **Contain:** degrade/shed/load-limit strategy
- **Recover:** replay/backfill/reconcile/rebuild
- **Prove:** how you confirm end-state correctness (idempotency/versioning/constraints/recon)

### Step D — Tail Latency & Scale (3–6 min)
Only for the chosen path:
- Top 3 contributors to **P99**
- Where are **hotspots** and how you mitigate (sharding/salting/hierarchical fanout/batching)
- **Backpressure** points and what you drop vs never drop (aligned to invariants)
- 10x QPS: first bottleneck, scaling plan, and cost curve

### Step E — Observability & Evolution (2–4 min)
- Key SLIs: success rate, E2E latency, queue lag, retry rate, dedupe hit rate, replay progress
- "5-minute production debug": where do you look first?
- Evolution: schema changes, resharding, rebuild, rollout/rollback, data rebuild

---

## 3) Module Library (Same as Previous Version)

- **M1** Data Model & Keys
- **M2** Idempotency, Dedup, Ordering, Versioning (Correctness Core)
- **M3** Transaction Boundary & Cross-System Consistency
- **M4** Failure Modes & Recovery Loop
- **M5** Tail Latency & Queueing (P99/P999)
- **M6** Scaling & Hotspot Mitigation
- **M7** Observability & Operations
- **M8** Evolution, Backfill, Rebuild

> **Important:** You do **NOT** deep dive every module. You select modules that are **tightly coupled** to the current design question and the candidate's proposed solution.

---

## 4) When a Module is "Tightly Coupled" vs "Skip It"
Each module has a **Trigger** (deep dive) and **Skip Conditions** (don't deep dive if not applicable).

### M1 — Data Model & Keys
**Deep dive triggers**
- Any persistent state (DB/KV/index/topic as source of truth)
- Sharding/partitioning is central
- Query depends on indexes (search/geo/secondary indexes)

**Skip if**
- The problem is truly stateless (gateway/proxy) and persistence isn't part of the design

---

### M2 — Correctness Core (Idempotency/Dedup/Ordering/Versioning)
**Deep dive triggers**
- Any side effect: writes, payments, inventory, matching, credits, notifications
- Retries exist (timeouts, client replays, at-least-once delivery)
- There is a state machine (order/task/match lifecycle)

**Skip if**
- Rare: pure static read-only distribution with no freshness/correctness constraints

---

### M3 — Transaction Boundary & Cross-System Consistency
**Deep dive triggers**
- Multiple writes: DB + MQ, DB + cache, source + index, or Saga flows
- Derived views/materialized indexes/caches exist
- Candidate mentions CDC/outbox/dual-write

**Skip if**
- All critical state changes are atomic within a single datastore transaction and no external side-effect chain exists

---

### M4 — Failure Modes & Recovery Loop
**Deep dive triggers**
- Any queue/async/batch component exists
- Any dependency exists (downstream services, third-party)
- Availability/SLO matters (almost always)

**Skip if**
- Mostly never; at most **reduce depth** if the system is trivially synchronous and low stakes

---

### M5 — Tail Latency & Queueing (P99)
**Deep dive triggers**
- Online request path with explicit latency targets
- Fanout, shared thread pools/connection pools, cache miss variance

**Skip if**
- Pure offline batch where only throughput/cost matters

---

### M6 — Scaling & Hotspot Mitigation
**Deep dive triggers**
- High QPS or skew/hot keys/hot partitions
- Resource contention (claiming, flash crowd)
- Multi-tenant isolation is required

**Skip if**
- Explicitly tiny-scale system (uncommon in L6 interviews)

---

### M7 — Observability & Operations
**Deep dive triggers**
- Always relevant: incident response, debugging, rollout, proving correctness

**Skip if**
- Essentially never; you can only limit depth

---

### M8 — Evolution, Backfill, Rebuild
**Deep dive triggers**
- Long-lived data, schema evolution, resharding, rebuilds, replay, audit/recon
- Derived data (indexes/caches/materialized views) that may need rebuilding

**Skip if**
- Data is short-lived/ephemeral and can be safely discarded/recreated without correctness obligations

---

## 5) Module Selection Algorithm (Prevents "Non-Fit" Deep Dives)

### Step 1 — Pick ONE critical path
Candidate chooses: read/write/async path.

### Step 2 — Always include the "core trio"
- **M2** Correctness core (if any side effects exist)
- **M4** Failure & recovery loop
- **M7** Observability & ops (to close the loop: detect → contain → recover → prove)

### Step 3 — Add 1–2 "design-specific" modules (trigger-driven)
- Persistent/sharding/indexing ⇒ **M1**
- Dual-write/derived views/async propagation ⇒ **M3**
- Online latency constraints ⇒ **M5**
- Hotspots/multi-tenant/isolation/high contention ⇒ **M6**
- Replay/rebuild/reshard/audit needs ⇒ **M8**

### Step 4 — Explicitly declare what you will NOT deep dive
If triggers don't fire, say:
> "We'll skip module X because your design doesn't include that mechanism."

---

## 6) Quick Reference: System Type → Suggested Modules (and What Not to Deep Dive)

> Use this as a shortcut, but default to **trigger-based** selection.

### A) Real-time Search / Indexing (geo/text/retrieval)
**Deep dive:** M1 + M2 + M3 + M5 + M6 + M7 (optional M8)
**Usually skip:** M8 unless rebuild/evolution is explicitly important

### B) Delayed Jobs / Timers / Expiration
**Deep dive:** M1 + M2 + M4 + M6 + M7 (add M5 if online triggering)
**Usually skip:** M3 cache/index consistency details unless candidate introduced them

### C) High Contention "Single Winner" (claim/match/coupon)
**Deep dive:** M2 + M3 + M4 + M5 + M6 + M7 (M1 if persistence is central)
**Usually skip:** M8 unless audit/recon is required

### D) Event Streaming / CDC / Multi-subscriber platform
**Deep dive:** M2 + M3 + M4 + M6 + M7 + M8 (add M5 if online SLA; M1 if stateful)
**Usually skip:** M1 indexing details if there's no query/index component

### E) Cache Consistency / Read-heavy configuration service
**Deep dive:** M2 + M3 + M5 + M6 + M7 (add M1 if DB is central; add M8 if migrations matter)
**Usually skip:** deep M4 beyond cache storm, unless async pipelines exist

### F) Multi-tenant platform / Rate-limiting / Isolation / Gateway
**Deep dive:** M5 + M6 + M7 + M4 (add M1/M2 if quota/billing state exists)
**Usually skip:** M8 unless long-lived billing/audit is required

### G) Ledger / Balance / Transaction correctness
**Deep dive:** M1 + M2 + M3 + M4 + M7 + M8 (add M5 if online latency matters)
**Usually skip:** deep M6 unless hotspot accounts or bursts are central

---

## 7) Validation Questions (Does the Deep Dive Stay Tight to the Current Design?)

1. Can the interviewer select and declare "We'll deep dive only these 4 modules" within 1 minute, based on the candidate's design?
2. Do the questions always point to concrete objects in the design (keys, tables, partitions, transaction boundaries, retry policies), not abstract concepts?
3. When the candidate doesn't include a mechanism (cache/index/dual-write), does the interviewer stop that module immediately and move on?
4. Does the deep dive end with verifiable artifacts: SLIs/alerts, a recovery runbook, and a correctness proof story?

### Ideal answer patterns
- **Fast selection:** M2+M4+M7 plus 1–2 trigger-hit modules
- **Concrete binding:** "In *your* design, what is the idempotency key? where is it stored? TTL? hotspot risk?"
- **Stop non-fit modules:** If "no cache/index," skip M3/M1 sub-branches
- **Verifiable closure:** metrics thresholds + detect/contain/recover/prove for a chosen failure scenario
