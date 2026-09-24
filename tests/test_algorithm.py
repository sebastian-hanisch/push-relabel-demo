"""Kern: Push-Relabel gegen Handfälle und unabhängige Gegenproben (networkx, scipy, Brute Force), Invarianten je Entladung aus dem Trace (gültige Markierung, Überschuss, Erhaltung),
Schnitt als Komplement der von T erreichbaren Knoten, Heuristiken (Gap, Global Relabeling, Zeigerliste), alle neun Konfigurationen."""

import itertools
import random

import networkx as nx
import numpy as np
import pytest
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_flow

import pr_algorithm as pr
import pr_dinic as dn
import pr_edmonds_karp as ek
import pr_scenario as sc
from pr_scenario import SplitMix64

CONFIGS = list(itertools.product(pr.SELECTIONS, ((False, False), (True, False), (True, True))))


def _nets(count, sizes=((2, 2, 3), (3, 3, 6), (3, 3, 8), (4, 3, 5), (2, 4, 9), (6, 6, 12))):
    """Zufällige Distributionsnetze unterschiedlicher Größe, Dichte, Streuung und Auslastung."""
    rng = random.Random(13)
    for i in range(count):
        p, d, s = sizes[i % len(sizes)]
        yield sc.generate(p, d, s, rng.choice((20, 40, 60, 80, 100)), rng.choice((0, 25, 50, 75, 100)), rng.choice((40, 90, 120, 160)), 3000 + i)


def _digraph(net):
    g = nx.DiGraph()
    for u, v, c, _, _ in net.arcs:
        g.add_edge(u, v, capacity=c)
    return g


def _run(net, cfg, trace=True):
    sel, (gap, glob) = cfg
    return pr.push_relabel(net, sel, gap, glob, keep_trace=trace)


def _residual_graph(net, flow):
    g = nx.DiGraph()
    g.add_nodes_from(range(net.n))
    for i, (u, v, c, _, _) in enumerate(net.arcs):
        if c - flow[i] > 0:
            g.add_edge(u, v)
        if flow[i] > 0:
            g.add_edge(v, u)
    return g


def _balance(net, flow):
    bal = [0] * net.n
    for i, (u, v, _, _, _) in enumerate(net.arcs):
        bal[u] -= flow[i]
        bal[v] += flow[i]
    return bal


# --- kopierte Bausteine (Wache gegen einen fehlerhaften Kopiervorgang) ----------------------------------------------------------------------

def test_splitmix64_reference_vector():
    rng = SplitMix64(0)
    assert [rng.next() for _ in range(2)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4]


def test_the_copied_predecessors_reproduce_their_numbers():
    """Edmonds-Karp (Breitensuche) und Dinic stammen aus den Vorgänger-Demos; deren Zahlen über die 100 festen Netze müssen wiederkommen."""
    ek_scans, dn_scans = [], []
    for seed in range(100000, 100100):
        net = sc.generate(3, 3, 8, 60, 50, 90, seed)
        ek_scans.append(ek.max_flow(net, "bfs", keep_flows=False).scanned_total)
        dn_scans.append(dn.dinic(net, keep_flows=False).scanned_total)
    assert sum(ek_scans) == 52475 and sum(dn_scans) == 25367           # Mittel 524,75 und 253,67


# --- Handfälle ---------------------------------------------------------------------------------------------------------------------------------

def test_assignment_chain_by_hand():
    res = pr.push_relabel(sc.assignment(4))
    assert res.value == 5 and (res.pushes, res.relabels, res.scanned) == (36, 12, 185) and res.cut_capacity == 5


def test_staircase_by_hand():
    net = sc.staircase(5)
    res = pr.push_relabel(net)
    assert res.value == 20 and res.discharges == 65 and (res.pushes, res.relabels, res.scanned) == (70, 15, 325)
    assert sum(res.s_side) == 41 and len(res.cut_arcs) == 20                 # die größte S-Seite: alles außer T-nahen Aufträgen; die Kanten A -> T
    assert sum(ek.max_flow(net, "bfs").reach) == 1                            # Edmonds-Karp: nur S


def test_invalid_selection_raises():
    with pytest.raises(ValueError):
        pr.push_relabel(sc.assignment(2), "lifo")


# --- Gegenproben -------------------------------------------------------------------------------------------------------------------------------

