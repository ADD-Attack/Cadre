"""Human-like pointer system + idle jiggler planning (wishlist #24, #28,
#29, #30) — pure, Windows-free, deterministic for a seeded rng.

Everything here PLANS; nothing injects input. muse_relay_hands.py owns
the pyautogui calls, the input mutex instance, the self-input ledger
instance and the jiggler thread, and feeds them through these planners.
Every random parameter is drawn per call from the rng passed in, so no
two movements share a curve (#24/#28 "never a fixed pattern").

Rule -> code map (also in docs/R9-MOTION-DESIGN.md):
  #29 cubic Bezier, 1-2 random control points ...... _control_points
  #29 Fitts velocity profile (slow/fast/hard stop) .. fitts_duration, _progress
  #29 wind/Perlin noise along the path ............... _ValueNoise, plan_move
  #29 40-120 ms pause on target ...................... hover_delay
  #29 Gaussian landing inside the target box ......... landing_point
  #29 click down->up 50-150 ms ....................... click_hold
  #29 scroll in variable chunks with pauses .......... plan_scroll
  #24 arc + sway, velocity jitter, light overshoot ... plan_move (overshoot branch)
  #30 attention buffer 200-700 ms by text volume ..... attention_delay
  #30 structural miss ~15 %, 5-10 px + fast correct .. plan_move (miss branch)
  #30 input mutex + 150-300 ms hand travel ........... InputMutex
  #30 Fitts extension: target size sets speed ........ fitts_duration(width)
  #30 idle drift after 30-60 s, 1-3 px / lazy drift .. plan_jiggle, jiggle_start_after
  #28 intensity decays with idle length .............. plan_jiggle
  #28 jiggler motion is not owner activity ........... SelfInputLedger
  #24 latency budget: <= +0.5 s per click ............ click_budget, fit_click_timing
"""
import math
import threading
import time

# ---------------------------------------------------------------- budget

EXTRA_BUDGET_S = 0.5  # owner-set: at most +0.5 s per click (#24)
MIN_PATH_S = 0.12     # graceful-degradation floor for the travel itself


def legacy_click_seconds(dist):
    """Per-click time of the pre-R9 human click, at its fastest.

    Path clamp(0.25 + d/2500, 0.3, 1.1) plus the minimum 0.05 s hover
    (the pre-R9 click itself was instantaneous). Using the minimum makes
    the +0.5 s budget the conservative reading.
    """
    return min(1.1, max(0.3, 0.25 + dist / 2500.0)) + 0.05


def click_budget(dist):
    """Upper bound for attention + travel + hover + hold on one click."""
    return legacy_click_seconds(dist) + EXTRA_BUDGET_S


def fit_click_timing(dist, attention, path, hover, hold):
    """Shrink the embellishments so the click fits click_budget(dist).

    Degrades in order: attention first, then travel time (not below
    MIN_PATH_S), then hover/hold toward their floors. Returns the
    (attention, path, hover, hold) actually used.
    """
    budget = click_budget(dist)
    total = attention + path + hover + hold
    if total <= budget:
        return attention, path, hover, hold
    over = total - budget
    cut = min(attention, over)
    attention -= cut
    over -= cut
    if over > 0:
        cut = min(max(0.0, path - MIN_PATH_S), over)
        path -= cut
        over -= cut
    if over > 0:
        cut = min(max(0.0, hover - 0.04), over)
        hover -= cut
        over -= cut
    if over > 0:
        hold = max(0.05, hold - over)
    return attention, path, hover, hold


# ------------------------------------------------------- timing draws

def hover_delay(rng):
    """Pause on target before the button goes down (#29): 40-120 ms."""
    return rng.uniform(0.04, 0.12)


def click_hold(rng):
    """Button down->up duration (#29): 50-150 ms."""
    return rng.uniform(0.05, 0.15)


def attention_delay(rng, text_chars=None):
    """Hesitation before moving to a newly rendered target (#30): 200-700 ms.

    Scales with how much text is on screen to "read" (text_chars, the
    caller's estimate); unknown volume draws from the low half.
    """
    if text_chars is None:
        return rng.uniform(0.20, 0.40)
    try:
        chars = max(0, int(text_chars))
    except (TypeError, ValueError):
        return rng.uniform(0.20, 0.40)
    base = 0.20 + min(0.40, chars / 2000.0 * 0.40)
    return min(0.70, base + rng.uniform(0.0, 0.10))


