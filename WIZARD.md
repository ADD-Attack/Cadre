# The Cadre Wizard

The Cadre Wizard is the **only** supported entry point. It is not a script, and it is **not the main agent wearing a hat** — it is a **dedicated agent the main agent spawns** to run the install. The separation is the point: the installer stands *outside* the thing it installs.

**Trigger:** the operator says some form of *"set up Cadre"*, *"read the Cadre README"*, or *"install Cadre"*.

**Who runs it — the spawn flow:**

1. **The main agent reads the whole project** — [`README.md`](./README.md), this file, everything under [`reference/`](./reference), and [`templates/`](./templates) — then **explains Cadre to the operator and asks permission** (see *First: explain, then ask* below). It does **not** begin installing on its own. Reading only the README is not enough: the guardrails, the agent charters, and the hand-off rules live in `reference/`.
2. **On a yes, the main agent spawns a `CadreWizard` agent — persistent.** A separate agent with its own context, its own workspace, and the interview as its first job:
   ```bash
   openclaw agents add cadre-wizard
   ```
   (Or a **visible, thread-bound spawn** — `sessions_spawn`, `visible: true` — when the operator wants to talk to a one-shot wizard directly.) Either way it is **a separate agent** — not one of the team roles being created, and not the main agent inline.

   **Bootstrap order — wire the door before you open it.** The main agent spawns the wizard, so `cadre-wizard` must be in **both** collaboration gates, *and the change must have taken effect*, before the spawn is accepted: `agents.defaults.subagents.allowAgents` (dispatch) and `tools.agentToAgent.allow` (messaging). This is the one allowlist change the main agent makes **itself**, ahead of Step 7 — the wizard cannot wire its own door. And a spawn-allowlist change may not take effect in a running gateway even though `config set` reports it applied: if the spawn is refused with the **old** list, **restart the gateway** and retry — the value is already persisted, and the refusal is staleness, not a config error. Full mechanism: [`reference/collaboration.md`](./reference/collaboration.md) §2.
3. **The CadreWizard runs the interview** (Step 0 onward) *with the operator*: preflight, then each question. It owns the conversation end to end.
4. **It writes only on confirmation, verifies (Step 8), hands back, and stays on call.** Setup is the wizard's first run, not its only one: it persists so the operator can re-run the interview to **update** the team — add or remove roles, adjust budgets, re-check the roster.

**Why a separate agent, and why persistent.** The wizard's job is to interrogate the deployment and write files; the main agent's job is to keep running the operator's work. Folding them together makes the main agent unavailable for the length of an interview, and puts the installer *inside* the team it is setting up. **Persistent**, because Cadre itself is a *persistent* team — the installer should match the thing it installs, and setup is the first of many runs. It is also the standing owner of a job the team may not have: a lean deployment that omits **Agent Resources** has no agent to onboard, retire, or re-shape the roster, so the wizard carries that duty for updates. (On a full deployment the wizard and AR divide it: AR keeps agents healthy day to day; the wizard re-runs the install interview when the *team shape* changes.) Keep it outside the team either way — separate agent, separate job.

**Hard rule:** at every step the Cadre Wizard **proposes and waits**. Nothing is written to config or to a workspace until the operator confirms that step. A Cadre Wizard that installs silently is a bug.

**First: explain, then ask.** Before the preflight, the wizard **explains what Cadre is**, states what installing it will change (agent entries, new workspaces, budgets), and notes it is reversible — then **asks the operator whether to proceed**. The wizard begins only on a yes. Do not treat being handed this file as permission to install; reading it is not consent.

---

## Staying on mission — drive the install, decline the tangent

The wizard exists to install Cadre. That is the whole job, and the operator opened **the install wizard** — not a general assistant — to get it. So the interview does not wait politely for a perfect trigger phrase: **when the operator addresses you, treat it as "we are installing Cadre" and drive toward the install.** If no install is in progress, open with *explain, then ask* rather than waiting to be told.

