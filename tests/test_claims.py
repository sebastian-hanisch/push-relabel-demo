"""Jede Zahl in den Hilfetexten, in der App und im README ist hier belegt: die Lehrnetze von Hand, die Beispielnetze über ihre Seeds, die Verteilungen über die 100 festen Netze (DIST_SEEDS).
Alles ist ganzzahlig gerechnet (eigener Zufallsgenerator), die Zahlen sind auf Windows und Linux dieselben."""

import pytest

import pr_constants as C
import pr_evaluation as ev
import pr_scenario as sc

S = (C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)


def near(value, expected, tol):
    assert abs(value - expected) <= tol, (value, expected)


def _preset(name):
    p = C.PRESETS[name]
    net = sc.build(p["net"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"], p["seed"])
    return net, ev.analyse(net, p["selection"], p["heuristics"])


def _shape(r):
    """(Entladungen Phase 1, Phase 2, Pushes, Relabels, durchsuchte Kanten)."""
    return r.by_phase[0][0], r.by_phase[1][0], r.pushes, r.relabels, r.scanned


# --- Presets (PRESET_HELP) ------------------------------------------------------------------------------------------------------------------------

def test_default_net_preset():
    net, a = _preset("🚚 Zufallsnetz")
    r = a.result
    assert (r.value, a.demand) == (80, 83)                                                      # "80 von 83 Einheiten"
    assert _shape(r) == (37, 8, 67, 13, 281)                                                    # "45 Entladungen (37 ... 8), 67 Pushes, 13 Relabels, 281 durchsuchte Kanten"
    assert (a.dinic.scanned_total, a.edmonds_karp.scanned_total) == (220, 621)                  # "Dinic 220, Edmonds-Karp 621"
    assert sum(r.s_side) == 17 == sum(a.edmonds_karp.reach) and tuple(r.s_side) == tuple(a.edmonds_karp.reach)    # "Seite von S ... 17 Knoten, dieselben wie bei Edmonds-Karp"
    assert r.gaps == 1 and r.globals_ == 2


def test_highest_label_and_generic_presets():
    _, hl = _preset("🏔️ Highest-Label")
    _, gen = _preset("🎲 Beliebiger Knoten")
    _, base = _preset("🚚 Zufallsnetz")
    assert _shape(hl.result) == (47, 4, 72, 16, 309)                                            # "47 + 4 Entladungen, 72 Pushes, 16 Relabels, 309"
    assert _shape(gen.result) == (42, 11, 74, 15, 307)                                          # "42 + 11 Entladungen, 74 Pushes, 15 Relabels, 307"
    assert hl.result.value == gen.result.value == base.result.value and hl.result.s_side == gen.result.s_side == base.result.s_side


def test_no_heuristics_preset():
    net, a = _preset("🐢 Ohne Heuristiken")
    r = a.result
    assert r.relabels == 217 and r.discharges == 243 and r.scanned == 1810 and r.gaps == 0 and r.globals_ == 0     # "217 statt 13 Relabels, 243 statt 45 Entladungen und 1810 statt 281"
    assert 2.8 < r.scanned / a.edmonds_karp.scanned_total < 3.0                                  # "fast das Dreifache von Edmonds-Karp (621)"


def test_gap_only_preset():
    net, a = _preset("🕳️ Nur Gap")
    r = a.result
    assert (r.relabels, r.scanned, r.gaps, r.globals_) == (62, 535, 1, 0)                        # "62 Relabels und 535 durchsuchte Kanten", "ein einziges Gap-Ereignis"


def test_much_return_preset():
    net, a = _preset("↩️ Viel Rückgabe")
    r = a.result
    assert (r.value, a.demand) == (28, 28)                                                       # "die gesamte Nachfrage (28)"
    assert (r.by_phase[0][0], r.by_phase[1][0], r.scanned, r.by_phase[1][3]) == (29, 18, 322, 102) and round(100 * 102 / 322) == 32    # "18 der 47 Entladungen und 102 der 322 durchsuchten Kanten (32 %)"


def test_staircase_preset():
    net, a = _preset("🪜 Treppe")
    r = a.result
    assert (net.n - 2) // 2 == 20 and (r.discharges, r.pushes, r.relabels, r.scanned) == (65, 70, 15, 325)     # "20 Fahrzeuge ... 65 Entladungen, 70 Pushes, 15 Relabels, 325"
    assert (a.dinic.scanned_total, a.edmonds_karp.scanned_total) == (928, 1345)                  # "Dinic 928, Edmonds-Karp 1345"
    assert (sum(r.s_side), sum(a.edmonds_karp.reach)) == (41, 1)                                 # "41 Knoten ... statt 1 bei Edmonds-Karp"


def test_assignment_preset():
    net, a = _preset("💑 Zuordnung als Fluss")
    r = a.result
    assert (r.discharges, r.pushes, r.relabels, r.scanned) == (35, 36, 12, 185)                  # "35 Entladungen, 36 Pushes, 12 Relabels, 185"
    assert (a.dinic.scanned_total, a.edmonds_karp.scanned_total) == (69, 100)                    # "Dinic ... 69, Edmonds-Karp 100"


# --- Konfigurationen bei den Standardeinstellungen (100 feste Netze) -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def table():
    return {(r["selection"], r["heuristics"]): r for r in ev.config_table(*S)}


@pytest.fixture(scope="module")
def dist():
    return ev.distribution(*S)


def test_heuristics_and_selection(table, dist):
    fifo = [table[("fifo", h)] for h in ("none", "gap", "both")]
    assert [round(r["scanned_mean"]) for r in fifo] == [1179, 408, 312]                        # Sidebar: "1179 ..., mit Gap 408, mit Gap und Global Relabeling 312"
    assert [round(table[(sel, "both")]["scanned_mean"]) for sel in ("fifo", "highest", "generic")] == [312, 319, 322]   # Sidebar Knotenwahl
    assert table[("highest", "none")]["scanned_mean"] < table[("generic", "none")]["scanned_mean"] < table[("fifo", "none")]["scanned_mean"]   # ohne Heuristiken ist der höchste Knoten am besten
    near(fifo[0]["scanned_mean"] / fifo[1]["scanned_mean"], 2.9, 0.05)                          # "Gap spart den Faktor 2,9"
    near(fifo[1]["scanned_mean"] / fifo[2]["scanned_mean"], 1.3, 0.05)                          # "Global Relabeling noch 1,3"
    near(fifo[1]["relabels_mean"], 47.5, 0.05), near(fifo[2]["relabels_mean"], 15.5, 0.05)      # "Relabels von 47,5 auf 15,5"
    assert fifo[0]["scanned_mean"] > dist["ek_mean"]                                            # "Ohne Heuristiken teurer als Edmonds-Karp"
    assert fifo[0]["scanned_median"] == 1332 and fifo[0]["scanned_mean"] / dist["ek_mean"] > 2   # README: "Median 1332", "mehr als doppelt so teuer wie Edmonds-Karp"
    near(fifo[0]["relabels_mean"], 135.7, 0.05)                                                 # "135,7 Relabels"
    assert [round(table[(sel, "none")]["scanned_mean"]) for sel in ("highest", "generic", "fifo")] == [1074, 1130, 1179]   # README: "1074 gegen 1130 und 1179"


def test_against_dinic_and_edmonds_karp(dist):
    near(dist["dinic_mean"], 253.67, 0.01)                                                       # Sidebar: "Dinic braucht 254, Edmonds-Karp 525"
    near(dist["ek_mean"], 524.75, 0.01)
    near(dist["scanned_mean"] / dist["dinic_mean"], 1.23, 0.01)                                  # Grenzen: "etwa ein Viertel mehr Kanten als Dinic"
    assert dist["share_le_dinic"] == 0.2 and dist["share_le_ek"] == 0.97                        # "nur in jedem fünften Netz gleich gut"; gegen Edmonds-Karp 97 %


def test_bounds_against_reality(dist):
    near(100 * dist["relabel_ratio_mean"], 2.1, 0.05)                                            # Kennzahl "Relabels ÷ 2n²": 2,1 %, höchstens 3,2 %
    near(100 * dist["relabel_ratio_max"], 3.2, 0.05)
    near(100 * dist["height_ratio_max"], 67.6, 0.2)                                              # "Höchste Höhe ÷ (2n − 1)" 68 %
    near(100 * dist["push_ratio_mean"], 0.5, 0.05)                                               # "Pushes ÷ n²·m" 0,5 %, höchstens 0,7 %
    near(100 * dist["push_ratio_max"], 0.7, 0.05)


def test_the_other_cut(dist):
    assert dist["share_same_cut"] == 0.8                                                          # "in 80 % der Netze"
    near(dist["extra_nodes_mean"], 3.35, 0.005)
    assert min(dist["extra_nodes"]) == 1 and dist["extra_nodes_max"] == 16                        # "um einen bis 16 Knoten größer"
    assert dist["share_all_served"] == 0.2


def test_phase2_share_by_load():
    rows = {r["load"]: r for r in ev.phase2_sweep(*S[:5])}
    near(100 * rows[40]["ops_share2"], 19.1, 0.1)                                                # Sidebar: "bei 40 % 19 % der Operationen, bei 160 % nur noch 3 %"
    near(100 * rows[160]["ops_share2"], 3.4, 0.1)
    assert round(100 * rows[40]["ops_share2"]) == 19 and round(100 * rows[160]["ops_share2"]) == 3
    assert all(0.23 <= r["scan_share2"] <= 0.274 for r in rows.values())                          # "Anteil der durchsuchten Kanten bleibt etwa gleich"
    assert all(rows[l]["share_no_phase2"] == 0 for l in (40, 60, 80, 90, 100)) and rows[120]["share_no_phase2"] == 0.2 and rows[160]["share_no_phase2"] == 0.25   # "Ab 120 % Netze ohne Phase-2-Arbeit"
    ops = [rows[l]["ops_share2"] for l in C.LOAD_SWEEP]
    assert ops[:-1] == sorted(ops[:-1], reverse=True) and ops[0] > 5 * ops[-1]                   # der Anteil der Operationen sinkt mit der Auslastung (bis 140 % streng, danach etwa gleich)


def test_scaling_and_dense_net():
    rows = ev.scaling()
    slopes = ev.slopes(rows)
    near(slopes["pr"], 1.00, 0.03)                                                               # README: Push-Relabel 1,00, Highest-Label 1,12, ohne Heuristiken 1,76, Dinic 0,94, Edmonds-Karp 1,74
    near(slopes["pr_hl"], 1.12, 0.03)
    near(slopes["pr_none"], 1.76, 0.03)
    near(slopes["dinic"], 0.94, 0.03)
    near(slopes["ek"], 1.74, 0.03)
    assert [round(r["pr"] / r["dinic"], 2) for r in rows] == [1.36, 1.15, 1.21, 1.68, 1.64, 1.45]  # Tabelle "Push-Relabel ÷ Dinic"
    assert rows[0]["pr_hl"] < rows[0]["pr"] and all(r["pr_hl"] > r["pr"] for r in rows[1:])      # "Highest-Label nur beim kleinsten Netz besser"
    assert rows[0]["pr"] > rows[0]["ek"] and all(r["pr"] < r["ek"] for r in rows[1:]) and rows[-1]["ek"] / rows[-1]["pr"] > 20     # gegen Edmonds-Karp erst ab 19 Knoten besser, bei 166 Knoten mehr als 20-fach
    last = rows[-1]
    assert (round(last["pr"]), round(last["dinic"]), round(last["ek"]), round(last["pr_hl"]), round(last["pr_none"])) == (8964, 6189, 208698, 14674, 471487)   # README: 166 Knoten
    near(last["ek"] / last["pr"], 23.3, 0.05), near(last["pr"] / last["dinic"], 1.45, 0.005)
    dense = ev.scaling(sizes=(C.DENSE_SETTINGS[:3],), density=C.DENSE_SETTINGS[3])[0]
    assert round(dense["m"]) == 1832 and dense["pr"] > dense["dinic"] and dense["pr"] < dense["ek"]      # "Netzdichte 100 %: Push-Relabel ..., Dinic ..., Edmonds-Karp ..."
    near(dense["pr"] / dense["dinic"], 1.23, 0.01)
