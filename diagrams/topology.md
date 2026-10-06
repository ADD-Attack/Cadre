# Cadre — team topology

```mermaid
flowchart TD
    OP([Operator])
    ENTRY[Configured OpenClaw entry point<br/>or direct PM contact]

    subgraph CORE[Cadre project team]
      PM[Project Manager<br/>one accountable outcome owner]
      RA[Requirements Analyst<br/>when useful]
      PD[Project Designer<br/>when useful]
      WORK[Persistent worker seat(s)]
      REVIEW[Independent QA / reviewer<br/>when risk or criteria warrant it]
    end

    subgraph SUPPORT[Support roles — as needed]
      SEC[Security / IT]
      FM[Finance]
      AR[Agent Resources]
      CON[Consultant]
      SMM[Social Media Manager<br/>optional doorway]
    end

    OP <--> ENTRY
    ENTRY --> PM
    OP <--> PM
    SMM -. optional relay .-> PM

    PM -. consults / assigns as useful .-> RA
    PM -. consults / assigns as useful .-> PD
    PM -->|bounded work| WORK
    WORK -->|result + evidence| PM
    PM -->|focused review, when warranted| REVIEW
    REVIEW -->|findings / verdict| PM
    PM -->|result, evidence, open decisions| OP

    PM -. security advice .-> SEC
    PM -. budget support .-> FM
    PM -. roster support .-> AR
    PM -. second opinion .-> CON
```

**How to read it:** the operator enters through the deployment's configured OpenClaw interface,
which may route directly to the PM or through an optional doorway. Each project outcome has one
accountable owner, normally the Project Manager. Requirements, design, implementation, and support
roles contribute as needed; the diagram is not a mandatory serial approval pipeline. Worker seats
are persistent agents, distinct from disposable subagent runs.

The owner checks work against its acceptance points and carries evidence through the handoff. Add
an independent QA/reviewer when consequence or acceptance criteria require it—not by role ceremony.
There is no fixed review-pass cap: each pass should test a named criterion, resolve a finding, or add
decision-relevant evidence, while preserving the tested artifact's identity.

Keep one canonical project/task record. Kanban and Gantt are views of that plan, not competing
sources of truth. Where FlowBoard is integrated, it is an operational tracking mirror unless the
team explicitly migrates its canonical board. Within delegated authority, the PM may resolve a
routine workflow/lifecycle/sequence warning through a supported, audited override, recording the
actor, reason, prior/new state, and evidence. An override never bypasses platform authentication or
RBAC, security, data integrity, schema/path validation, destructive-action limits, or decisions
reserved to the operator.

After delivery, a new product or material scope change starts a new, explicit outcome; bring the RA
back in when requirements need to be established or revised. Project-specific details stay with the
tenant, not in the reusable team topology.
