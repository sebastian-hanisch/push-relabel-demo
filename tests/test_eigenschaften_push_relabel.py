"""Eigenschaftstests (metamorph) für Push-Relabel: Aussagen, die für den maximalen Fluss gelten müssen, ohne dass man das richtige Ergebnis kennt (ORACLE-PLAYBOOK §5.2).
Die Orakel-Tests prüfen Wert, Fluss, Schnitt und die Invarianten je Entladung gegen networkx, scipy und Aufzählung; hier wird die Eingabe auf eine Weise verändert, deren Wirkung bekannt ist.

1. Umnummerieren der Knoten und Umsortieren der Kanten (auch von S und T) ändert Wert und - mit umbenannt - die größte S-Seite nicht (alle zwölf Konfigurationen, dazu die Lehrnetze).
2. Alle Kapazitäten mal c > 0: Wert mal c, dieselbe S-Seite, dieselben Schnittkanten, der Fluss bleibt zulässig.
3. Eine zusätzliche Kante senkt den Wert nie; eine um d größere Kapazität erhöht ihn um höchstens d (wird sie um d kleiner, sinkt er um höchstens d).
4. Eine Kante in zwei parallele Kanten aufteilen und Kanten mit Kapazität 0 ergänzen ändert weder Wert noch S-Seite.
5. Netz umkehren (alle Kanten gedreht, S und T getauscht): derselbe Wert (Dualität), und die größte S-Seite des umgekehrten Netzes ist das Komplement der von S erreichbaren Knoten bei Edmonds-Karp (kleinste S-Seite).
6. Über die Bilder: Der Überschuss in T ist nie fallend, Phase 2 ändert den Wert nicht mehr, und in Phase 1 steht im Zufluss-Überschuss genau die Kapazität aus S (Summe der Überschüsse 0).
7. Minimaler Schnitt aus den Höhen (MIT 15.082J, Vorlesung 11, Folien 16-17): Am Ende von Phase 1 liegt die kleinste unbesetzte Höhe k* zwischen 1 und n - 1; die Knoten oberhalb von k* bilden einen
   Schnitt, dessen Kapazität der Flusswert ist, und sie gehören zur S-Seite (Knoten, die T nicht erreichen).
8. Höhen sind Untergrenzen (MIT 15.082J, Vorlesung 11, Folie 6, Lemma zu den Distanzmarken): in jedem Bild ist h(v) höchstens die Restentfernung von v zu T (bzw. n + Restentfernung zu S), und S erreicht T nie.
Alle mit festem Seed, 20 bis 50 Zufallsnetze je Eigenschaft, Kleinstfälle (zwei Knoten, keine Kante, Kapazität 0, Gleichstände) eingeschlossen."""

import random
from collections import Counter, deque

import pytest

import pr_algorithm as pr
import pr_edmonds_karp as ek
import pr_scenario as sc

CONFIGS = [(sel, gap, glob) for sel in pr.SELECTIONS for gap in (True, False) for glob in (True, False)]


def _net(n, arcs, s=0, t=1):
    """Netz aus (u, v, Kapazität)-Kanten; Knoten 0 = S und 1 = T, wenn nicht anders angegeben."""
    return sc.Net(tuple(f"n{i}" for i in range(n)), tuple(f"n{i}" for i in range(n)), tuple((i, 0) for i in range(n)), tuple((u, v, c, 1, sc.K_OTHER) for u, v, c in arcs), s, t, False)


def _instances(count, seed):
    """(n, arcs) mit Parallel- und Gegenkanten, Kapazität 0 und Gleichständen; die ersten Fälle sind die Randfälle."""
    edge = [(2, []), (2, [(0, 1, 5)]), (2, [(0, 1, 0)]), (3, [(0, 2, 4), (2, 1, 4)]), (3, [(0, 2, 4)]), (4, [(0, 2, 1), (0, 3, 1), (2, 1, 1), (3, 1, 1)]), (5, [(2, 3, 2), (3, 4, 2)])]
    rng = random.Random(seed)
    out = list(edge)
    while len(out) < count:
        n = rng.randint(2, 9)
        arcs = []
        for _ in range(rng.randint(n, 3 * n)):
            u, v = rng.randrange(n), rng.randrange(n)
            if u != v:
                arcs.append((u, v, rng.choice([0, 1, 1, 2, 3, 4, 5, 7])))
        out.append((n, arcs))
    return out


def _run(net, cfg=("fifo", True, True), trace=True):
    return pr.push_relabel(net, cfg[0], cfg[1], cfg[2], keep_trace=trace)


def _is_flow(n, arcs, flow, value, s=0, t=1):
    bal = [0] * n
    for (u, v, c), f in zip(arcs, flow):
        if not 0 <= f <= c:
            return False
        bal[u] -= f
        bal[v] += f
    return all(bal[v] == 0 for v in range(n) if v not in (s, t)) and bal[t] == value == -bal[s]


