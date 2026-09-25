# Less babysitting: the AUTONOMY.md resource

**Here is the autonomy file promised in the Reddit discussion, plus the clauses that connect it to an agent's `AGENTS.md` and `SOUL.md`.** It comes from Michael Scott's customized OpenClaw workspace. Cadre is simply hosting this resource: you do not need Cadre, a multi-agent team, or Michael Scott's persona to use it.

**Start here: [read AUTONOMY.md](../examples/michael-scott/AUTONOMY.md) · [get the raw Markdown](https://raw.githubusercontent.com/ADD-Attack/Cadre/main/examples/michael-scott/AUTONOMY.md).**

The useful change is behavioral: when you have already authorized a task, the agent should carry it through, investigate problems, verify the result, and report back—not stop at every routine step with “want me to continue?” This is the reusable contract behind that behavior:

> If the task is within my authority, safe, reversible, and understood: do it, then report what changed.

**What you are downloading:** a public adaptation of the working policy, not the verbatim private file. It preserves reusable procedures while omitting private context and machine-specific incident history. It is not an installer or an unlock for OpenClaw permissions.

## Act on authorized work; diagnose real limits

There are two different problems: an agent **needlessly asking** when it can act, and an agent **actually lacking access**. This policy targets the first and asks the agent to diagnose the second accurately. It does not establish whether a particular OpenClaw release changed a permission or capability.

| Situation | Behavior this policy asks for |
| --- | --- |
| You ask for an authorized model or embeddings-provider change | Inspect the supported configuration interface, make the scoped change if permitted, and verify the effective result—not ask again merely because it is a config change. |
| A gateway restart is part of authorized maintenance | Check service supervision, restart prerequisites, and recovery first; use the supported lifecycle and verify recovery. Do not blindly stop the process carrying the conversation. |
| You request a skill update | Complete the supported edit/review/publication workflow to the extent authorized. If a platform step requires human action, name that exact step instead of vaguely saying “I can't.” |
| You give a backlog and say “keep going” | Continue through the in-scope work, keep check-ins for delegated tasks, and stop only for a real blocker or reserved decision. |
| A tool explicitly denies an operation, or a credential is needed | Report the actual restriction or supported credential-entry step. Do not mistake another execution path for authorization. |

So this is **not a claim that AUTONOMY.md solves every complaint in that thread**. It can remove self-imposed hesitation; it cannot remove platform restrictions. An agent should distinguish those cases using evidence rather than inventing a prohibition—or inventing access it does not have.

## Get the files

These are actual Markdown files, not just descriptions. Open **Raw** to copy the text, or save it under the filename shown in your agent's workspace.

| File | Read on GitHub | Raw Markdown | What you are getting |
| --- | --- | --- | --- |
| `AUTONOMY.md` | [Read](../examples/michael-scott/AUTONOMY.md) | [Raw / save](https://raw.githubusercontent.com/ADD-Attack/Cadre/main/examples/michael-scott/AUTONOMY.md) | Michael Scott's public replication edition; adapted from the private policy, not a verbatim dump. |
| `AGENTS.md` | [Read](../templates/agent-workspace/AGENTS.md) | [Raw / save](https://raw.githubusercontent.com/ADD-Attack/Cadre/main/templates/agent-workspace/AGENTS.md) | Generic Cadre role template with an autonomy pointer—not Michael Scott's private administrator file. |
| `SOUL.md` | [Read](../templates/agent-workspace/SOUL.md) | [Raw / save](https://raw.githubusercontent.com/ADD-Attack/Cadre/main/templates/agent-workspace/SOUL.md) | Generic persona template with an autonomy pointer—not a copy of private identity or memory. |

## Adopt it in an existing agent

1. Have the agent read the linked files first and compare them with its existing instructions. Back up existing workspace files; do not replace a working `AGENTS.md` or `SOUL.md` wholesale with the generic templates.
2. Adapt and save the public policy as workspace-root `AUTONOMY.md`. Preserve existing higher-priority instructions and operator decisions; surface actual conflicts instead of silently overwriting them.
3. Merge a pointer into both existing files. For example:

   **In `AGENTS.md`:**

   ```text
   Read workspace-root AUTONOMY.md at session startup and before planning delegated work.
   It defines initiative, follow-through, verification, and when to ask the operator.
   Apply it within higher-priority instructions, runtime permissions, and existing authorizations.
   ```

   **In `SOUL.md`:**

   ```text
   My act-versus-ask and follow-through contract is in workspace-root AUTONOMY.md.
   I act on authorized routine work, verify results, and report genuine blockers precisely.
   ```

4. Start a fresh session and verify that the agent can identify and summarize the installed file. Do not assume a new filename is automatically loaded by every runtime; use the supported startup-loading mechanism or an explicit read.
5. Try a small, reversible task. Check that the agent completes and verifies it without unnecessary approval questions, while reporting missing access honestly. Tools, scheduling, memory retrieval, and multi-agent orchestration must be configured separately if you want those capabilities.

**A request you can give your agent with this page:**

> Read this page and its linked AUTONOMY.md. Adapt the reusable behavior rules to my existing agent workspace, preserving my identity, preferences, and existing permissions. If authorized workspace editing is available, back up affected files, install AUTONOMY.md, and merge the AGENTS.md and SOUL.md pointers without replacing those files wholesale. Show the changes, identify unresolved conflicts or missing capabilities, and verify loading in a fresh session. Do not change security controls or claim that copying Markdown installs tools or grants access.

You do not need to install the Cadre team to use the autonomy policy. The repository is its public home; the policy is a starting point for an individual agent too.

## Check that it changed behavior—not just files

After installation, use a fresh session and try a small task your agent can already perform:

- **Routine work:** ask it to fix a documentation typo and verify the edit. It should finish without asking you to authorize each obvious step.
- **Follow-through:** give it two small, reversible tasks. It should complete both, not stop after the first to offer the second.
- **Honest limitations:** ask it to inspect an unavailable integration. It should identify what is missing, not claim success or invent a universal ban.
- **Continuity:** ask it to record a harmless preference, then check that a later session can find the persisted record.

For each test, look for an actual result and evidence. Being able to recite the policy is a loading check, not proof of autonomy.

## What else is needed to replicate the setup?

The file supplies the decision and follow-through rules. Tools supply execution; persistent records supply continuity; scheduled wakes supply unattended follow-up. If your installation lacks those mechanisms, copying the file will not add them. Start with one agent and the capabilities you already have, then add only what your work needs.

Optional background references:

- [Autonomy index](./autonomy.md): the file and related resources in one place.
- [Memory](./memory.md): continuity and durable records.
- [Scheduled work](./scheduled-work.md): check-ins and timed wakeups.
- [Collaboration](./collaboration.md): delegation and verified hand-offs if you run a team.
- [Guardrails](./guardrails.md): runtime mechanisms, distinct from written instructions.

Keep your own agent's name, personality, and existing operator decisions. The goal is to reproduce useful working habits, not to impersonate Michael Scott or copy his deployment wholesale.
