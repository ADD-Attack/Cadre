# The Cadre Wizard

The Cadre Wizard is the **only** supported entry point. It is not a script — it is a *procedure the OpenClaw main agent performs by talking to the operator*, then writing files only after confirmation.

**Trigger:** the operator says some form of *"set up Cadre"*, *"read the Cadre README"*, or *"install Cadre"*.

**Who runs it:** the OpenClaw **main agent** on the target deployment (the agent the operator already talks to). It may delegate file-writing to a subagent, but it owns the interview.

**Hard rule:** at every step the Cadre Wizard **proposes and waits**. Nothing is written to config or to a workspace until the operator confirms that step. A Cadre Wizard that installs silently is a bug.

---

## Step 0 — Preflight (read-only)

Before asking anything, discover the ground truth. Never ask the operator for facts you can read.

1. Read the live config (`openclaw config get` and the config schema). Establish:
   - existing agents and their workspaces
   - available channels/accounts (Discord, Telegram, etc.)
   - models configured and reachable
   - whether a plugin/hook system is active (needed later for FlowBoard)
2. Detect existing projects worth porting (repos, workspaces with `PROJECT.md`, active work).
3. Detect resource limits (disk, any spend caps).

**Output:** a short capabilities summary shown to the operator — *"here's what I found"* — before any question is asked.

**Completion criterion:** the operator has seen the environment summary and confirmed it's accurate.

---

## Step 1 — Confirm the agent set

Present the roster from [`reference/agents.md`](./reference/agents.md) as a **checklist**, not a mandate. For each: role, one-line charter, default model, default budget.

Recommend a starting set based on what the operator says they want:
- **Solo-operator, one project** → PM, Requirements Analyst, Project Designer, QA. Add others later.
- **Public-facing** → add Social Media Manager.
- **Spending real money** → add Finance Manager.
- **Several agents/projects** → add Agent Resources.

**Ask:** *"Create these? Deselect any."*

**Completion criterion:** an explicit list of agents to create.

---

## Step 2 — Models per role

Cadre ships **model classes**, not hard-coded model names (models drift). The Cadre Wizard maps each class to a concrete model that exists *on this deployment*.

| Class | Use for | Cost posture |
|---|---|---|
| `reasoning` | PM, Requirements, Designer, Security, QA, Consultant | higher |
| `fast` | Social, Finance, Agent Resources, routine relay | lower |

Default mapping = *lightest, most accurate model that fits the class*, decided by the Cadre Wizard from the deployment's available models. **The operator may override any single role.**

**Completion criterion:** a model bound to every selected role, each confirmed.

---

## Step 3 — Naming conventions

Cadre roles are fixed; **the team name and the agent names are the operator's.**