def test_renumbering_nodes_and_reordering_arcs_changes_nothing_but_the_names():
    rng = random.Random(101)
    for n, arcs in _instances(40, 20261017):
        base = {cfg: _run(_net(n, arcs), cfg) for cfg in CONFIGS}
        perm = list(range(n))
        rng.shuffle(perm)
        arcs2 = [(perm[u], perm[v], c) for u, v, c in arcs]
        rng.shuffle(arcs2)
        net2 = _net(n, arcs2, perm[0], perm[1])
        for cfg in CONFIGS:
            a, b = base[cfg], _run(net2, cfg)
            assert a.value == b.value and a.cut_capacity == b.cut_capacity, (cfg, n, arcs)
            assert all(a.s_side[v] == b.s_side[perm[v]] for v in range(n)), (cfg, n, arcs)       # größte S-Seite ist eindeutig, also mit umbenannt gleich
            assert _is_flow(n, arcs2, b.flow, b.value, perm[0], perm[1])
    for k in range(1, 6):                                              # Lehrnetze mit Gleichständen: bekannter Wert (Zuordnung: k + 1 Paare; Treppe: k (k + 3) / 2 Paare, perfekte Zuordnung)
        for net, expected in ((sc.assignment(k), k + 1), (sc.staircase(k), k * (k + 3) // 2)):
            arcs = [(u, v, c) for u, v, c, _, _ in net.arcs]
            perm = list(range(net.n))
            rng.shuffle(perm)
            arcs2 = [(perm[u], perm[v], c) for u, v, c in arcs]
            rng.shuffle(arcs2)
            for cfg in CONFIGS[::3]:
                assert _run(net, cfg, False).value == expected == _run(_net(net.n, arcs2, perm[0], perm[1]), cfg, False).value


def test_scaling_all_capacities_scales_the_value_and_keeps_the_cut():
    for n, arcs in _instances(40, 7001):
        base = _run(_net(n, arcs))
        for c in (2, 3, 7):
            arcs2 = [(u, v, c * cap) for u, v, cap in arcs]
            scaled = _run(_net(n, arcs2))
            assert scaled.value == c * base.value and scaled.cut_capacity == c * base.cut_capacity, (c, n, arcs)
            assert scaled.s_side == base.s_side and scaled.cut_arcs == base.cut_arcs, (c, n, arcs)
            assert _is_flow(n, arcs2, scaled.flow, scaled.value)


def test_more_capacity_never_hurts_and_changes_the_value_by_at_most_the_amount():
    rng = random.Random(42)
    for n, arcs in _instances(50, 31337):
        v0 = _run(_net(n, arcs), trace=False).value
        u, v = rng.randrange(n), rng.randrange(n)
        if u != v:                                                      # zusätzliche Kante
            cap = rng.randint(0, 6)
            assert _run(_net(n, arcs + [(u, v, cap)]), trace=False).value in range(v0, v0 + cap + 1), (n, arcs, u, v, cap)
        if arcs:
            i, d = rng.randrange(len(arcs)), rng.randint(1, 5)
            more = list(arcs)
            more[i] = (arcs[i][0], arcs[i][1], arcs[i][2] + d)
            assert v0 <= _run(_net(n, more), trace=False).value <= v0 + d, (n, arcs, i, d)
            less = list(arcs)
            d = min(d, arcs[i][2])
            less[i] = (arcs[i][0], arcs[i][1], arcs[i][2] - d)
            assert v0 - d <= _run(_net(n, less), trace=False).value <= v0, (n, arcs, i, d)


def test_splitting_arcs_in_parallel_and_adding_zero_capacity_arcs_changes_nothing():
    rng = random.Random(5)
    for n, arcs in _instances(40, 99):
        base = _run(_net(n, arcs))
        arcs2 = []
        for u, v, c in arcs:
            c1 = rng.randint(0, c)
            arcs2 += [(u, v, c1), (u, v, c - c1)]
        for _ in range(rng.randint(0, 4)):
            u, v = rng.randrange(n), rng.randrange(n)
            if u != v:
                arcs2.insert(rng.randrange(len(arcs2) + 1), (u, v, 0))
        for cfg in CONFIGS[::2]:
            res = _run(_net(n, arcs2), cfg)
            assert res.value == base.value and res.s_side == base.s_side, (cfg, n, arcs)
            assert _is_flow(n, arcs2, res.flow, res.value)


def test_reversing_the_net_gives_the_same_value_and_the_complementary_cut_side():
    """Dualität: Fluss in G von S nach T = Fluss im umgekehrten Netz von T nach S. Die größte S-Seite des umgekehrten Netzes (Knoten, die S nicht erreichen) ist das Komplement der von S erreichbaren Knoten (Edmonds-Karp)."""
    for n, arcs in _instances(40, 555):
        rev = _net(n, [(v, u, c) for u, v, c in arcs], 1, 0)
        reach = ek.max_flow(_net(n, arcs), "bfs", keep_flows=False).reach
        for cfg in CONFIGS[::4]:
            a, b = _run(_net(n, arcs), cfg), _run(rev, cfg)
            assert a.value == b.value, (cfg, n, arcs)
            assert b.s_side == tuple(not r for r in reach), (cfg, n, arcs)


def test_excess_in_t_never_falls_and_phase_two_does_not_change_the_value():
    """In Phase 1 kommt aus S genau die Kapazität aus S (nichts fließt zu S zurück); Summe der Überschüsse stets 0; der Überschuss in T steigt nur; in Phase 2 ändert er sich nicht mehr."""
    rng = random.Random(8)
    for i in range(40):
        p, d, s = rng.choice([(2, 2, 3), (3, 3, 6), (3, 3, 8), (4, 3, 5), (2, 4, 9)])
        net = sc.generate(p, d, s, rng.choice((20, 60, 100)), rng.choice((0, 50, 100)), rng.choice((40, 90, 160)), 9000 + i)
        for cfg in (("fifo", True, True), ("highest", False, False), ("generic", True, False)):
            res = _run(net, cfg)
            previous = 0
            for fr in res.frames:
                assert sum(fr.excess) == 0 and fr.value == fr.excess[net.t] >= previous
                assert fr.value <= res.value
                if fr.phase == 1:
                    assert fr.excess[net.s] == -net.total_capacity_out_of_s()
                else:
                    assert fr.value == res.value
                previous = fr.value
            end1 = next(f for f in res.frames if f.kind == "phase1_end")
            assert end1.value == res.value
            assert res.frames[-1].excess[net.t] == res.value and all(x == 0 for k, x in enumerate(res.frames[-1].excess) if k not in (net.s, net.t))


def test_the_nodes_above_the_lowest_gap_form_a_minimum_cut_at_the_end_of_phase_one():
    """MIT 15.082J (Herbst 2010), Vorlesung 11, Folien 16-17: S* = Knoten unterhalb des kleinsten Gap-Niveaus k*, T* = Knoten oberhalb; (S*, T*) ist ein minimaler Schnitt mit Kapazität = Flusswert.
    Hier ist die Seite von S die Menge oberhalb von k*. Ein Gap-Niveau in 1..n-1 gibt es immer (n - 2 Knoten für n - 1 Niveaus)."""
    checked = 0
    for n, arcs in _instances(50, 4711):
        if n < 3:
            continue
        for cfg in CONFIGS[::3]:
            res = _run(_net(n, arcs), cfg)
            end = next(f for f in res.frames if f.kind == "phase1_end")
            h = end.heights
            k_star = next(k for k in range(1, n) if k not in h)
            above = {v for v in range(n) if h[v] > k_star}
            assert 0 in above and 1 not in above
            assert sum(c for u, v, c in arcs if u in above and v not in above) == res.value, (cfg, n, arcs)
            assert all(res.s_side[v] for v in above), (cfg, n, arcs)
            checked += 1
    assert checked >= 100


def test_heights_are_lower_bounds_of_the_residual_distances_and_s_never_reaches_t():
    """MIT 15.082J, Vorlesung 11, Folie 6: eine gültige Markierung ist eine Untergrenze der Restentfernung zu T; mit h(S) = n heißt das: S erreicht T im Restgraphen nie. Entsprechend h(v) <= n + Entfernung zu S."""
    def distances(n, arcs, flow, target):
        pred = [[] for _ in range(n)]                                     # Restkante a -> b: in pred[b] steht a
        for (u, v, c), f in zip(arcs, flow):
            if f < c:
                pred[v].append(u)
            if f > 0:
                pred[u].append(v)
        dist = {target: 0}
        queue = deque([target])
        while queue:
            b = queue.popleft()
            for a in pred[b]:
                if a not in dist:
                    dist[a] = dist[b] + 1
                    queue.append(a)
        return dist

    for n, arcs in _instances(40, 123):
        for cfg in CONFIGS[::3]:
            res = _run(_net(n, arcs), cfg)
            for fr in res.frames:
                to_t, to_s = distances(n, arcs, fr.flow, 1), distances(n, arcs, fr.flow, 0)
                assert 0 not in to_t, (cfg, n, arcs)                              # S erreicht T nie
                for v in range(n):
                    if v in to_t:
                        assert fr.heights[v] <= to_t[v], (cfg, n, arcs, v)
                    if v in to_s:
                        assert fr.heights[v] <= n + to_s[v], (cfg, n, arcs, v)
