"""Unabhängiges Orakel: zufällige Kleinstnetze (Parallel- und Gegenkanten, Kanten in S hinein und aus T heraus, Kapazität 0, Sackgassen) gegen networkx und scipy (Flusswert) und gegen die
Aufzählung aller S-T-Schnitte (kleinste und größte S-Seite aller minimalen Schnitte). Alle zwölf Kombinationen aus Knotenwahl und Heuristiken: Wert, fertiger Fluss, Schnitt, und nach jeder Entladung
gültige Markierung (h(u) <= h(v) + 1 auf jeder Restkante), Höhen sinken nie, jedes relabel hebt strikt.
Fund: das Global Relabeling in Phase 2 hob nur Knoten mit h >= n an; ein Knoten der Seite von S mit alter Höhe < n (ohne Überschuss, erreicht T nicht mehr) behielt seine Höhe, die Markierung wurde
ungültig und ein relabel konnte eine Höhe senken. Betraf die Konfiguration „nur Global Relabeling“ in etwa 5 % der Zufallsnetze."""

import random

import pytest

import pr_algorithm as pr
import pr_dinic as dn
import pr_edmonds_karp as ek
import pr_scenario as sc

nx = pytest.importorskip("networkx")


def _instance(rng):
    n = rng.randint(3, 9)
    arcs = []
    for _ in range(rng.randint(n, 3 * n)):
        u, v = rng.randrange(n), rng.randrange(n)
        if u != v:
            arcs.append((u, v, rng.choice([0, 1, 1, 2, 3, 4, 5, 7])))
    net = sc.Net(tuple(f"n{i}" for i in range(n)), tuple(f"n{i}" for i in range(n)), tuple((i, 0) for i in range(n)), tuple((u, v, c, 1, sc.K_OTHER) for u, v, c in arcs), 0, 1, False)
    return n, arcs, net


def _max_flow_value(n, arcs):
    g = nx.DiGraph()
    g.add_nodes_from(range(n))
    for u, v, c in arcs:
        g.add_edge(u, v, capacity=g[u][v]["capacity"] + c if g.has_edge(u, v) else c)
    return nx.maximum_flow_value(g, 0, 1)


def _minimum_cuts(n, arcs):
    """Alle S-Seiten minimaler Schnitte durch Aufzählung aller Knotenmengen."""
    others = list(range(2, n))
    best, sides = None, []
    for mask in range(1 << len(others)):
        side = {0} | {others[i] for i in range(len(others)) if mask >> i & 1}
        cap = sum(c for u, v, c in arcs if u in side and v not in side)
        if best is None or cap < best:
            best, sides = cap, [side]
        elif cap == best:
            sides.append(side)
    return best, sides


CONFIGS = [(sel, gap, glob) for sel in pr.SELECTIONS for gap in (True, False) for glob in (True, False)]


def test_random_small_nets_all_configurations():
    rng = random.Random(20261004)
    for _ in range(40):
        n, arcs, net = _instance(rng)
        expected = _max_flow_value(n, arcs)
        best, sides = _minimum_cuts(n, arcs)
        assert best == expected
        largest, smallest = max(sides, key=len), min(sides, key=len)
        for sel, gap, glob in CONFIGS:
            res = pr.push_relabel(net, sel, gap, glob)
            assert res.value == expected and res.cut_capacity == expected
            balance = [0] * n
            for (u, v, c), f in zip(arcs, res.flow):
                assert 0 <= f <= c
                balance[u] += f
                balance[v] -= f
            assert balance == [expected] + [-expected] + [0] * (n - 2)
            assert {v for v in range(n) if res.s_side[v]} == largest                       # größte S-Seite aller minimalen Schnitte
            prev = res.frames[0]
            for fr in res.frames:
                h = fr.heights
                assert h[0] == n and h[1] == 0 and max(h) <= 2 * n - 1, (sel, gap, glob)
                for (u, v, c), f in zip(arcs, fr.flow):
                    assert f >= c or h[u] <= h[v] + 1, (sel, gap, glob, arcs)               # gültige Markierung
                    assert f <= 0 or h[v] <= h[u] + 1, (sel, gap, glob, arcs)
                assert all(a <= b for a, b in zip(prev.heights, h)), (sel, gap, glob, arcs)  # Höhen sinken nie
                assert all(new > old for old, new in fr.relabels)
                prev = fr
        for e in (ek.max_flow(net, "bfs"), dn.dinic(net)):
            assert e.value == expected and {v for v in range(n) if e.reach[v]} == smallest and e.unique_cut == (len(sides) == 1)
