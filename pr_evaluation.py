"""Kennzahlen, Urteil und die Experimente der Demo (Verteilungen über feste Netze, Heuristiken, Phase 2, Skalierung, Schranken, Schnitt gegen Edmonds-Karp).
Alles ganzzahlig gerechnet; Prozente entstehen erst bei der Ausgabe."""

from dataclasses import dataclass
from functools import lru_cache
from statistics import mean, median

import numpy as np

import pr_algorithm as pr
import pr_constants as C
import pr_dinic as dn
import pr_edmonds_karp as ek
import pr_scenario as sc

K_SUPPLY, K_LANE_IN, K_THROUGHPUT, K_LANE_OUT, K_DEMAND = sc.K_SUPPLY, sc.K_LANE_IN, sc.K_THROUGHPUT, sc.K_LANE_OUT, sc.K_DEMAND
STAGE_KINDS = (K_SUPPLY, K_LANE_IN, K_THROUGHPUT, K_LANE_OUT)
CONFIGS = tuple((sel, heur) for sel in pr.SELECTIONS for heur in C.HEURISTICS_LABELS)


@dataclass(frozen=True)
class Analysis:
    net: sc.Net
    result: pr.Result
    dinic: dn.Result
    edmonds_karp: ek.Result
    demand: int          # Gesamtnachfrage (nur beim Distributionsnetz, sonst 0)
    stage_caps: dict     # Art -> Kapazität der Schnitt-Kanten dieser Art (größte S-Seite, wie sie Push-Relabel findet)
    selection: str
    heuristics: str


def _demand(net):
    return sum(c for _, _, c, _, kind in net.arcs if kind == K_DEMAND)


def _stage_caps(net, cut_arcs):
    caps = {}
    for i in cut_arcs:
        kind = net.arcs[i][4]
        caps[kind] = caps.get(kind, 0) + net.arcs[i][2]
    return caps


def run(net, selection, heuristics, keep_trace=True):
    gap, glob = C.HEURISTICS_FLAGS[heuristics]
    return pr.push_relabel(net, selection, gap, glob, keep_trace=keep_trace)


def analyse(net, selection=C.DEFAULT_SELECTION, heuristics=C.DEFAULT_HEURISTICS):
    res = run(net, selection, heuristics)
    return Analysis(net, res, dn.dinic(net, keep_flows=False), ek.max_flow(net, "bfs", keep_flows=False), _demand(net) if net.logistic else 0, _stage_caps(net, res.cut_arcs), selection, heuristics)


def pct(numerator, denominator, digits=1):
    return round(100 * numerator / denominator, digits) if denominator else 0.0


def phase_ops(res, phase):
    d, p, r, s = res.by_phase[phase - 1]
    return p + r


def verdict(a):
    """(Stufe, Code, Daten): 'delivered' = alle Nachfrage gedeckt, 'bottleneck' = das Netz schafft weniger, 'disconnected' = gar nichts kommt an, 'teaching' = Lehrnetz."""
    res, net = a.result, a.net
    (d1, p1, r1, s1), (d2, p2, r2, s2) = res.by_phase
    data = {
        "value": res.value, "demand": a.demand, "share": pct(res.value, a.demand) if a.demand else None,
        "discharges": res.discharges, "discharges1": d1, "discharges2": d2, "pushes": res.pushes, "pushes_sat": res.pushes_sat, "relabels": res.relabels, "gaps": res.gaps, "globals": res.globals_,
        "scanned": res.scanned, "scanned1": s1, "scanned2": s2, "ops1": p1 + r1, "ops2": p2 + r2, "dinic_scanned": a.dinic.scanned_total, "ek_scanned": a.edmonds_karp.scanned_total,
        "cut_capacity": res.cut_capacity, "cut_arcs": len(res.cut_arcs), "stage_caps": a.stage_caps, "s_side": sum(res.s_side), "max_height": res.max_height,
        "same_cut": tuple(res.s_side) == tuple(a.edmonds_karp.reach), "ek_side": sum(a.edmonds_karp.reach),
    }
    if not net.logistic:
        return "info", "teaching", data
    if res.value == 0:
        return "warning", "disconnected", data
    if res.value == a.demand:
        return "success", "delivered", data
    net_caps = {k: v for k, v in a.stage_caps.items() if k in STAGE_KINDS}
    data["dominant"] = max(net_caps, key=net_caps.get) if net_caps else None
    return "warning", "bottleneck", data


def _generate(p, d, s, density, spread, load, seed):
    return sc.generate(p, d, s, density, spread, load, seed)


@lru_cache(maxsize=128)
def _runs(p, d, s, density, spread, load, seeds=C.DIST_SEEDS):
    """Je Netz alle neun Konfigurationen, Dinic und Edmonds-Karp (ohne Trace); von den Verteilungen gemeinsam genutzt."""
    out = []
    for seed in seeds:
        net = _generate(p, d, s, density, spread, load, seed)
        out.append((net, _demand(net), {cfg: run(net, cfg[0], cfg[1], keep_trace=False) for cfg in CONFIGS}, dn.dinic(net, keep_flows=False), ek.max_flow(net, "bfs", keep_flows=False)))
    return out