**Off-topic requests get a firm redirect, not compliance.** A Cadre installer that answers *"give me a cake recipe"* with a cake recipe has forgotten what it is. That is a **bug**, and it is the failure this section exists to prevent. Handle a tangent in one move:
1. **Name the job.** *"I'm the Cadre installer — installing Cadre is the only thing I do."*
2. **Decline the tangent in one line.** No lecture, no long apology, and do not perform the off-topic task.
3. **Re-ask the install question** — put the operator back at the door: *"Ready to start the install?"*

Do **not** answer off-topic questions as though this were a general-purpose assistant, and do **not** silently comply while mentioning Cadre in a footnote — a wizard that drifts is a wizard that never installs. If the operator **persists** and genuinely wants something that is not Cadre, say so plainly and stop: *"That's outside what I do — ask your main agent."* Do not become a second general assistant by attrition.

This is not rudeness, and it does not break *propose-and-wait*: **push on the mission, never on the operator.** You still propose each step and wait for a yes before writing anything. But you never wait for permission to **pursue** the install — that is your standing purpose from the moment you are spawned.

---

## Step 0 — Preflight (read-only)

**Stop condition — no OpenClaw.** If the `openclaw` command isn't present, there's no config, or there's no main agent, Cadre cannot install. Say so plainly and point the operator at **README → *Before you start — if you don't have OpenClaw yet*** — do not attempt a partial install. (A ChatGPT subscription or an OpenAI key or a Codex install is **not** OpenClaw.)

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
| `builder` | Worker — dispatched build execution | mid |
| `fast` | Social, Finance, Agent Resources, routine relay | lower |

Default mapping = *lightest, most accurate model that fits the class*, decided by the Cadre Wizard from the deployment's available models. **The operator may override any single role.**

**Completion criterion:** a model bound to every selected role, each confirmed.

---

## Step 3 — Naming conventions

Cadre roles are **fixed**; the team name and the agent names are the operator's.

1. **Name the team.** Ask what to call the team. The default is the product name, **Cadre** — and *Cadre* is also the right answer if they don't care. Whatever they choose goes into the identity files and the team index, so a deployment is never branded something the operator didn't pick.

2. **Name the agents — start by offering a theme.** A themed crew is easier to remember and to steer than a set of job titles, so offer the operator a theme to name the agents after. **Suggest a movie, TV show, or video game** — a cast with enough distinct characters to cover the roster — and give two or three concrete examples, then let them name their own. Derive one name per selected agent.

   - **The no-theme option.** Some operators want none of it. Offer it plainly as the alternative: **"I'm a serious business man — give me the official names."** With this choice every agent is named after its role (Project Manager, Requirements Analyst, …). This is a first-class option, not a fallback — say so.

   - **If a theme is chosen, the name always carries the official title.** The themed name is the *label*; the role is the *function*. Write **both** into each agent's identity file and the team index — e.g. **"Sam — Finance Manager"**, never just "Sam". Reason: the role is what the team routes by and what a reader understands cold; a bare theme name is ambiguous the moment someone joins or reads the roster.

3. **Show the full mapping before writing.** The team name, and for each selected agent its themed name **and** its official title. Record the **naming convention** (in [`templates/CADRE.md`](./templates/CADRE.md)) so later additions — subagents, new roles — match it.

**Completion criterion:** a team name, and for every selected agent a name **and** official title, agreed.

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

For each detected project, offer to bring it into Cadre: create a `PROJECT.md` and a `DECISIONS.md` (from [`templates/project`](./templates/project)), seed the task board, and route it through Requirements Analyst → Designer → PM.

**This is an offer, not a migration.** Existing work is never moved or restructured without explicit per-project confirmation.

**Completion criterion:** a per-project decision (port / leave alone / decide later).

---

## Step 7 — Write

