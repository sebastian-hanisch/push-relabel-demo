"""Dinic-Algorithmus: maximaler Fluss in Phasen mit Niveaugraph und blockierendem Fluss.

Jede Phase besteht aus zwei Teilen. Eine **Breitensuche** vergibt jedem Knoten sein **Niveau** (Zahl der Kanten des kürzesten Weges von S im Restgraphen) und
hält an, sobald T erreicht ist; der **Niveaugraph** enthält nur Restkanten von Niveau k nach Niveau k+1. Darin sucht eine **Tiefensuche** immer wieder einen Weg von S
nach T und füllt ihn auf, bis keiner mehr existiert: der **blockierende Fluss**. Danach ist die Entfernung von S nach T echt gewachsen (mindestens um 1),
also gibt es höchstens |V|-1 Phasen. Eine **Zeigerliste** (current arc) merkt je Knoten, ab welcher Kante es sich lohnt weiterzusuchen: Kanten davor sind voll
oder führen in Sackgassen und werden in dieser Phase nie wieder angesehen. Ohne Zeiger (`current_arc=False`) beginnt jede Wegesuche je Knoten wieder bei der ersten Kante:
dieselben Wege, aber Sackgassen werden immer wieder besucht.

Restkanten wie in der Edmonds-Karp-Demo: Kante 2i ist die Vorwärtskante der Netzkante i (Rest = Kapazität - Fluss), Kante 2i+1 die Rückkante (Rest = Fluss).
Aufwand wird in gescannten Kanten gezählt (jede in einer Adjazenzliste angesehene Restkante), nie in Sekunden.
"""

from collections import deque
from dataclasses import dataclass

from pr_edmonds_karp import _adjacency, _reachable


@dataclass(frozen=True)
class Path:
    nodes: tuple           # Knotenfolge von S nach T
    arcs: tuple            # Restkanten-Indizes (gerade = Vorwärts-, ungerade = Rückkante)
    bottleneck: int
    length: int
    scanned: int           # Tiefensuche-Einträge seit dem vorigen akzeptierten Weg (einschließlich der Sackgassen davor)
    dead: tuple            # in diesem Abschnitt als Sackgasse verlassene Knoten
    uses_back_arc: bool
    flow_after: tuple      # Fluss je Netzkante nach diesem Weg (leer bei keep_flows=False)


@dataclass(frozen=True)
class Phase:
    level: int             # Niveau von T = Zahl der Kanten jedes kürzesten Weges dieser Phase
    levels: tuple          # Niveau je Knoten, -1: in dieser Phase nicht gebraucht (weiter als T oder nicht erreicht)
    level_arcs: tuple      # Restkanten-Indizes des Niveaugraphen
    bfs_scanned: int
    dfs_scanned: int       # gesamt: Summe der Wege plus tail_scanned
    tail_scanned: int      # Tiefensuche-Einträge nach dem letzten akzeptierten Weg (vergeblich)
    tail_dead: tuple
    paths: tuple
    flow_before: tuple     # Fluss je Netzkante vor der Phase (leer bei keep_flows=False)
    value_before: int
    value_after: int

    @property
    def scanned(self):
        return self.bfs_scanned + self.dfs_scanned


@dataclass(frozen=True)
class Result:
    phases: tuple
    flow: tuple              # fertiger Fluss je Netzkante
    value: int
    reach: tuple             # bool je Knoten: von S im Schluss-Restgraphen erreichbar
    co_reach: tuple
    cut_arcs: tuple
    cut_capacity: int
    final_scanned: int       # letzte, gescheiterte Breitensuche (der Beweis)
    unique_cut: bool

    @property
    def n_paths(self):
        return sum(len(p.paths) for p in self.phases)

    @property
    def bfs_total(self):
        return sum(p.bfs_scanned for p in self.phases) + self.final_scanned

    @property
    def dfs_total(self):
        return sum(p.dfs_scanned for p in self.phases)

    @property
    def scanned_total(self):
        return self.bfs_total + self.dfs_total


