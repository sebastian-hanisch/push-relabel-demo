"""Push-Relabel-Algorithmus (Goldberg und Tarjan): maximaler Fluss ohne Wege, mit Überschüssen und Höhen.

Ein **Preflow** darf an Knoten mehr hineinfließen lassen, als herausfließt: der Überschuss (excess) e(v) >= 0. Jeder Knoten hat eine **Höhe** h(v): h(S) = n, h(T) = 0, und für jede
Restkante u -> v gilt h(u) <= h(v) + 1 (gültige Markierung). Zu Beginn sättigt man alle Kanten aus S (dadurch entstehen Überschüsse) und hebt sonst nichts an. Ein Knoten mit Überschuss
heißt **aktiv**; er wird **entladen**: **push** schiebt Überschuss über eine zulässige Kante (Rest > 0 und h(u) = h(v) + 1) genau eine Stufe bergab, **relabel** hebt den Knoten auf 1 + kleinste Höhe
eines Restnachbarn an, wenn keine Kante zulässig ist. Solange h(S) = n gilt, gibt es keinen S-T-Weg im Restgraphen (ein Weg hätte höchstens n - 1 Kanten, jede senkt die Höhe um höchstens 1).

**Phase 1** entlädt nur Knoten mit h < n; am Ende ist der Überschuss in T der maximale Flusswert und die Knoten, die T im Restgraphen nicht mehr erreichen, sind die Seite von S eines minimalen Schnitts (die
GRÖSSTE S-Seite - Edmonds-Karp und Dinic finden die kleinste). Der Rest der Überschüsse steckt in Knoten mit h >= n, die T nicht erreichen. **Phase 2** entlädt auch diese Knoten (Höhen bis 2n - 1) und schickt den
Überschuss zurück nach S: erst dann ist der Preflow ein Fluss.

Heuristiken: **Zeigerliste** (current arc) je Knoten; **Gap** (gibt es nach einem relabel keine Höhe k < n mehr, kommt keiner der Knoten darüber noch zu T: sie wandern auf n + 1);
**Global Relabeling** (alle n relabels und am Anfang werden die Höhen durch die exakten Entfernungen zu T - in Phase 2 zu S - ersetzt). Knotenwahl: 'fifo' (Warteschlange), 'highest' (höchster aktiver Knoten),
'generic' (beliebig: der aktive Knoten mit dem kleinsten Index).

Aufwand wird in gescannten Kanten gezählt (jede in Entladung, relabel oder Global Relabeling angesehene Restkante) und in Operationen (push und relabel), nie in Sekunden.
Restkanten wie in den Vorgänger-Demos: Kante 2i ist die Vorwärtskante der Netzkante i (Rest = Kapazität - Fluss), Kante 2i+1 die Rückkante (Rest = Fluss).
"""

from collections import deque
from dataclasses import dataclass

from pr_edmonds_karp import _adjacency

SELECTIONS = ("fifo", "highest", "generic")


@dataclass(frozen=True)
class Frame:
    """Zustand nach einer Entladung (node = None: Start nach dem Preflow, kind 'phase1_end': Ende von Phase 1)."""
    kind: str              # 'start' | 'discharge' | 'phase1_end'
    phase: int             # 1 oder 2
    node: object           # entladener Knoten oder None
    pushes: tuple          # ((Restkante, Menge), ...)
    relabels: tuple        # ((von, nach), ...) Höhenänderungen dieser Entladung
    gap: bool              # in dieser Entladung wurde ein Gap-Ereignis ausgelöst
    global_relabel: bool   # nach dieser Entladung wurden alle Höhen neu berechnet
    scanned: int
    heights: tuple
    excess: tuple
    flow: tuple            # Preflow je Netzkante
    value: int             # Überschuss in T


@dataclass(frozen=True)
class Result:
    value: int
    flow: tuple                # fertiger Fluss (nach Phase 2) je Netzkante
    frames: tuple              # leer bei keep_trace=False
    s_side: tuple              # bool je Knoten: Seite von S des minimalen Schnitts (größte S-Seite)
    cut_arcs: tuple
    cut_capacity: int
    pushes_sat: int
    pushes_nonsat: int
    relabels: int
    scanned: int
    gaps: int
    globals_: int
    max_height: int
    by_phase: tuple            # ((Entladungen, Pushes, Relabels, durchsuchte Kanten), (... Phase 2))

    @property
    def pushes(self):
        return self.pushes_sat + self.pushes_nonsat

    @property
    def operations(self):
        return self.pushes + self.relabels

    @property
    def discharges(self):
        return self.by_phase[0][0] + self.by_phase[1][0]