def hand_travel(rng):
    """Keyboard<->mouse hand-travel delay (#30): 150-300 ms."""
    return rng.uniform(0.15, 0.30)


# -------------------------------------------------------- path physics

def fitts_duration(dist, width, rng):
    """Movement time by Fitts's law (#29, #30 size extension).

    MT = a + b * log2(dist / W + 1), with a and b drawn per movement, so
    a tiny target (close box, checkbox) is reached more slowly than a
    large one at the same distance. W defaults to 16 px (a point target
    of unknown size).
    """
    w = max(2.0, float(width)) if width else 16.0
    a = rng.uniform(0.07, 0.12)
    b = rng.uniform(0.08, 0.12)
    return a + b * math.log2(dist / w + 1.0)


def _progress(t, skew):
    """Fraction of the path covered at normalised time t (#29).

    Minimum-jerk profile (zero velocity at both ends, peak in the
    middle) on a warped clock t**skew with skew < 1: the peak arrives
    early and the tail is a long, hard deceleration into the target.
    """
    u = t ** skew
    return 10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5


class _ValueNoise:
    """Smooth 1-D noise (Perlin-style value noise, cosine-interpolated).

    Lattice values are drawn from the rng at construction, so each
    movement gets its own tremor field.
    """

    def __init__(self, rng, octaves=6):
        self.vals = [rng.uniform(-1.0, 1.0) for _ in range(octaves + 2)]
        self.n = octaves

    def __call__(self, s):
        x = s * self.n
        i = min(int(x), self.n)
        f = x - i
        w = (1 - math.cos(f * math.pi)) / 2
        return self.vals[i] * (1 - w) + self.vals[i + 1] * w


def _cubic(p0, c1, c2, p1, t):
    u = 1 - t
    return (
        u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p1[0],
        u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p1[1],
    )


