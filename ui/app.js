/* Muse Relay v2 — window logic.
 *
 * Safety rules for this file (reviewers: check these first):
 *  - Every value from the API is written with textContent / dataset /
 *    style numbers, never as markup: claim holders, purposes, op names
 *    and log lines can come from remote agents.
 *  - The UI key arrives in the URL fragment (never sent over HTTP),
 *    is moved into this closure, and the fragment is wiped.
 *  - The token is fetched only on Show/Copy and never logged.
 */
(() => {
  "use strict";

  const KEY = new URLSearchParams(location.hash.slice(1)).get("k") || "";
  history.replaceState(null, "", location.pathname);

  const $ = (id) => document.getElementById(id);
  const SERVICES = ["hands", "gateway", "parser"];
  const STATE_CHIP = {
    applied: "chip-ok", held: "chip-held", "refused-yielded": "chip-bad",
    failed: "chip-bad", expired: "chip-quiet",
  };
  const STATE_COLOR = {
    applied: "#3ddc97", held: "#ffb547", "refused-yielded": "#ff7a59",
    failed: "#ff5c6c", expired: "#5b6376",
  };

  let logSeq = 0;
  let started = false;
  let startedAt = 0;
  let tokenShown = false;
  let lastFeedIds = new Set();
  let elevation = null;
  let busy = false;

  // ------------------------------------------------------------ API
  async function api(path, opts = {}) {
    const init = { method: opts.method || "GET", headers: { "X-UI-Key": KEY } };
    if (opts.body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
    }
    const r = await fetch(path, init);
    let data = {};
    try { data = await r.json(); } catch (_) { /* empty */ }
    return { status: r.status, data };
  }

  // ------------------------------------------------------- formatting
  function dur(s) {
    if (typeof s !== "number" || !isFinite(s)) return "?";
    const t = Math.max(0, Math.round(s));
    if (t < 60) return `${t}s`;
    if (t < 3600) return `${Math.floor(t / 60)}m ${String(t % 60).padStart(2, "0")}s`;
    return `${Math.floor(t / 3600)}h ${String(Math.floor((t % 3600) / 60)).padStart(2, "0")}m`;
  }
  function setText(el, text, cls) {
    el.textContent = text;
    if (cls !== undefined) el.className = cls;
  }
  function toast(text, bad) {
    const t = $("toast");
    t.textContent = text;
    t.className = bad ? "toast bad" : "toast";
    t.hidden = false;
    clearTimeout(toast._h);
    toast._h = setTimeout(() => { t.hidden = true; }, 2600);
  }
  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_) {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      let ok = false;
      try { ok = document.execCommand("copy"); } catch (_) { ok = false; }
      ta.remove();
      return ok;
    }
  }

  // ---------------------------------------------------------- render
  function phaseOf(view) {
    if (!view.started) return "idle";
    const m = view.model;
    if (!m) return "starting";
    const states = SERVICES.map((s) => m.services[s]);
    if (states.every((s) => s === "ok")) return "running";
    if (Date.now() - startedAt < 20000) return "starting";
    return "degraded";
  }

  function renderTiles(view) {
    const m = view.model;
    for (const svc of SERVICES) {
      const tile = document.querySelector(`.tile[data-svc="${svc}"]`);
      let state = "idle";
      let word = "not started";
      if (view.started) {
        const s = m ? m.services[svc] : null;
        if (s === "ok") { state = "ok"; word = "running"; }
        else if (s === "down") { state = "down"; word = "not answering"; }
        else { state = "starting"; word = m ? "unknown" : "starting…"; }
      }
      tile.dataset.state = state;
      setText(tile.querySelector('[data-role="state"]'), word);
      const detail = (view.status && view.status[svc]) || "";
      setText(tile.querySelector('[data-role="detail"]'), detail.replace(/^[A-Za-z]+ \(:\d+\):\s*/, ""));
    }
  }

  function renderClaim(m) {
    const claim = m && m.claim;
    $("claim").dataset.held = claim ? "1" : "0";
    if (claim) {
      setText($("claim-holder"), claim.holder);
      setText($("claim-purpose"), claim.purpose || "No purpose given");
      const left = claim.expires_in_s;
      setText($("claim-expiry"), left == null ? "no expiry" : `expires in ${dur(left)}`);
      const pct = left == null ? 100 : Math.max(2, Math.min(100, (left / 1800) * 100));
      $("claim-meter").style.width = `${pct}%`;
    } else {
      setText($("claim-holder"), "Free");
      setText($("claim-purpose"), m ? "No session holds the hands." : "—");
      setText($("claim-expiry"), "—");
      $("claim-meter").style.width = "0%";
    }
    const q = (m && m.queue_len) || 0;
    setText($("claim-queue"), `queue ${q}`, q ? "chip chip-held" : "chip chip-quiet");
    const res = $("claim-reserved");
    if (m && m.reserved_for) {
      res.hidden = false;
      setText(res, `Reserved for ${m.reserved_for}`);
    } else {
      res.hidden = true;
    }
  }

  function renderDesktop(m) {
    const pc = m && m.pc;
    if (!pc) {
      for (const id of ["pc-lock", "pc-idle", "pc-display", "pc-probe", "pc-motion"]) {
        setText($(id), m ? "unknown" : "—", "");
      }
    } else {
      const lock = { true: ["Locked", "bad"], false: ["Unlocked", "good"] }[String(pc.locked)] || ["Unknown", ""];
      setText($("pc-lock"), lock[0], lock[1]);
      const idle = pc.owner_idle_seconds != null ? pc.owner_idle_seconds : pc.idle_seconds;
      setText($("pc-idle"), idle == null ? "unknown" : dur(idle), "");
      const disp = pc.display_asleep;
      setText($("pc-display"), disp == null ? "unknown" : disp ? "Asleep" : "On", disp ? "warnc" : "");
      const probe = {
        ok: ["OK", "good"],
        degraded: [`Degraded (${pc.probe_failures ?? "?"} fails)`, "bad"],
        unknown: ["Unknown", ""],
      }[pc.probe_state] || ["Unknown", ""];
      setText($("pc-probe"), probe[0], probe[1]);
      setText($("pc-motion"), pc.human_motion == null ? "unknown" : pc.human_motion ? "Human-like" : "Direct", "");
    }
    const jig = view_jiggler;
    const sw = $("jiggler");
    sw.disabled = !started || !jig;
    if (jig && jig.enabled != null && !sw.matches(":focus")) sw.checked = !!jig.enabled;
    let label = "off";
    let cls = "chip chip-quiet";
    if (jig && jig.enabled) {
      label = jig.active ? `drifting · ${jig.moves ?? 0} moves` : "armed";
      cls = jig.active ? "chip chip-info" : "chip chip-ok";
    }
    setText($("jiggler-state"), label, cls);
  }
  let view_jiggler = null;

  function renderFeed(m) {
    const body = $("feed");
    const rows = (m && m.feed) || [];
    const counts = (m && m.counts) || {};
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    setText($("counts"), total ? `${total} total · ${Object.keys(counts).sort().map((k) => `${k} ${counts[k]}`).join(" · ")}` : "");
    const bar = $("statebar");
    bar.replaceChildren();
    for (const k of Object.keys(counts).sort()) {
      const seg = document.createElement("span");
      seg.style.flexGrow = String(counts[k]);
      seg.style.background = STATE_COLOR[k] || "#7a8cff";
      seg.title = `${k}: ${counts[k]}`;
      bar.appendChild(seg);
    }
    body.replaceChildren();
    if (!rows.length) {
      const tr = document.createElement("tr");
      tr.className = "empty";
      const td = document.createElement("td");
      td.colSpan = 4;
      td.textContent = "No acts yet";
      tr.appendChild(td);
      body.appendChild(tr);
      return;
    }
    const seen = new Set();
    for (const row of rows) {
      const tr = document.createElement("tr");
      if (!lastFeedIds.has(row.id8) && lastFeedIds.size) tr.className = "fresh";
      seen.add(row.id8);
      const cells = [row.id8, row.op, null, `${dur(row.age_s)} ago`];
      cells.forEach((v, i) => {
        const td = document.createElement("td");
        if (i === 2) {
          const chip = document.createElement("span");
          chip.className = `chip ${STATE_CHIP[row.state] || "chip-info"}`;
          chip.textContent = row.state;
          td.appendChild(chip);
        } else {
          td.textContent = v;
        }
        if (i === 3) td.className = "num";
        tr.appendChild(td);
      });
      body.appendChild(tr);
    }
    lastFeedIds = seen;
  }

  function appendLog(entries) {
    if (!entries.length) return;
    const box = $("log");
    const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
    const filter = $("log-filter").value.trim().toLowerCase();
    for (const e of entries) {
      const div = document.createElement("div");
      const line = String(e.line);
      let cls = "ln";
      if (/ERROR|FAILED|LOCKOUT|DEGRADED/.test(line)) cls += " err";
      else if (/WARNING|giving up|not restarting/i.test(line)) cls += " warn";
      else if (/\] hands: /.test(line)) cls += " hands";
      div.className = cls;
      const m = line.match(/^(\[\d\d:\d\d:\d\d\])\s?(.*)$/s);
      if (m) {
        const ts = document.createElement("span");
        ts.className = "ts";
        ts.textContent = m[1] + " ";
        div.appendChild(ts);
        div.appendChild(document.createTextNode(m[2]));
      } else {
        div.textContent = line;
      }
      div.dataset.text = line.toLowerCase();
      if (filter && !div.dataset.text.includes(filter)) div.hidden = true;
      box.appendChild(div);
    }
    while (box.childElementCount > 600) box.firstElementChild.remove();
    if (atBottom) box.scrollTop = box.scrollHeight;
  }

  function renderElevation(list) {
    const modal = $("elevation");
    if (!list || !list.length) {
      if (!modal.hidden) modal.hidden = true;
      elevation = null;
      return;
    }
    const req = list[0];
    if (!elevation || elevation.id !== req.id) {
      elevation = req;
      setText($("elev-title"), req.name || "(unnamed request)");
      setText($("elev-command"), `${req.exe}${req.args ? " " + req.args : ""}`);
      modal.hidden = false;
      $("elev-deny").focus();  // the safe choice has focus
    }
    const more = $("elev-more");
    more.hidden = list.length < 2;
    if (list.length > 1) setText(more, `${list.length - 1} more request(s) waiting after this one.`);
    const left = 120 - (Date.now() / 1000 - req.shown_at);
    setText($("elev-countdown"), left > 0 ? `Expires in about ${Math.ceil(left)}s` : "Expiring…");
  }

  function render(view) {
    started = view.started;
    if (started && !startedAt) startedAt = Date.now();
    const phase = phaseOf(view);
    document.body.dataset.phase = phase;
    setText($("phase-text"), { idle: "Stopped", starting: "Starting…", running: "All systems running", degraded: "Attention needed" }[phase]);
    $("btn-start").disabled = started || busy;
    $("btn-start").classList.toggle("is-running", started);
    setText($("start-label"), started ? "Running" : busy ? "Starting…" : "Start");
    $("btn-reveal").disabled = !view.token_ready;
    $("btn-copy-token").disabled = !view.token_ready;
    if (view.token_ready && !tokenShown) {
      setText($("token"), "•••• •••• •••• ••••", "token ready");
    }
    const auto = $("autostart");
    if (!auto.matches(":focus")) auto.checked = !!view.autostart;
    view_jiggler = view.jiggler;
    renderTiles(view);
    renderClaim(view.model);
    renderDesktop(view.model);
    renderFeed(view.model);
    appendLog(view.log || []);
    logSeq = Math.max(logSeq, view.log_seq || 0);
    renderElevation(view.elevations);
  }

  // ------------------------------------------------------------ loop
  let failures = 0;
  async function tick() {
    try {
      const { status, data } = await api(`/api/state?since=${logSeq}`);
      if (status === 200 && data.ok) {
        failures = 0;
        render(data);
      } else {
        failures++;
      }
    } catch (_) {
      failures++;
    }
    if (failures === 3) toast("Lost contact with the relay controller", true);
    setTimeout(tick, 1000);
  }

  // --------------------------------------------------------- actions
  $("btn-start").addEventListener("click", async () => {
    busy = true;
    $("btn-start").disabled = true;
    const { data } = await api("/api/start", { method: "POST" });
    busy = false;
    if (!data.ok) toast("Start failed", true);
  });

  $("btn-stop").addEventListener("click", async () => {
    const msg = started
      ? "Stop all three services and close the relay?"
      : "Close the relay?";
    if (!confirm(msg)) return;
    await api("/api/stop", { method: "POST" });
  });

  $("autostart").addEventListener("change", async (e) => {
    const want = e.target.checked;
    const { data } = await api("/api/autostart", { method: "POST", body: { enabled: want } });
    if (!data.ok) {
      e.target.checked = !!data.autostart;
      toast("Start on login could not be changed", true);
    } else {
      toast(want ? "Will start on login (and wait for Start)" : "Start on login turned off");
    }
  });

  $("jiggler").addEventListener("change", async (e) => {
    const want = e.target.checked;
    const { data } = await api("/api/jiggler", { method: "POST", body: { enabled: want } });
    if (!data.ok) {
      e.target.checked = !want;
      toast(`Jiggler: ${data.message || "not changed"}`, true);
    } else {
      toast(want ? "Idle jiggler on" : "Idle jiggler off");
    }
  });

  async function fetchToken() {
    const { data } = await api("/api/token");
    return data.ok ? data.token : null;
  }

  $("btn-reveal").addEventListener("click", async () => {
    if (tokenShown) {
      tokenShown = false;
      setText($("token"), "•••• •••• •••• ••••", "token ready");
      setText($("btn-reveal"), "Show");
      return;
    }
    const tok = await fetchToken();
    if (!tok) return toast("Token not available yet", true);
    tokenShown = true;
    setText($("token"), tok, "token ready");
    setText($("btn-reveal"), "Hide");
  });

  $("btn-copy-token").addEventListener("click", async () => {
    const tok = await fetchToken();
    if (!tok) return toast("Token not available yet", true);
    toast((await copy(tok)) ? "Token copied" : "Copy failed", false);
  });

  $("btn-diag").addEventListener("click", async () => {
    const { data } = await api("/api/diagnostics", { method: "POST" });
    if (!data.ok) return toast("Nothing to report yet — start the services first", true);
    toast((await copy(data.text)) ? "Diagnostics copied" : "Copy failed", false);
  });

  $("log-filter").addEventListener("input", (e) => {
    const f = e.target.value.trim().toLowerCase();
    for (const div of $("log").children) div.hidden = !!f && !div.dataset.text.includes(f);
  });

  async function decide(approved) {
    if (!elevation) return;
    const id = elevation.id;
    $("elev-approve").disabled = true;
    $("elev-deny").disabled = true;
    try {
      const { data } = await api(`/api/elevation/${encodeURIComponent(id)}`, { method: "POST", body: { approved } });
      toast(data.ok ? `Request ${approved ? "approved" : "denied"} — ${data.state}` : (data.error || "Could not resolve"), !data.ok);
    } finally {
      $("elev-approve").disabled = false;
      $("elev-deny").disabled = false;
      elevation = null;
      $("elevation").hidden = true;
    }
  }
  $("elev-approve").addEventListener("click", () => decide(true));
  $("elev-deny").addEventListener("click", () => decide(false));

  tick();
})();