def test_value_flow_and_cut_agree_with_networkx_and_scipy_for_every_configuration():
    for net in _nets(36):
        g = _digraph(net)
        expected, _ = nx.minimum_cut(g, net.s, net.t)
        assert nx.maximum_flow_value(g, net.s, net.t, flow_func=nx.algorithms.flow.preflow_push) == expected
        assert nx.maximum_flow_value(g, net.s, net.t, flow_func=nx.algorithms.flow.dinitz) == expected
        mat = np.zeros((net.n, net.n), dtype=np.int32)
        for u, v, c, _, _ in net.arcs:
            mat[u, v] = c
        assert maximum_flow(csr_matrix(mat), net.s, net.t, method="dinic").flow_value == expected
        for cfg in CONFIGS:
            res = _run(net, cfg, trace=False)
            assert res.value == expected == res.cut_capacity
            bal = _balance(net, res.flow)
            assert all(0 <= res.flow[i] <= net.arcs[i][2] for i in range(net.m))
            assert all(bal[v] == 0 for v in range(net.n) if v not in (net.s, net.t)) and bal[net.t] == expected == -bal[net.s]


def test_the_cut_is_a_minimum_cut_by_brute_force():
    for net in _nets(30, sizes=((2, 2, 3), (2, 2, 4))):
        others = [v for v in range(net.n) if v not in (net.s, net.t)]
        best = min(sum(c for u, v, c, _, _ in net.arcs if u in ({net.s} | {w for w, b in zip(others, mask) if b}) and v not in ({net.s} | {w for w, b in zip(others, mask) if b}))
                   for mask in itertools.product((0, 1), repeat=len(others)))
        assert pr.push_relabel(net).cut_capacity == best


def test_the_cut_side_is_everything_that_cannot_reach_t_and_saturates_its_arcs():
    for net in _nets(40):
        res = pr.push_relabel(net)
        g = _residual_graph(net, res.flow)
        reach_t = nx.ancestors(g, net.t) | {net.t}                              # Knoten, die T im Restgraphen des fertigen Flusses erreichen
        assert res.s_side == tuple(v not in reach_t for v in range(net.n))
        assert res.s_side[net.s] and not res.s_side[net.t]
        assert all(res.flow[i] == net.arcs[i][2] for i in res.cut_arcs)
        assert all(res.flow[i] == 0 for i, (u, v, _, _, _) in enumerate(net.arcs) if not res.s_side[u] and res.s_side[v])


def test_same_cut_as_edmonds_karp_exactly_when_the_cut_is_unique_and_never_smaller():
    for net in _nets(60):
        res, e = pr.push_relabel(net), ek.max_flow(net, "bfs")
        pr_side, ek_side = {v for v in range(net.n) if res.s_side[v]}, {v for v in range(net.n) if e.reach[v]}
        assert ek_side <= pr_side and res.cut_capacity == e.cut_capacity
        assert (pr_side == ek_side) == e.unique_cut