def _levels(adj, head, res, s, t):
    """Niveaus per Breitensuche. Rückgabe (Niveau je Knoten, Niveau von T oder None, durchsuchte Kanten, erreichte Menge bei Misserfolg).
    Hält an, sobald T erreicht ist: dann sind alle Knoten mit Niveau < Niveau(T) vergeben; weiter entfernte Knoten werden nicht gebraucht und bleiben -1."""
    n = len(adj)
    level = [-1] * n
    level[s] = 0
    queue = deque([s])
    scanned = 0
    while queue:
        u = queue.popleft()
        for e in adj[u]:
            scanned += 1
            v = head[e]
            if res[e] > 0 and level[v] < 0:
                level[v] = level[u] + 1
                if v == t:
                    top = level[t]
                    return [x if 0 <= x < top or i == t else -1 for i, x in enumerate(level)], top, scanned, None
                queue.append(v)
    return level, None, scanned, {i for i in range(n) if level[i] >= 0}


def dinic(net, current_arc=True, keep_flows=True):
    """Maximaler Fluss nach Dinic. `current_arc=False` setzt die Zeiger nach jedem Weg zurück (gleiche Wege, mehr durchsuchte Kanten).
    `keep_flows=False` spart die Flusszustände je Weg (für Verteilungen über viele Netze)."""
    adj, head = _adjacency(net)
    n, s, t = net.n, net.s, net.t
    res = [0] * (2 * net.m)
    for i, (_, _, cap, _, _) in enumerate(net.arcs):
        res[2 * i] = cap
    value = 0
    phases = []

    def flow_now():
        return tuple(net.arcs[i][2] - res[2 * i] for i in range(net.m))

    while True:
        level, top, bfs_scanned, visited = _levels(adj, head, res, s, t)
        if top is None:
            final_scanned = bfs_scanned
            break
        flow_before = flow_now() if keep_flows else ()
        value_before = value
        level_arcs = tuple(e for u in range(n) if level[u] >= 0 for e in adj[u] if res[e] > 0 and level[head[e]] == level[u] + 1)      # Niveaugraph des Restgraphen VOR der Phase
        ptr = [0] * n
        paths, dead_now, dfs_total, since = [], [], 0, 0
        while True:                                        # ein Weg je Durchlauf, bis S keinen Weg mehr hat
            if not current_arc:
                ptr = [0] * n
            arcs = []
            u = s
            found = False
            while True:
                if u == t:
                    found = True
                    break
                advanced = False
                while ptr[u] < len(adj[u]):
                    e = adj[u][ptr[u]]
                    since += 1
                    v = head[e]
                    if res[e] > 0 and level[v] == level[u] + 1:
                        arcs.append(e)
                        u = v
                        advanced = True
                        break
                    ptr[u] += 1
                if advanced:
                    continue
                if u == s:
                    break                                   # S ist erschöpft: der Fluss ist blockierend
                dead_now.append(u)                          # Sackgasse: zurück und diese Kante am Elternknoten überspringen
                e = arcs.pop()
                u = head[e ^ 1]
                ptr[u] += 1
            if not found:
                break
            bottleneck = min(res[e] for e in arcs)
            for e in arcs:
                res[e] -= bottleneck
                res[e ^ 1] += bottleneck
            value += bottleneck
            nodes = (s,) + tuple(head[e] for e in arcs)
            paths.append(Path(nodes, tuple(arcs), bottleneck, len(arcs), since, tuple(dead_now), any(e % 2 for e in arcs), flow_now() if keep_flows else ()))
            dfs_total += since
            since, dead_now = 0, []
        tail = since
        dfs_total += tail
        phases.append(Phase(top, tuple(level), level_arcs, bfs_scanned, dfs_total, tail, tuple(dead_now), tuple(paths), flow_before, value_before, value))
    reach = _reachable(adj, head, res, s)
    co_reach = _reachable(adj, head, res, t, reverse=True)
    cut = tuple(i for i, (u, v, _, _, _) in enumerate(net.arcs) if u in reach and v not in reach)
    return Result(
        phases=tuple(phases), flow=flow_now(), value=value,
        reach=tuple(v in reach for v in range(n)), co_reach=tuple(v in co_reach for v in range(n)),
        cut_arcs=cut, cut_capacity=sum(net.arcs[i][2] for i in cut), final_scanned=final_scanned,
        unique_cut=all(v in reach or v in co_reach for v in range(n)),
    )


def has_augmenting_path(net, flow):
    """Unabhängige Gegenprobe: gibt es zu diesem Fluss noch einen Verbesserungsweg?"""
    adj, head = _adjacency(net)
    res = [0] * (2 * net.m)
    for i, (_, _, c, _, _) in enumerate(net.arcs):
        res[2 * i] = c - flow[i]
        res[2 * i + 1] = flow[i]
    return net.t in _reachable(adj, head, res, net.s)