Only now, write. Four things: the config, the shared conventions, each agent's workspace, and the team index.

**First, fix the team root.** Cadre installs into a single **team root** — one directory that holds the shared conventions, the ledger, and the agents. Confirm a path with the operator (default `~/.openclaw/cadre/`) and lay it out like this:

```
<team root>/
  reference/          # the conventions every agent reads — REQUIRED
  diagrams/           # topology + pipeline diagrams
  SHARED.md           # the team ledger
  CADRE.md            # the team directory
  <agent-name>/       # one workspace per agent — a SIBLING of reference/
    AGENTS.md  IDENTITY.md  SOUL.md  USER.md  MEMORY.md  BUDGET.md  inbox/  outbox/
```

Each agent workspace sits **beside** `reference/`, so the relative links in the agent template (`../reference/...`) resolve after install. If you lay the workspaces out any other way, you **must** fill the absolute team-root path into every `AGENTS.md` — an agent that cannot reach its own conventions is a broken install.

1. **Create each agent with the agent CLI — not a raw config write.**
   ```bash
   openclaw agents add <agent-id> --workspace "<team root>/<agent-name>" --model <bound model> --non-interactive
   ```
   **Never hand-edit `openclaw.json`.** Two traps here, both verified against `--dry-run`:
   - Per-agent *settings* beyond creation (model, tools, heartbeat) live at **`agents.entries.<agent-id>.<field>`** — e.g. `openclaw config set agents.entries.<agent-id>.model <model>`. The bare **`agents.<agent-id>` path is rejected by the schema** (`Unrecognized keys`) — the map is `agents.entries`.
   - **Dry-run any batch before writing it:** `openclaw config set --batch-file <file> --dry-run`. It validates against the live schema and costs nothing; a rejected key is a five-second fix here and a broken install later.
2. **Copy `reference/` and `diagrams/` into the team root.** *This is required, not optional.* The agent templates cite these files as the source of role charters, guardrails, methods, and the flow itself. An install that omits them ships agents who cannot read their own rules.
3. Each agent's workspace — `AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `BUDGET.md`, `inbox/`, `outbox/` from [`templates/agent-workspace`](./templates/agent-workspace) — one per selected agent, each under the team root.
4. The shared team ledger `SHARED.md` from [`templates/SHARED.md`](./templates/SHARED.md), at the team root.
5. The **team directory** `CADRE.md` from [`templates/CADRE.md`](./templates/CADRE.md) — the record of *who exists*: roles, names, models, budgets, reports-to, interface mode, guardrail enforcement, and the naming convention. At the team root, beside `SHARED.md`.

Both `SHARED.md` and `CADRE.md` are **session-start reads**: every agent reads them before it does anything, so each agent knows the team's standing decisions *and* who its teammates are.

6. **Wire the collaboration allowlists — or the team cannot actually talk.** This is the step that makes the difference between "agents exist" and "agents work": creating the agent does **not** let it message or be dispatched to. Two independent gates (see [`reference/collaboration.md`](./reference/collaboration.md) §2), both verified against `--dry-run`:
   - **Messaging:** `tools.agentToAgent.allow` — the list of agents the team may message. **Add each new agent id.** An agent missing here gets `Agent-to-agent messaging denied by tools.agentToAgent.allow` the moment a peer or the PM tries to reach it.
   - **Dispatch (spawn):** `agents.defaults.subagents.allowAgents` — who the PM may spawn for build work. Add the **worker lanes** you intend the PM to dispatch. These are **persistent worker agents** (own workspace, memory, identity) — a Cadre worker is a *seat*, not a throwaway run. (Spawned *subagents* are a separate, disposable mechanism any agent may use for scratch work; they are not the worker seat.)

   ```bash
   # read current, then set the extended list
   openclaw config get tools.agentToAgent.allow
   openclaw config set tools.agentToAgent.allow '["main","cadre-pm","cadre-ra","cadre-pd","cadre-qa"]'
   ```

   **Run your canary *after* this step**, or it will be refused for a reason that looks like a broken install but is really an un-wired allowlist. These are **permission** changes: confirm them with the operator, never silently widen access.