# --- Invarianten je Entladung ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("cfg", CONFIGS)
def test_trace_invariants(cfg):
    for net in _nets(15):
        res = _run(net, cfg)
        n = net.n
        assert res.frames[0].kind == "start" and sum(1 for f in res.frames if f.kind == "phase1_end") == 1
        assert len(res.frames) == res.discharges + 2
        prev = res.frames[0]
        for f in res.frames:
            h, e, flow = f.heights, f.excess, f.flow
            assert h[net.s] == n and h[net.t] == 0 and max(h) <= 2 * n - 1
            assert all(x >= 0 for k, x in enumerate(e) if k != net.s)
            bal = _balance(net, flow)
            assert all(bal[v] == e[v] for v in range(n) if v != net.s)                          # Überschuss = Zufluss - Abfluss
            assert all(0 <= flow[i] <= net.arcs[i][2] for i in range(net.m))
            for i, (u, v, c, _, _) in enumerate(net.arcs):                                      # gültige Markierung
                if c - flow[i] > 0:
                    assert h[u] <= h[v] + 1
                if flow[i] > 0:
                    assert h[v] <= h[u] + 1
            assert all(a <= b for a, b in zip(prev.heights, h))                                 # Höhen sinken nie
            if f is not prev:
                moved = [0] * net.m
                for edge, amount in f.pushes:
                    moved[edge // 2] += amount if edge % 2 == 0 else -amount
                assert [flow[i] - prev.flow[i] for i in range(net.m)] == moved
                for old, new in f.relabels:
                    assert new > old
            prev = f
        end1 = next(f for f in res.frames if f.kind == "phase1_end")
        assert not any(end1.excess[v] > 0 and end1.heights[v] < n for v in range(n) if v not in (net.s, net.t))     # Ende von Phase 1: nichts Aktives unterhalb von n
        assert end1.value == res.value == end1.excess[net.t]
        last = res.frames[-1]
        assert all(last.excess[v] == 0 for v in range(n) if v not in (net.s, net.t)) and last.flow == res.flow


@pytest.mark.parametrize("cfg", CONFIGS)
def test_pushes_use_admissible_arcs_when_no_relabel_precedes(cfg):
    """In Entladungen ohne relabel stehen die Höhen fest: jeder Push geht genau eine Stufe bergab über eine Kante mit Rest."""
    for net in _nets(12):
        res = _run(net, cfg)
        for before, f in zip(res.frames, res.frames[1:]):
            if f.kind != "discharge" or f.relabels or before.kind == "phase1_end":      # nach dem Ende von Phase 1 setzt das Global Relabeling von Phase 2 die Höhen neu, ohne eigenes Bild
                continue
            for edge, amount in f.pushes:
                i = edge // 2
                u, v = (net.arcs[i][0], net.arcs[i][1]) if edge % 2 == 0 else (net.arcs[i][1], net.arcs[i][0])
                assert before.heights[u] == before.heights[v] + 1 and amount >= 1


def test_global_relabeling_sets_the_exact_distances_to_t():
    checked = 0
    for net in _nets(30):
        res = pr.push_relabel(net, "fifo", True, True)
        for f in res.frames:
            if f.global_relabel and f.phase == 1 and f.kind in ("start", "discharge"):
                g = _residual_graph(net, f.flow)
                dist = nx.single_source_shortest_path_length(g.reverse(), net.t)               # Entfernung zu T im Restgraphen
                for v in range(net.n):
                    if v in dist and v not in (net.s, net.t):
                        assert f.heights[v] == dist[v]
                checked += 1
    assert checked > 30


def test_gap_events_leave_no_node_between_the_gap_and_n():
    seen = 0
    for net in _nets(40):
        res = pr.push_relabel(net, "fifo", True, False)
        for f in res.frames:
            if f.gap:
                seen += 1
                below = {x for k, x in enumerate(f.heights) if k != net.s and x < net.n}
                gap = min(k for k in range(1, net.n) if k not in below)
                assert not any(gap < x < net.n for k, x in enumerate(f.heights) if k != net.s)
    assert seen > 10


# --- alle neun Konfigurationen, Heuristiken ------------------------------------------------------------------------------------------------------

def test_all_nine_configurations_agree_on_value_and_cut():
    for net in _nets(30):
        results = [_run(net, cfg, trace=False) for cfg in CONFIGS]
        assert len({r.value for r in results}) == 1 and len({r.s_side for r in results}) == 1


def test_heuristics_reduce_the_effort_somewhere_and_never_the_value():
    for sel in pr.SELECTIONS:
        fewer_relabels = fewer_scans = 0
        for net in _nets(40):
            none, both = pr.push_relabel(net, sel, False, False, keep_trace=False), pr.push_relabel(net, sel, True, True, keep_trace=False)
            assert none.value == both.value
            fewer_relabels += both.relabels < none.relabels
            fewer_scans += both.scanned < none.scanned
        assert fewer_relabels > 25 and fewer_scans > 25                             # Negativkontrolle: ohne Heuristiken wird es wirklich teurer


def test_keep_trace_false_changes_nothing_else():
    for net in _nets(10):
        a, b = pr.push_relabel(net), pr.push_relabel(net, keep_trace=False)
        assert (a.value, a.flow, a.pushes, a.relabels, a.scanned, a.s_side) == (b.value, b.flow, b.pushes, b.relabels, b.scanned, b.s_side) and b.frames == ()


def test_relabels_stay_below_the_two_n_squared_bound_and_heights_below_two_n():
    for net in _nets(60):
        for cfg in CONFIGS:
            res = _run(net, cfg, trace=False)
            assert res.relabels <= 2 * net.n ** 2 and res.max_height <= 2 * net.n - 1


def test_a_net_with_no_path_returns_the_whole_excess():
    net = sc.generate(2, 6, 3, 20, 50, 90, 8)
    res = pr.push_relabel(net)
    assert res.value == 0 and res.cut_capacity == 0 and res.by_phase[1][0] > 0
    assert all(f == 0 for f in res.flow)