def _control_points(p0, p1, rng):
    """1-2 randomized control points pushed off the chord (#29, #24 arc)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    dist = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / dist, dx / dist
    side = 1 if rng.random() < 0.5 else -1

    def ctrl(along, spread):
        off = side * rng.uniform(0.04, spread) * dist
        a = along + rng.uniform(-0.08, 0.08)
        return (p0[0] + dx * a + nx * off, p0[1] + dy * a + ny * off)

    c1 = ctrl(0.30, 0.20)
    if rng.random() < 0.5:  # one control point: both handles coincide
        return c1, c1
    c2 = ctrl(0.70, 0.12)
    return c1, c2


def _segment(p0, p1, duration, rng, noise_amp=None):
    """One Bezier travel from p0 to p1 lasting `duration`: [(x, y, dt)]."""
    dist = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    n = max(6, min(90, int(duration / rng.uniform(0.010, 0.014))))
    c1, c2 = _control_points(p0, p1, rng)
    skew = rng.uniform(0.78, 0.92)
    amp = noise_amp if noise_amp is not None else min(2.5, 0.006 * dist)
    nx_, ny_ = _ValueNoise(rng), _ValueNoise(rng)
    # Velocity jitter: uneven clock ticks, renormalised to the duration.
    ticks = [rng.uniform(0.85, 1.15) for _ in range(n)]
    scale = duration / sum(ticks)
    steps = []
    t = 0.0
    for i in range(n):
        t += ticks[i] * scale
        s = _progress(min(1.0, t / duration), skew)
        x, y = _cubic(p0, c1, c2, p1, s)
        taper = math.sin(math.pi * s)  # tremor fades to zero at both ends
        x += nx_(s) * amp * taper
        y += ny_(s) * amp * taper
        steps.append((x, y, ticks[i] * scale))
    return steps


def plan_move(x0, y0, x1, y1, rng, width=None, path_seconds=None):
    """Human-like pointer path to (x1, y1): list of (x, y, delay_after).

    The final step is always exactly (x1, y1). Per movement, one of:
      - structural miss (~15 %, #30): aim 5-10 px outside the target,
        then a hyper-fast short correction curve to it;
      - light overshoot + settle-back (~55 %, #24);
      - direct landing.
    path_seconds, when given, is the total travel time (the click budget
    already applied); otherwise Fitts's law decides. A move under 4 px
    is a single step.
    """
    dist = math.hypot(x1 - x0, y1 - y0)
    if dist < 4:
        return [(x1, y1, path_seconds if path_seconds is not None else 0.02)]
    total = path_seconds if path_seconds is not None else fitts_duration(dist, width, rng)
    total = max(0.05, total)
    roll = rng.random()
    ux, uy = (x1 - x0) / dist, (y1 - y0) / dist
    if roll < 0.15 and dist >= 40:
        # Structural miss: land beside the box, then correct fast.
        miss = rng.uniform(5.0, 10.0)
        ang = math.atan2(uy, ux) + rng.uniform(-1.2, 1.2)
        aim = (x1 + math.cos(ang) * miss, y1 + math.sin(ang) * miss)
        main_t = total * rng.uniform(0.74, 0.82)
        steps = _segment((x0, y0), aim, main_t, rng)
        steps += _segment(aim, (x1, y1), total - main_t, rng, noise_amp=0.3)
    elif roll < 0.70 and dist >= 20:
        # Overshoot along the approach direction, then settle back.
        over = min(8.0, max(2.0, dist * rng.uniform(0.01, 0.04)))
        jitter = rng.uniform(-0.3, 0.3)
        ox = x1 + (ux * math.cos(jitter) - uy * math.sin(jitter)) * over
        oy = y1 + (ux * math.sin(jitter) + uy * math.cos(jitter)) * over
        main_t = total * rng.uniform(0.82, 0.90)
        steps = _segment((x0, y0), (ox, oy), main_t, rng)
        steps += _segment((ox, oy), (x1, y1), total - main_t, rng, noise_amp=0.2)
    else:
        steps = _segment((x0, y0), (x1, y1), total, rng)
    steps[-1] = (x1, y1, steps[-1][2])  # exact target, always
    drift = total - sum(s[2] for s in steps)
    steps[-1] = (x1, y1, max(0.0, steps[-1][2] + drift))
    return steps


def landing_point(cx, cy, w, h, rng):
    """Click point inside a w x h box centred on (cx, cy) (#29).

    Gaussian, centre-weighted (sd = size/6); about 1 in 20 draws use a
    wider sd so edge hits happen. Always clamped inside the box with a
    1 px margin. No box (w or h missing/< 3) -> the exact centre.
    """
    try:
        w, h = float(w), float(h)
    except (TypeError, ValueError):
        return int(round(cx)), int(round(cy))
    if w < 3 or h < 3:
        return int(round(cx)), int(round(cy))
    div = 4.0 if rng.random() < 0.05 else 6.0
    x = rng.gauss(cx, w / div)
    y = rng.gauss(cy, h / div)
    hx, hy = w / 2 - 1, h / 2 - 1
    x = min(cx + hx, max(cx - hx, x))
    y = min(cy + hy, max(cy - hy, y))
    return int(round(x)), int(round(y))


def plan_scroll(clicks, rng):
    """Split a scroll into variable chunks with small pauses (#29).

    Returns [(chunk, pause_after)]; chunk signs follow `clicks` and the
    chunks sum to it exactly.
    """
    clicks = int(clicks)
    if clicks == 0:
        return []
    sign = 1 if clicks > 0 else -1
    left = abs(clicks)
    out = []
    while left > 0:
        chunk = min(left, rng.choice((1, 1, 2, 2, 3)))
        left -= chunk
        out.append((sign * chunk, rng.uniform(0.03, 0.12) if left else 0.0))
    return out


# ------------------------------------------------------------- jiggler

JIGGLE_DECAY_S = 240.0  # e-folding time of jiggle size with idle length


def jiggle_start_after(rng):
    """Owner-idle seconds before drift begins, drawn per episode (#30)."""
    return rng.uniform(30.0, 60.0)


def plan_jiggle(idle_into_episode, rng):
    """One jiggle: (dx, dy, wait_before_next_seconds) (#28, #30).

    Intensity decays with idle length: early in an episode, lazy drifts
    up to ~40 px every few seconds; after a long idle, 1-3 px
    micro-jitters minutes apart. Size and wait are both drawn per
    jiggle — the decay is a trend, never a fixed cadence.
    """
    e = max(0.0, float(idle_into_episode))
    decay = math.exp(-e / JIGGLE_DECAY_S)
    if rng.random() < 0.35 * decay:
        amp = rng.uniform(10.0, 40.0) * decay + rng.uniform(1.0, 3.0)
    else:
        amp = rng.uniform(1.0, 3.0)
    ang = rng.uniform(0, 2 * math.pi)
    dx, dy = math.cos(ang) * amp, math.sin(ang) * amp
    wait = rng.uniform(3.0, 10.0) * (1.0 + e / 90.0)
    return dx, dy, min(300.0, wait)


# ------------------------------------------------ self-input ledger

def tick_diff(a, b):
    """a - b on the 32-bit GetTickCount clock (wrap-safe), in ms."""
    d = (int(a) - int(b)) & 0xFFFFFFFF
    return d - 0x100000000 if d >= 0x80000000 else d


class SelfInputLedger:
    """Separate jiggler-injected input from owner input (#28 constraint 2).

    Windows' last-input time (GetLastInputInfo) counts injected input
    too, so jiggler motion would otherwise look like the owner. The
    jiggler records the tick span of every injection; when the OS's
    last-input tick falls inside a recorded span, the input was ours
    and owner idle keeps counting from the owner's last real input.

    The spans are written from tick reads taken around the injection
    (GetTickCount never fails), NOT from a post-injection
    GetLastInputInfo probe — so a failed probe cannot leave a stale
    "self" baseline that later misreads our own motion as the owner's
    (the R7.2 Grok failure mode, avoided by construction).
    """

    SLACK_MS = 120
    MAX_SPANS = 64

    def __init__(self):
        self._lock = threading.Lock()
        self._spans = []
        self._owner_tick = None  # last input tick known to be the owner's

    def record(self, start_tick, end_tick):
        with self._lock:
            self._spans.append((int(start_tick), int(end_tick)))
            del self._spans[: -self.MAX_SPANS]

    def truncate_last(self, end_tick):
        """Close the newest span early (owner fought the move)."""
        with self._lock:
            if self._spans:
                s, _ = self._spans[-1]
                self._spans[-1] = (s, int(end_tick))

    def _is_self(self, tick):
        for s, e in self._spans:
            if tick_diff(tick, s) >= -self.SLACK_MS and tick_diff(e, tick) >= -self.SLACK_MS:
                return True
        return False

    def owner_idle(self, idle_seconds, now_tick):
        """Owner idle seconds given the OS idle and the current tick."""
        if idle_seconds is None or now_tick is None:
            return idle_seconds
        last = (int(now_tick) - int(round(idle_seconds * 1000))) & 0xFFFFFFFF
        with self._lock:
            if not self._is_self(last):
                self._owner_tick = last
                return idle_seconds
            if self._owner_tick is None:
                return idle_seconds  # nothing known about the owner: be honest
            return max(idle_seconds, tick_diff(now_tick, self._owner_tick) / 1000.0)


# --------------------------------------------------------- input mutex

class InputMutex:
    """One input stream at a time + hand-travel between devices (#30).

    acquire(kind) blocks until no other op is injecting; when the
    previous op used the other device ("mouse" vs "keys") and ended
    less than its drawn travel time ago, it sleeps the remainder first.
    try_acquire is the jiggler's non-blocking form: it never waits for
    an op and never makes an op wait for it.
    """

    def __init__(self, clock=time.monotonic, sleep=time.sleep):
        self._lock = threading.RLock()
        self._clock = clock
        self._sleep = sleep
        self._last_kind = None
        self._last_end = None

    def _travel(self, kind, rng):
        if self._last_kind is None or kind == self._last_kind or self._last_end is None:
            return 0.0
        need = hand_travel(rng)
        gap = self._clock() - self._last_end
        return max(0.0, need - gap)

    def acquire(self, kind, rng):
        self._lock.acquire()
        wait = self._travel(kind, rng)
        if wait > 0:
            self._sleep(wait)
        return wait

    def try_acquire(self):
        return self._lock.acquire(blocking=False)

    def release(self, kind):
        self._last_kind = kind
        self._last_end = self._clock()
        self._lock.release()
