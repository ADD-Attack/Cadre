# Cadre — team topology

```mermaid
flowchart TD
    OP([Operator])

    subgraph DOOR[" "]
      SMM["Social Media Manager<br/><i>doorway (optional)</i>"]
    end

    subgraph CORE["Cadre nucleus"]
      PM["Project Manager<br/>plan · tasks · Gantt · dispatch"]
      RA["Requirements Analyst"]
      PD["Project Designer"]
      QA["QA / Verifier<br/><i>independent — may veto</i>"]
    end

    subgraph STAND["Standing functions"]
      SEC["Security / IT<br/><i>advises, never self-edits</i>"]
      FM["Finance Manager<br/><i>budgets</i>"]
      AR["Agent Resources<br/><i>roster</i>"]
      CON["Consultant"]
    end

    subgraph WORK["Worker seats — persistent (recommend two)"]
      W1["worker 1"]
      W2["worker 2"]
    end

    OP <-->|single interface| SMM
    OP <-->|direct| PM
    SMM -. relays .-> PM

    RA --> PD --> PM
    PM --> W1 & W2
    W1 & W2 --> QA
    QA -->|evidence| PM
    QA --> PROD["Finished product"]
    PROD -.->|new product, or scope change / new feature| RA
    PM -. consults .-> CON
    PM -. budget .-> FM
    PM -. roster .-> AR
    SEC -. audit .-> PM
```

**Reading it:** projects enter at Requirements → Design → Plan. The PM owns execution and dispatches its **worker seats** — **the workers sit in the PM's scope**, and they are **persistent agents** (own workspace, memory, identity), not throwaway runs. **Cadre recommends two:** one is a single point of failure, and two lets the PM run in parallel. QA verifies independently (a *different* agent than the builder) and can block a "done" claim; passing verification produces the **finished product**. Once something ships, two things send work back to the start: a **scope change or new feature** to what just shipped, or a **new product** entirely — either way it re-enters at the Requirements Analyst rather than being patched mid-stream. The standing functions support the PM without doing project work: they ride *beside* the line, never on it. Security audits and advises but never edits config. The Social Media Manager is optional — it exists as the **doorway** for operators who want one interface.