@lru_cache(maxsize=256)
def distribution(p, d, s, density, spread, load, selection=C.DEFAULT_SELECTION, heuristics=C.DEFAULT_HEURISTICS, seeds=C.DIST_SEEDS):
    """Über feste Netze für EINE Konfiguration: Entladungen, Pushes, Relabels, durchsuchte Kanten (gegen Dinic und Edmonds-Karp), Phase 2, Schnitt, Schranken."""
    keys = ("discharges", "pushes", "relabels", "scanned", "dinic", "ek", "ops2", "scanned2", "gaps", "globals")
    cols = {k: [] for k in keys}
    ratios_rel, ratios_h, ratios_push, same_cut, extra_nodes, served, all_served, no_phase2 = [], [], [], [], [], [], 0, 0
    for net, demand, results, dr, er in _runs(p, d, s, density, spread, load, seeds):
        r = results[(selection, heuristics)]
        vals = (r.discharges, r.pushes, r.relabels, r.scanned, dr.scanned_total, er.scanned_total, phase_ops(r, 2), r.by_phase[1][3], r.gaps, r.globals_)
        for k, v in zip(keys, vals):
            cols[k].append(v)
        ratios_rel.append(r.relabels / (2 * net.n ** 2))
        ratios_h.append(r.max_height / (2 * net.n - 1))
        ratios_push.append(r.pushes / (net.n ** 2 * net.m))
        eq = tuple(r.s_side) == tuple(er.reach)
        same_cut.append(eq)
        if not eq:
            extra_nodes.append(sum(r.s_side) - sum(er.reach))
        served.append(pct(r.value, demand))
        all_served += r.value == demand
        no_phase2 += phase_ops(r, 2) == 0
    n = len(seeds)
    out = {"n_seeds": n, "cols": cols, "share_same_cut": sum(same_cut) / n, "extra_nodes": extra_nodes, "extra_nodes_mean": mean(extra_nodes) if extra_nodes else 0.0,
           "extra_nodes_max": max(extra_nodes, default=0), "relabel_ratio_mean": mean(ratios_rel), "relabel_ratio_max": max(ratios_rel), "height_ratio_max": max(ratios_h),
           "push_ratio_mean": mean(ratios_push), "push_ratio_max": max(ratios_push), "served_mean": mean(served), "share_all_served": all_served / n, "share_no_phase2": no_phase2 / n,
           "edges_mean": mean(net.m for net, *_ in _runs(p, d, s, density, spread, load, seeds)), "nodes_mean": mean(net.n for net, *_ in _runs(p, d, s, density, spread, load, seeds)),
           "share_le_dinic": sum(1 for a, b in zip(cols["scanned"], cols["dinic"]) if a <= b) / n, "share_le_ek": sum(1 for a, b in zip(cols["scanned"], cols["ek"]) if a <= b) / n}
    for k in keys:
        out[k + "_mean"], out[k + "_median"], out[k + "_max"] = mean(cols[k]), median(cols[k]), max(cols[k])
    return out


def config_table(p, d, s, density, spread, load):
    """Alle neun Kombinationen aus Knotenwahl und Heuristiken (Mittel und Median über die festen Netze)."""
    return [dict(selection=sel, heuristics=heur, **{k: v for k, v in distribution(p, d, s, density, spread, load, sel, heur).items() if k != "cols" and k != "extra_nodes"}) for sel, heur in CONFIGS]


@lru_cache(maxsize=32)
def phase2_sweep(p, d, s, density, spread, loads=C.LOAD_SWEEP, seeds=C.SWEEP_SEEDS):
    """Je Auslastung: Anteil von Phase 2 an Operationen und durchsuchten Kanten (Warteschlange, Gap + Global Relabeling), Anteil der Netze ganz ohne Phase-2-Arbeit, gelieferter Anteil."""
    rows = []
    for load in loads:
        ops1 = ops2 = sc1 = sc2 = no2 = 0
        served = []
        for seed in seeds:
            net = _generate(p, d, s, density, spread, load, seed)
            r = run(net, C.DEFAULT_SELECTION, C.DEFAULT_HEURISTICS, keep_trace=False)
            ops1 += phase_ops(r, 1)
            ops2 += phase_ops(r, 2)
            sc1 += r.by_phase[0][3]
            sc2 += r.by_phase[1][3]
            no2 += phase_ops(r, 2) == 0
            served.append(pct(r.value, _demand(net)))
        rows.append({"load": load, "ops_share2": ops2 / (ops1 + ops2), "scan_share2": sc2 / (sc1 + sc2), "share_no_phase2": no2 / len(seeds), "served_mean": mean(served)})
    return rows


@lru_cache(maxsize=32)
def scaling(sizes=C.SCALE_SIZES, seeds=C.SCALE_SEEDS, density=C.DEFAULT_DENSITY):
    """Durchsuchte Kanten gegen die Netzgröße: Push-Relabel (Warteschlange mit beiden Heuristiken, Highest-Label, ohne Heuristiken), Dinic, Edmonds-Karp."""
    rows = []
    for (p, d, s) in sizes:
        cols = {k: [] for k in ("pr", "pr_hl", "pr_none", "dinic", "ek", "relabels", "pushes", "n", "m")}
        for seed in seeds:
            net = _generate(p, d, s, density, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, seed)
            a = run(net, "fifo", "both", keep_trace=False)
            for k, v in (("pr", a.scanned), ("pr_hl", run(net, "highest", "both", keep_trace=False).scanned), ("pr_none", run(net, "fifo", "none", keep_trace=False).scanned),
                         ("dinic", dn.dinic(net, keep_flows=False).scanned_total), ("ek", ek.max_flow(net, "bfs", keep_flows=False).scanned_total),
                         ("relabels", a.relabels), ("pushes", a.pushes), ("n", net.n), ("m", net.m)):
                cols[k].append(v)
        rows.append({"size": (p, d, s), **{k: mean(v) for k, v in cols.items()}})
    return rows


def slopes(rows):
    """Steigung im doppelt logarithmischen Diagramm (durchsuchte Kanten gegen Kantenzahl)."""
    x = np.log([r["m"] for r in rows])
    return {k: float(np.polyfit(x, np.log([r[k] for r in rows]), 1)[0]) for k in ("pr", "pr_hl", "pr_none", "dinic", "ek")}
