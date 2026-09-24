"""Szenario (Aufbau, Reproduzierbarkeit, Stufen), Auswertung (Urteil, Verteilungen, Konfigurationen, Experimente)."""

import pytest

import pr_algorithm as pr
import pr_constants as C
import pr_dinic as dn
import pr_edmonds_karp as ek
import pr_evaluation as ev
import pr_scenario as sc

DEFAULT = (C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)


def _net(seed=C.DEFAULT_SEED, *settings):
    return sc.generate(*(settings or DEFAULT), seed)


def test_generation_is_reproducible_and_seed_dependent():
    assert _net(5) == _net(5) and _net(5) != _net(6)


def test_structure_of_a_distribution_net():
    p, d, s = 3, 3, 8
    net = _net()
    assert net.n == 2 + p + 2 * d + s and net.s == 0 and net.t == 1 and net.logistic
    kinds = [a[4] for a in net.arcs]
    assert kinds.count(sc.K_SUPPLY) == p and kinds.count(sc.K_THROUGHPUT) == d and kinds.count(sc.K_DEMAND) == s
    assert all(a[2] >= 1 for a in net.arcs)
    for u, v, _, _, kind in net.arcs:
        assert net.pos[u][1] > net.pos[v][1]


@pytest.mark.parametrize("seed", range(20))
def test_every_plant_and_store_has_a_lane_even_on_the_thinnest_net(seed):
    net = _net(seed, 3, 3, 8, C.DENSITY_MIN, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)
    assert {a[1] for a in net.arcs if a[4] == sc.K_SUPPLY} <= {a[0] for a in net.arcs if a[4] == sc.K_LANE_IN}
    assert {a[0] for a in net.arcs if a[4] == sc.K_DEMAND} <= {a[1] for a in net.arcs if a[4] == sc.K_LANE_OUT}


def test_a_thinner_net_only_removes_lanes_and_keeps_all_other_values():
    for seed in range(20):
        thin, full = _net(seed, 3, 3, 8, 40, 50, 90), _net(seed, 3, 3, 8, 100, 50, 90)
        assert set(thin.arcs) <= set(full.arcs) and len(thin.arcs) < len(full.arcs)


def test_teaching_nets_and_build_ignore_the_random_settings():
    assert not sc.assignment(4).logistic and sc.build("assignment", 6, 6, 12, 100, 100, 160, 1) == sc.assignment(4)
    assert sc.build("random", *DEFAULT, 9) == _net(9)
    assert sc.build("stair", 6, 6, 12, 100, 100, 160, 1) == sc.staircase(5)


def test_verdict_codes():
    lvl, code, d = ev.verdict(ev.analyse(_net(1, 3, 3, 8, 100, 50, 40)))
    assert (lvl, code) == ("success", "delivered") and d["value"] == d["demand"]
    lvl, code, d = ev.verdict(ev.analyse(_net(1, 3, 3, 8, 60, 50, 160)))
    assert (lvl, code) == ("warning", "bottleneck") and d["value"] < d["demand"] and d["dominant"] in ev.STAGE_KINDS
    assert ev.verdict(ev.analyse(sc.assignment(4)))[:2] == ("info", "teaching")
    lvl, code, d = ev.verdict(ev.analyse(sc.generate(2, 6, 3, 20, 50, 90, 8)))
    assert (lvl, code) == ("warning", "disconnected") and d["value"] == 0


def test_verdict_data_is_consistent():
    a = ev.analyse(_net())
    _, _, d = ev.verdict(a)
    assert d["discharges"] == d["discharges1"] + d["discharges2"] == len(a.result.frames) - 2
    assert d["scanned"] == d["scanned1"] + d["scanned2"] and d["ops1"] + d["ops2"] == d["pushes"] + d["relabels"]
    assert d["dinic_scanned"] == dn.dinic(a.net, keep_flows=False).scanned_total and d["ek_scanned"] == ek.max_flow(a.net, "bfs", keep_flows=False).scanned_total


def test_stage_capacities_add_up_to_the_cut():
    for seed in range(30):
        a = ev.analyse(_net(seed))
        assert sum(a.stage_caps.values()) == a.result.cut_capacity == a.result.value


def test_distribution_is_consistent_with_single_runs():
    dist = ev.distribution(*DEFAULT, seeds=tuple(range(5)))
    runs = [ev.run(sc.generate(*DEFAULT, seed), C.DEFAULT_SELECTION, C.DEFAULT_HEURISTICS, keep_trace=False) for seed in range(5)]
    assert dist["cols"]["scanned"] == [r.scanned for r in runs] and dist["cols"]["pushes"] == [r.pushes for r in runs]
    assert dist["cols"]["dinic"] == [dn.dinic(sc.generate(*DEFAULT, seed), keep_flows=False).scanned_total for seed in range(5)]
    assert dist["n_seeds"] == 5 and 0 <= dist["share_all_served"] <= 1 and dist["relabel_ratio_max"] <= 1


def test_config_table_covers_all_nine_configurations():
    rows = ev.config_table(*DEFAULT)
    assert [(r["selection"], r["heuristics"]) for r in rows] == list(ev.CONFIGS) and len(rows) == 9
    assert all(r["scanned_mean"] > 0 for r in rows)


def test_phase2_sweep_and_scaling_rows():
    rows = ev.phase2_sweep(*DEFAULT[:5])
    assert [r["load"] for r in rows] == list(C.LOAD_SWEEP) and all(0 < r["ops_share2"] < 1 and 0 < r["scan_share2"] < 1 for r in rows)
    sc_rows = ev.scaling()
    assert [r["size"] for r in sc_rows] == list(C.SCALE_SIZES) and all(r["pr"] > 0 and r["pr_none"] > r["pr"] for r in sc_rows)
    assert all(0.5 < s < 2.5 for s in ev.slopes(sc_rows).values())