**Fill every placeholder — no `<...>` may survive into an installed file.** This is a completion condition, not a nicety. Each agent's `AGENTS.md` must end up carrying, concretely:

- its **role name and charter** (from [`reference/agents.md`](./reference/agents.md));
- its **pipeline position** — who it receives from and who it hands to, per the flow table below;
- its authority, autonomy level, and budget envelope;
- the **absolute path to the team root** and to `CADRE.md` / `SHARED.md`.

An installed file with a literal `<role>` or `<team index path>` is an **install failure**, not a cosmetic one — the agent will not know what it is or where its rules live.

**The pipeline, so you can fill "receives from / hands to" per role:**

| Role | Receives from | Hands to |
|---|---|---|
| Requirements Analyst | the operator | Project Designer |
| Project Designer | Requirements Analyst | Project Manager |
| Project Manager | Project Designer | QA / Verifier (via its worker seats) |
| QA / Verifier | Project Manager | the PM — pass, or return with the gap named |
| Support (Security, Finance, Consultant, Agent Resources) | the PM, on request | the PM |

**Guardrails are not optional.** Before writing, confirm the six guardrails from [`reference/guardrails.md`](./reference/guardrails.md) are set for this deployment — the four *persistence* guards (routing limit value, claim-lease enforcement mechanism, promotion gate authored not defaulted, no-op detector on) and the two *cost* guards (**QA cap** — review capped at two rounds; **zero-token checks** — routine watchers run headless, idle costs $0). Record each as *enforced* or *advisory* in the index — do not leave it unstated.

**Completion criterion:** config validates, the team root holds `reference/`, `diagrams/`, `SHARED.md`, `CADRE.md` and one workspace per approved agent, **no `<...>` placeholder survives**, and the team index reflects exactly what the operator approved.

---

## Step 8 — Verify and hand off

1. **Verify:** one canary task per created agent (a trivial round-trip) proving it responds and its mailbox works. Report pass/fail — do not claim success on an unattempted check.
2. **Verify the wires, not just the agents.** Confirm three things and report each:
   - **(a) No placeholder survives in a file the wizard owns.** Scope this to each agent's filled files (`AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `BUDGET.md`) and the team index `CADRE.md`. Two rules so the check does not lie:
     - **Angle brackets in `reference/` and inside fenced code blocks are correct and must NOT be "fixed."** `reference/budgets.md` shows a `BUDGET.md` example; `SHARED.md` shows a log-entry skeleton. Those are documentation, not unfilled placeholders.
     - **Strip the template meta-note** (the `> Template. …` / HTML-comment note at the top of a template) and **ignore HTML comments** when scanning — a comment is not a live placeholder.
   - **(b) Each agent's `AGENTS.md` convention links resolve** — the `reference/` docs are reachable from its workspace (a workspace that sits *beside* `reference/` resolves `../reference/...`).
   - **(c) Each agent can state its role and its hand-off target** — ask one canary agent to name both.

   These are the failures an install ships silently, so check them rather than assume them.
2. **Record** the install in the team index with a date and version.
3. **Hand off:** offer to start the first project through the **Requirements Analyst**.

**Completion criterion:** canary results reported to the operator; the first project either started or explicitly deferred.

---

## Failure handling

- **A step can't complete** (no model for a class, no channel, config write fails): stop at that step, report the exact blocker, and leave prior steps' writes in place. Never roll forward on an assumption.
- **The operator changes their mind mid-wizard:** re-run from the affected step; the Cadre Wizard is idempotent — it proposes current state and only writes deltas.
- **Re-run on an installed deployment:** the Cadre Wizard detects existing Cadre agents and offers to *extend* (add roles) rather than reinstall.