def push_relabel(net, selection="fifo", gap=True, global_relabel=True, keep_trace=True):
    """Maximaler Fluss nach Push-Relabel. `gap` und `global_relabel` schalten die beiden Heuristiken; `selection` wählt die Knotenreihenfolge."""
    if selection not in SELECTIONS:
        raise ValueError(selection)
    adj, head = _adjacency(net)
    n, s, t = net.n, net.s, net.t
    res = [0] * (2 * net.m)
    for i, (_, _, cap, _, _) in enumerate(net.arcs):
        res[2 * i] = cap
    excess = [0] * n
    h = [0] * n
    h[s] = n
    count = [0] * (2 * n + 2)                       # Zahl der Knoten je Höhe (für den Gap)
    stats = {"sat": 0, "nonsat": 0, "relabels": 0, "gaps": 0, "globals": 0}
    by_phase = [[0, 0, 0, 0], [0, 0, 0, 0]]        # Entladungen, Pushes, Relabels, durchsuchte Kanten je Phase
    frames = []
    phase = [1]

    def flow_now():
        return tuple(net.arcs[i][2] - res[2 * i] for i in range(net.m))

    def snapshot(kind, node, pushes, relabels, gap_event, global_event, scanned):
        if keep_trace:
            frames.append(Frame(kind, phase[0], node, tuple(pushes), tuple(relabels), gap_event, global_event, scanned, tuple(h), tuple(excess), flow_now(), excess[t]))

    def allowed(v):
        return v != s and v != t and excess[v] > 0 and (phase[0] == 2 or h[v] < n)

    def recount():
        for k in range(len(count)):
            count[k] = 0
        for v in range(n):
            count[h[v]] += 1

    def global_heights():
        """Höhen durch die exakten Entfernungen ersetzen (Phase 1: zu T, unerreichbare Knoten auf n; Phase 2: n + Entfernung zu S). Höhen sinken nie. Gibt die durchsuchten Kanten zurück."""
        target = t if phase[0] == 1 else s
        base = 0 if phase[0] == 1 else n
        dist = {target: 0}
        queue = deque([target])
        scanned = 0
        while queue:
            v = queue.popleft()
            for e in adj[v]:
                scanned += 1
                w = head[e]
                if w not in dist and res[e ^ 1] > 0:        # w -> v hat Rest: w erreicht das Ziel über v
                    dist[w] = dist[v] + 1
                    queue.append(w)
        for v in range(n):
            if v == s or v == t:
                continue
            if v in dist:
                if phase[0] == 1 or h[v] >= n:              # Phase 2: nur Knoten auf der Seite von S; die Knoten, die T erreichen, bleiben unberührt (sie bekommen nie Überschuss)
                    h[v] = max(h[v], base + dist[v])
            elif phase[0] == 1:
                h[v] = max(h[v], n)
        recount()
        return scanned

    # --- Preflow: alle Kanten aus S sättigen -------------------------------------------------------------------------------------
    for e in adj[s]:
        if e % 2 == 0 and res[e] > 0:
            amount = res[e]
            res[e] = 0
            res[e ^ 1] += amount
            excess[head[e]] += amount
            excess[s] -= amount
    recount()
    start_scans = 0
    if global_relabel:
        start_scans = global_heights()
        stats["globals"] += 1
        by_phase[0][3] += start_scans
    snapshot("start", None, (), (), False, global_relabel, start_scans)

    ptr = [0] * n
    queue = deque(v for v in range(n) if allowed(v))
    queued = set(queue)
    active = set(queue)                              # für highest und generic
    relabels_since_global = [0]

    def pick():
        if selection == "fifo":
            while queue:
                v = queue.popleft()
                queued.discard(v)
                if allowed(v):
                    return v
            return None
        pool = [v for v in active if allowed(v)]
        active.intersection_update(pool)
        if not pool:
            return None
        return max(pool, key=lambda v: (h[v], -v)) if selection == "highest" else min(pool)

    def activate(v):
        if allowed(v):
            active.add(v)
            if v not in queued:
                queue.append(v)
                queued.add(v)

    def discharge(u):
        """Entlädt u. Rückgabe (Pushes, Relabels, Gap-Ereignis, durchsuchte Kanten)."""
        pushes, relabels, gap_event, scanned = [], [], False, 0
        p = phase[0] - 1
        while allowed(u):
            if ptr[u] < len(adj[u]):
                e = adj[u][ptr[u]]
                scanned += 1
                v = head[e]
                if res[e] > 0 and h[u] == h[v] + 1:
                    amount = min(excess[u], res[e])
                    res[e] -= amount
                    res[e ^ 1] += amount
                    excess[u] -= amount
                    excess[v] += amount
                    pushes.append((e, amount))
                    by_phase[p][1] += 1
                    if res[e] == 0:
                        stats["sat"] += 1
                    else:
                        stats["nonsat"] += 1
                    activate(v)
                    if excess[u] == 0:
                        break                         # die Kante kann noch zulässig sein: Zeiger bleibt
                ptr[u] += 1
                continue
            # relabel
            scanned += len(adj[u])
            old = h[u]
            new = 1 + min(h[head[e]] for e in adj[u] if res[e] > 0)
            if gap and phase[0] == 1 and old < n and count[old] == 1:
                stats["gaps"] += 1
                gap_event = True
                for v in range(n):
                    if v != s and old <= h[v] < n:
                        count[h[v]] -= 1
                        h[v] = n + 1
                        count[n + 1] += 1
                relabels.append((old, n + 1))
                stats["relabels"] += 1
                by_phase[p][2] += 1
                relabels_since_global[0] += 1
                ptr[u] = 0
                break
            count[old] -= 1
            h[u] = new
            count[new] += 1
            ptr[u] = 0
            relabels.append((old, new))
            stats["relabels"] += 1
            by_phase[p][2] += 1
            relabels_since_global[0] += 1
        by_phase[p][3] += scanned
        return pushes, relabels, gap_event, scanned

    def run_phase():
        while True:
            u = pick()
            if u is None:
                return
            phase_idx = phase[0] - 1
            by_phase[phase_idx][0] += 1
            pushes, relabels, gap_event, scanned = discharge(u)
            did_global = False
            if global_relabel and relabels_since_global[0] >= n:
                relabels_since_global[0] = 0
                extra = global_heights()
                by_phase[phase_idx][3] += extra
                scanned += extra
                stats["globals"] += 1
                did_global = True
                for v in range(n):
                    ptr[v] = 0
                queue.clear()
                queued.clear()
                active.clear()
                for v in range(n):
                    if allowed(v):
                        queue.append(v)
                        queued.add(v)
                        active.add(v)
            elif allowed(u):
                activate(u)
            snapshot("discharge", u, pushes, relabels, gap_event, did_global, scanned)

    run_phase()
    # --- Ende Phase 1: Wert und minimaler Schnitt ------------------------------------------------------------------------------
    value = excess[t]
    reach_t = {t}
    q = deque([t])
    while q:
        v = q.popleft()
        for e in adj[v]:
            w = head[e]
            if w not in reach_t and res[e ^ 1] > 0:
                reach_t.add(w)
                q.append(w)
    s_side = tuple(v not in reach_t for v in range(n))
    cut = tuple(i for i, (u, v, _, _, _) in enumerate(net.arcs) if s_side[u] and not s_side[v])
    snapshot("phase1_end", None, (), (), False, False, 0)
    # --- Phase 2: Überschuss zurück nach S -----------------------------------------------------------------------------------------
    phase[0] = 2
    ptr = [0] * n
    relabels_since_global[0] = 0
    if global_relabel and any(excess[v] > 0 for v in range(n) if v not in (s, t)):
        extra = global_heights()
        by_phase[1][3] += extra
        stats["globals"] += 1
    queue.clear()
    queued.clear()
    active.clear()
    for v in range(n):
        if allowed(v):
            queue.append(v)
            queued.add(v)
            active.add(v)
    run_phase()
    return Result(
        value=value, flow=flow_now(), frames=tuple(frames), s_side=s_side, cut_arcs=cut, cut_capacity=sum(net.arcs[i][2] for i in cut),
        pushes_sat=stats["sat"], pushes_nonsat=stats["nonsat"], relabels=stats["relabels"], scanned=by_phase[0][3] + by_phase[1][3], gaps=stats["gaps"], globals_=stats["globals"],
        max_height=max(h), by_phase=(tuple(by_phase[0]), tuple(by_phase[1])),
    )