1. **Name the team.** Ask what the operator wants to call the team itself. The default is the product name, **Cadre** — and *Cadre* is also the correct answer if they don't care. Whatever they choose is what goes in the agent identity files and the team index, so a deployment is never branded something the operator didn't pick.
2. **Name the agents.** Ask for a theme (a TV show, a ship's crew, a colour set, or plain role names) and derive one name per agent. Show the mapping before writing.

The **naming convention** is recorded so later additions (subagents, new roles) match it.

**Completion criterion:** a team name, and a name for every selected agent, agreed.

---

## Step 4 — Budgets

If the operator selected **Finance Manager**, run the full budget interview (per-role envelopes, currency vs token units, alert thresholds, hard cap behaviour).

Otherwise, apply **Cadre's light defaults** (see [`reference/budgets.md`](./reference/budgets.md)): modest per-role token envelopes, warn-only thresholds, one global daily ceiling. State the defaults plainly and let the operator adjust or accept.

**Completion criterion:** every selected agent has a budget; the global ceiling is set; the enforcement mode is recorded.

---

## Step 4b — Budget enforcement (ask ONLY if Finance Manager is approved)

Ask **once**, plainly, before moving on:

> *"You set a ceiling. Should the deployment actually **enforce** it — cap spend and switch models automatically — or is accounting enough for now?"*

**Why this is a question and not a default.** The platform ships **no native spend cap** (see [`reference/budgets.md`](./reference/budgets.md) — "Platform reality"). Without a mechanism, a ceiling is a *promise*, not a limit. The mechanism is a **local AI gateway** — **LiteLLM** — that sits between this deployment and the model providers:

- **Per-model budget caps** — spend stops at the ceiling you set.
- **Automatic model fallback at a threshold** — e.g. at **95%** of a model's budget, requests are silently rerouted to a cheaper model instead of failing. This is the "flag at 95% and move to a new model" behaviour FM exists to promise.

**If the operator says yes:**

1. **Propose the install, then wait for confirmation.** LiteLLM runs as a local service (Docker is the lightest path) on port **4000**, configured by a `config.yaml` plus a master key. **The operator approves the install command before it runs** — this is a new background service, and it is the operator's machine.
2. **Wire OpenClaw to it**, once confirmed: add a custom provider pointed at the gateway, and route the budgeted models through it.
   ```bash
   openclaw config set models.providers.litellm.baseUrl http://127.0.0.1:4000/v1
   openclaw config set models.providers.litellm.apiKey "${LITELLM_MASTER_KEY}"
   openclaw config set models.providers.litellm.api openai-completions
   ```
   (Set the master key as a secret, never inline. Model entries and any override of `agents.defaults.model` follow per [`reference/budgets.md`](./reference/budgets.md).)
3. **Record it** in the team index: the gateway, its port, and which models route through it.

**If the operator says no:** say so plainly in the index — *budget = accounting + convention, no enforcement binary installed* — and move on. Do not imply a cap that isn't there.

**Honest limits to state when proposing it:** LiteLLM is a **third-party service** the operator now runs and maintains; it is a **single point of failure** for model traffic (if it is down, so is the team's inference); and it only enforces what is routed *through* it — a call that bypasses the gateway bypasses the cap. Recommend it, do not oversell it.

**Completion criterion:** the operator has decided yes/no; if yes, the gateway is installed, OpenClaw points at it, and the index records the routing; if no, the index records *accounting-only*.

---

## Step 5 — Interface & the doorway

Ask how the operator wants to *talk to the team*.

- **Direct** (default): the operator has a chat surface per agent, or talks to the main agent who relays.
- **Single-doorway**: the operator wants **one** interface. They pick one agent — commonly the Social Media Manager — as the **doorway**. On a cadence (default: hourly) the doorway reads every agent's `outbox/`, batches queued messages to the operator, and routes replies back to the right `inbox/`.

If single-doorway: confirm the door agent, the polling cadence, and the **scope** (which agents' outboxes that door may read). Record dedupe and urgency rules per [`reference/mailboxes.md`](./reference/mailboxes.md).

**Completion criterion:** interface mode chosen; if doorway, its agent + cadence + scope confirmed.

---

## Step 6 — Port existing projects

For each detected project, offer to bring it into Cadre: create a `PROJECT.md`, seed the task board, and route it through Requirements Analyst → Designer → PM.

**This is an offer, not a migration.** Existing work is never moved or restructured without explicit per-project confirmation.

**Completion criterion:** a per-project decision (port / leave alone / decide later).

---

## Step 7 — Write

Only now, write:
1. Agent entries in OpenClaw config (via `openclaw config set` — never hand-edit JSON).
2. Each agent's workspace: `AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `BUDGET.md`, `inbox/`, `outbox/` from [`templates/agent-workspace`](./templates/agent-workspace).
3. The shared team ledger `SHARED.md` from [`templates/SHARED.md`](./templates/SHARED.md).
4. The **team directory** `CADRE.md` from [`templates/CADRE.md`](./templates/CADRE.md) — the record of *who exists*: roles, names, models, budgets, reports-to, interface mode, and guardrail enforcement. Write it beside `SHARED.md` in the **team root** (the shared location that holds `SHARED.md`).

Both `SHARED.md` and `CADRE.md` are **session-start reads**: every agent reads them before it does anything, so each agent knows the team's standing decisions *and* who its teammates are. Fill the path to each into every agent's `AGENTS.md` (item 2), so the read is not a guess.

**Guardrails are not optional.** Before writing, confirm the six guardrails from [`reference/guardrails.md`](./reference/guardrails.md) are set for this deployment — the four *persistence* guards (routing limit value, claim-lease enforcement mechanism, promotion gate authored not defaulted, no-op detector on) and the two *cost* guards (**QA cap** — review capped at two rounds; **zero-token checks** — routine watchers run headless, idle costs $0). Record each as *enforced* or *advisory* in the index — do not leave it unstated.

**Completion criterion:** config validates, every agent workspace exists, and the team index reflects exactly what the operator approved.

---

## Step 8 — Verify and hand off

1. **Verify:** one canary task per created agent (a trivial round-trip) proving it responds and its mailbox works. Report pass/fail — do not claim success on an unattempted check.
2. **Record** the install in the team index with a date and version.
3. **Hand off:** offer to start the first project through the **Requirements Analyst**.

**Completion criterion:** canary results reported to the operator; the first project either started or explicitly deferred.

---

## Failure handling

- **A step can't complete** (no model for a class, no channel, config write fails): stop at that step, report the exact blocker, and leave prior steps' writes in place. Never roll forward on an assumption.
- **The operator changes their mind mid-wizard:** re-run from the affected step; the Cadre Wizard is idempotent — it proposes current state and only writes deltas.
- **Re-run on an installed deployment:** the Cadre Wizard detects existing Cadre agents and offers to *extend* (add roles) rather than reinstall.
