"""Plotly-Abbildungen: Netz mit Überschüssen und Höhen, Höhenschema, Fluss mit Schnitt (Beweis), Phasen, Verteilungen, Heuristiken, Aufwand.
Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen. Kanten haben über unsichtbare Marker einen Hover-Text
(Plotly-Linien reagieren nur an ihren Stützpunkten)."""

from math import atan2, degrees, hypot

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import pr_constants as C


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.08), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _layout(fig, net, height):
    xs = [p[0] for p in net.pos]
    ys = [p[1] for p in net.pos]
    pad = 9
    fig.update_xaxes(visible=False, range=[min(xs) - pad, max(xs) + pad], scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False, range=[min(ys) - pad, max(ys) + pad])
    return _base(fig, height)


def _curve(p0, p1, bulge, steps=8):
    """Punkte von p0 nach p1; mit `bulge` > 0 als flacher Bogen nach rechts (so trennen sich Vorwärts- und Rückkante). Dazu der Pfeilwinkel bei 65 %."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length = hypot(dx, dy) or 1.0
    cx, cy = (x0 + x1) / 2 + bulge * length * dy / length, (y0 + y1) / 2 - bulge * length * dx / length
    ts = [k / steps for k in range(steps + 1)]
    xs = [(1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1 for t in ts]
    ys = [(1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1 for t in ts]
    t = 0.65
    tx = 2 * (1 - t) * (cx - x0) + 2 * t * (x1 - cx)
    ty = 2 * (1 - t) * (cy - y0) + 2 * t * (y1 - cy)
    ax = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1
    ay = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1
    return xs, ys, (ax, ay, degrees(atan2(tx, ty))), (xs[steps // 2], ys[steps // 2])


def _segments(curves):
    x, y = [], []
    for xs, ys, _, _ in curves:
        x += xs + [None]
        y += ys + [None]
    return x, y


def _lines(fig, curves, color, width, name, dash=None, showlegend=True):
    if not curves:
        return
    x, y = _segments(curves)
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=width, dash=dash), hoverinfo="skip", name=name, showlegend=showlegend))


def _arrows(fig, curves, color, size=9):
    if not curves:
        return
    fig.add_trace(go.Scatter(x=[c[2][0] for c in curves], y=[c[2][1] for c in curves], mode="markers", hoverinfo="skip", showlegend=False,
                             marker=dict(symbol="arrow", size=size, color=color, angle=[c[2][2] for c in curves])))


def _hover_points(fig, net, entries):
    """Unsichtbare Marker entlang jeder Kante, damit der Hover-Text überall auf der Kante erscheint. entries: [(Kurve, Text)]"""
    x, y, text = [], [], []
    for curve, label in entries:
        xs, ys = curve[0], curve[1]
        for k in range(1, len(xs) - 1):
            x.append(xs[k]); y.append(ys[k]); text.append(label)
    if x:
        fig.add_trace(go.Scatter(x=x, y=y, mode="markers", marker=dict(size=9, opacity=0), hovertext=text, hoverinfo="text", showlegend=False))


def _labels(fig, points):
    """points: [(x, y, Text)] - als Annotationen mit heller Hinterlegung, damit sie Kanten, Pfeile und Knotenbeschriftungen nicht unlesbar machen."""
    for x, y, text in points:
        fig.add_annotation(x=x, y=y, text=text, showarrow=False, xanchor="left", font=dict(size=11, color="#111"), bgcolor="rgba(255,255,255,0.88)", borderpad=1)


def _arc_name(net, i):
    u, v = net.arcs[i][0], net.arcs[i][1]
    return f"{net.names[u]} → {net.names[v]}"


def _nodes(fig, net, reach=None):
    """Knoten: S und T als Quadrate, alle anderen als Kreise; mit `reach` grün (von S erreichbar) oder grau eingefärbt."""
    text_pos = {0: "top center", 1: "bottom center"}
    for kind, idx in (("Quelle/Senke", [net.s, net.t]), ("Knoten", [v for v in range(net.n) if v not in (net.s, net.t)])):
        colors = [C.COLORS["node"] if reach is None else (C.COLORS["reach"] if reach[v] else C.COLORS["unreach"]) for v in idx]
        pos = [text_pos.get(v, "top center" if net.pos[v][1] > 70 else ("bottom center" if net.pos[v][1] < 30 else "middle left")) for v in idx]
        if net.logistic and kind == "Knoten":
            pos = ["top center" if net.names[v].startswith("Werk") else "bottom center" if net.names[v].startswith("Filiale") else "middle left" for v in idx]
        fig.add_trace(go.Scatter(
            x=[net.pos[v][0] for v in idx], y=[net.pos[v][1] for v in idx], mode="markers+text", showlegend=False,
            text=[net.labels[v] for v in idx], textposition=pos, hovertext=[net.names[v] for v in idx], hoverinfo="text",
            marker=dict(symbol="square" if kind == "Quelle/Senke" else "circle", size=13 if kind == "Quelle/Senke" else 10, color=colors, line=dict(width=1.5, color="#333"))))


def _wscale(net):
    return max(c for _, _, c, _, _ in net.arcs)


def _width(amount, top, lo=1.0, hi=6.0):
    return lo + (hi - lo) * amount / top if top else lo


def build_flow(net, flow, path=None, cut=None, reach=None, height=460):
    """Fluss je Kante: Breite ~ Fluss, dunkelblau = voll ausgelastet, blass = ungenutzt. `path`: Kanten (Netzkanten-Indizes) der letzten Augmentierung
    (grün beschriftet mit Fluss/Kapazität); `cut`: Schnittkanten in Rot mit Kapazität; `reach`: von S erreichbare Knoten in Grün."""
    fig = go.Figure()
    top = _wscale(net)
    cut_set, path_set = set(cut or ()), set(path or ())
    groups = {"idle": [], "part": [], "full": []}
    hover, labels = [], []
    special = {"cut": [], "path": []}
    for i, (u, v, cap, cost, _) in enumerate(net.arcs):
        curve = _curve(net.pos[u], net.pos[v], 0.0)
        hover.append((curve, f"{_arc_name(net, i)}: Fluss {flow[i]} von {cap}, Kosten {cost} je Einheit"))
        if i in cut_set:
            special["cut"].append(curve)
            labels.append((curve[0][3] + 1.5, curve[1][3], f"{cap}"))
        elif i in path_set:
            special["path"].append(curve)
            labels.append((curve[0][3] + 1.5, curve[1][3], f"{flow[i]}/{cap}"))
        else:
            groups["idle" if flow[i] == 0 else "full" if flow[i] == cap else "part"].append((curve, flow[i]))
    _lines(fig, [c for c, _ in groups["idle"]], C.COLORS["faint"], 1.2, "ungenutzt")
    for group, color in (("part", "rgba(31,119,180,0.85)"), ("full", "#0b3d91")):
        by_width = {}
        for c, f in groups[group]:
            by_width.setdefault(round(_width(f, top)), []).append(c)      # ganze Breiten: wenige Spuren statt einer je Kante
        for w, curves in by_width.items():
            _lines(fig, curves, color, w, group, showlegend=False)
    if groups["part"]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="rgba(31,119,180,0.85)", width=4), name="Fluss (nicht voll)"))
    if groups["full"]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="#0b3d91", width=4), name="Fluss (Kante voll)"))
    _lines(fig, special["path"], C.COLORS["path"], 5, "Kante des letzten Weges")
    _lines(fig, special["cut"], C.COLORS["cut"], 5, "Schnittkante (voll, Kapazität beschriftet)")
    if net.m <= 60:
        _arrows(fig, [c for c, _ in groups["idle"]] + [c for c, _ in groups["part"]] + [c for c, _ in groups["full"]], "rgba(60,60,60,0.7)", 8)
    _arrows(fig, special["path"] + special["cut"], "rgba(30,30,30,0.9)", 11)
    _hover_points(fig, net, hover)
    _labels(fig, labels)
    _nodes(fig, net, reach)
    return _layout(fig, net, height)


def _node_text_positions(net, idx):
    if net.logistic:
        return ["top center" if (v == 0 or net.names[v].startswith("Werk")) else "bottom center" if (v == 1 or net.names[v].startswith("Filiale")) else "middle left" for v in idx]
    return ["top center" if net.pos[v][1] > 60 else "bottom center" for v in idx]


def _colorbar(top):
    return dict(title=dict(text="Höhe", side="top"), orientation="h", thickness=9, len=0.6, x=0.5, xanchor="center", y=-0.02, yanchor="top", tickmode="linear", tick0=0, dtick=max(1, -(-top // 4)))


def build_state(net, frame, height=460):
    """Netz nach einer Entladung: Knotengröße ~ Überschuss, Farbe ~ Höhe, aktive Knoten (Überschuss > 0) rot umrandet, der entladene Knoten dick schwarz umrandet;
    Fluss (Preflow) wie in der Fluss-Abbildung, die Pushes der Entladung grün mit Menge (orange gestrichelt: ein Push über eine Rückkante nimmt Fluss zurück)."""
    fig = go.Figure()
    flow = frame.flow
    top = _wscale(net)
    push_arcs = {}
    for e, amount in frame.pushes:
        push_arcs[e // 2] = (e % 2 == 0, push_arcs.get(e // 2, (True, 0))[1] + amount)
    groups = {"idle": [], "part": [], "full": []}
    fwd_push, back_push, hover, labels = [], [], [], []
    for i, (u, v, cap, cost, _) in enumerate(net.arcs):
        curve = _curve(net.pos[u], net.pos[v], 0.0)
        hover.append((curve, f"{_arc_name(net, i)}: Fluss {flow[i]} von {cap}"))
        if i in push_arcs:
            forward, amount = push_arcs[i]
            (fwd_push if forward else back_push).append(curve)
            labels.append((curve[0][3] + 1.5, curve[1][3], f"{'+' if forward else '−'}{amount}"))
        else:
            groups["idle" if flow[i] == 0 else "full" if flow[i] == cap else "part"].append((curve, flow[i]))
    _lines(fig, [c for c, _ in groups["idle"]], C.COLORS["faint"], 1.2, "ungenutzt")
    for group, color, name in (("part", "rgba(31,119,180,0.85)", "Fluss (nicht voll)"), ("full", "#0b3d91", "Fluss (Kante voll)")):
        by_width = {}
        for c, f in groups[group]:
            by_width.setdefault(round(_width(f, top)), []).append(c)
        for w, curves in by_width.items():
            _lines(fig, curves, color, w, name, showlegend=False)
        if groups[group]:
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color=color, width=4), name=name))
    _lines(fig, fwd_push, C.COLORS["path"], 5.5, "Push in dieser Entladung")
    _lines(fig, back_push, C.COLORS["back"], 5.5, "Push über eine Rückkante (nimmt Fluss zurück)", dash="dash")
    if net.m <= 80:
        _arrows(fig, [c for c, _ in groups["idle"]] + [c for c, _ in groups["part"]] + [c for c, _ in groups["full"]], "rgba(60,60,60,0.7)", 8)
    _arrows(fig, fwd_push + back_push, "rgba(30,30,30,0.9)", 11)
    _hover_points(fig, net, hover)
    _labels(fig, labels)
    n = net.n
    idx = list(range(n))
    size = [13 if v in (net.s, net.t) else 10 + min(14, 3 * frame.excess[v] ** 0.5) for v in idx]
    fig.add_trace(go.Scatter(
        x=[net.pos[v][0] for v in idx], y=[net.pos[v][1] for v in idx], mode="markers+text", showlegend=False, text=[net.labels[v] for v in idx], textposition=_node_text_positions(net, idx),
        hovertext=[f"{net.names[v]}: Höhe {frame.heights[v]}, Überschuss {frame.excess[v]}" for v in idx], hoverinfo="text",
        marker=dict(symbol=["square" if v in (net.s, net.t) else "circle" for v in idx], size=size, color=list(frame.heights), colorscale=C.COLORS["levels"], cmin=0, cmax=max(n, max(frame.heights)), showscale=True,
                    line=dict(width=1.5, color="#333"), colorbar=_colorbar(max(n, max(frame.heights))))))
    active = [v for v in idx if v not in (net.s, net.t) and frame.excess[v] > 0]
    if active:
        fig.add_trace(go.Scatter(x=[net.pos[v][0] for v in active], y=[net.pos[v][1] for v in active], mode="markers", name="Knoten mit Überschuss", hoverinfo="skip",
                                 marker=dict(symbol="circle-open", size=[16 + min(14, 3 * frame.excess[v] ** 0.5) for v in active], color=C.COLORS["cut"], line=dict(width=2.5))))
        _labels(fig, [(net.pos[v][0] + 2.2, net.pos[v][1] + 3.2, f"+{frame.excess[v]}") for v in active])
    if frame.node is not None:
        v = frame.node
        fig.add_trace(go.Scatter(x=[net.pos[v][0]], y=[net.pos[v][1]], mode="markers", name="entladener Knoten", hoverinfo="skip", marker=dict(symbol="circle-open", size=26, color="#111", line=dict(width=3.5))))
    fig = _layout(fig, net, height)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=90), legend=dict(orientation="h", y=-0.3))
    return fig


def build_heights(net, frame, height=460):
    """Höhenschema: x = Kartenposition, y = Höhe. Restkanten blass, zulässige Restkanten (eine Stufe bergab) dunkel; gestrichelte Linie bei der Höhe n von S.
    Knoten auf oder über dieser Linie erreichen T nicht mehr (Seite von S des Schnitts)."""
    fig = go.Figure()
    n = net.n
    ys = sorted({p[1] for p in net.pos}, reverse=True)
    x = [net.pos[v][0] + 2.4 * (ys.index(net.pos[v][1]) - len(ys) / 2) for v in range(n)]
    h = frame.heights
    plain, admissible, hover = [], [], []
    for i, (u, v, cap, _, _) in enumerate(net.arcs):
        for a, b, res in ((u, v, cap - frame.flow[i]), (v, u, frame.flow[i])):
            if res <= 0:
                continue
            seg = ([x[a], x[b]], [h[a], h[b]])
            (admissible if h[a] == h[b] + 1 else plain).append(seg)
            hover.append((seg, f"{net.names[a]} → {net.names[b]}: Rest {res}, Höhenunterschied {h[a] - h[b]}" + (" (zulässig)" if h[a] == h[b] + 1 else "")))
    for segs, color, w, name in ((plain, "rgba(150,150,150,0.35)", 1, "Restkante"), (admissible, "rgba(40,70,110,0.9)", 2.4, "zulässige Restkante (eine Stufe bergab)")):
        px, py = [], []
        for sx, sy in segs:
            px += sx + [None]
            py += sy + [None]
        if px:
            fig.add_trace(go.Scatter(x=px, y=py, mode="lines", line=dict(color=color, width=w), hoverinfo="skip", name=name))
    hx, hy, ht = [], [], []
    for (sx, sy), label in hover:
        for k in (0.25, 0.5, 0.75):
            hx.append(sx[0] + k * (sx[1] - sx[0]))
            hy.append(sy[0] + k * (sy[1] - sy[0]))
            ht.append(label)
    fig.add_trace(go.Scatter(x=hx, y=hy, mode="markers", marker=dict(size=9, opacity=0), hovertext=ht, hoverinfo="text", showlegend=False))
    idx = list(range(n))
    size = [13 if v in (net.s, net.t) else 10 + min(14, 3 * frame.excess[v] ** 0.5) for v in idx]
    fig.add_trace(go.Scatter(
        x=x, y=list(h), mode="markers+text", showlegend=False, text=[net.labels[v] or "" for v in idx], textposition="top center",
        hovertext=[f"{net.names[v]}: Höhe {h[v]}, Überschuss {frame.excess[v]}" for v in idx], hoverinfo="text",
        marker=dict(symbol=["square" if v in (net.s, net.t) else "circle" for v in idx], size=size, color=list(h), colorscale=C.COLORS["levels"], cmin=0, cmax=max(n, max(h)), line=dict(width=1.5, color="#333"))))
    active = [v for v in idx if v not in (net.s, net.t) and frame.excess[v] > 0]
    if active:
        fig.add_trace(go.Scatter(x=[x[v] for v in active], y=[h[v] for v in active], mode="markers", name="Knoten mit Überschuss", hoverinfo="skip",
                                 marker=dict(symbol="circle-open", size=[16 + min(14, 3 * frame.excess[v] ** 0.5) for v in active], color=C.COLORS["cut"], line=dict(width=2.5))))
    if frame.node is not None:
        v = frame.node
        fig.add_trace(go.Scatter(x=[x[v]], y=[h[v]], mode="markers", name="entladener Knoten", hoverinfo="skip", marker=dict(symbol="circle-open", size=26, color="#111", line=dict(width=3.5))))
    fig.add_hline(y=n, line=dict(color="#555", dash="dash"), annotation_text=f"Höhe {n} = Höhe von S", annotation_position="top left")
    fig.update_xaxes(visible=False)
    fig.update_yaxes(title="Höhe", range=[-1.5, max(n, max(h)) + 4], dtick=max(1, n // 6), zeroline=False)
    fig = _base(fig, height)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=50), legend=dict(orientation="h", y=-0.12))
    return fig


def build_phase_bars(res, height=300):
    """Operationen (Pushes und Relabels gestapelt) und durchsuchte Kanten je Phase."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    labels = ["Phase 1<br>(Fluss zu T)", "Phase 2<br>(Überschuss zurück zu S)"]
    fig.add_trace(go.Bar(x=labels, y=[res.by_phase[0][1], res.by_phase[1][1]], name="Pushes", marker_color="#2ca02c", opacity=0.75), secondary_y=False)
    fig.add_trace(go.Bar(x=labels, y=[res.by_phase[0][2], res.by_phase[1][2]], name="Relabels", marker_color="#ff7f0e", opacity=0.75), secondary_y=False)
    fig.add_trace(go.Scatter(x=labels, y=[res.by_phase[0][3], res.by_phase[1][3]], mode="lines+markers", name="durchsuchte Kanten", line=dict(color="#1f77b4")), secondary_y=True)
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="Operationen", secondary_y=False, rangemode="tozero")
    fig.update_yaxes(title="durchsuchte Kanten", secondary_y=True, rangemode="tozero", showgrid=False)
    return _base(fig, height)


def build_scans_hist(pr_scans, dinic_scans, ek_scans, current=None, height=300):
    """Durchsuchte Kanten je Netz: Push-Relabel, Dinic und Edmonds-Karp übereinandergelegt."""
    fig = go.Figure()
    for values, name, color in ((ek_scans, "Edmonds-Karp", "#1f77b4"), (pr_scans, "Push-Relabel", "#ff7f0e"), (dinic_scans, "Dinic", "#2ca02c")):
        fig.add_trace(go.Histogram(x=values, xbins=dict(size=50), name=name, marker_color=color, opacity=0.6))
    fig.update_layout(barmode="overlay")
    if current is not None:
        fig.add_vline(x=current, line=dict(color=C.COLORS["optimal"], dash="dash"), annotation_text="Ihre Ziehung", annotation_position="top")
    fig.update_xaxes(title="durchsuchte Kanten")
    fig.update_yaxes(title="Netze")
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.35), height=height + 50, margin=dict(l=10, r=10, t=30 if current is not None else 10, b=10))
    return fig


def build_configs(rows, dinic_mean, ek_mean, height=340):
    """Durchsuchte Kanten (Mittel) der neun Kombinationen aus Knotenwahl und Heuristiken; dazu Dinic und Edmonds-Karp als Linien."""
    fig = go.Figure()
    colors = {"none": "#d62728", "gap": "#ff7f0e", "both": "#2ca02c"}
    names = {"none": "keine Heuristik", "gap": "Gap", "both": "Gap + Global Relabeling"}
    sel_label = {"fifo": "FIFO", "highest": "Highest-Label", "generic": "beliebig"}
    for heur in ("none", "gap", "both"):
        sub = [r for r in rows if r["heuristics"] == heur]
        fig.add_trace(go.Bar(x=[sel_label[r["selection"]] for r in sub], y=[r["scanned_mean"] for r in sub], name=names[heur], marker_color=colors[heur], opacity=0.85))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="#2ca02c", dash="dash"), name=f"Dinic ({dinic_mean:.0f})"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="#1f77b4", dash="dash"), name=f"Edmonds-Karp ({ek_mean:.0f})"))
    fig.add_hline(y=dinic_mean, line=dict(color="#2ca02c", dash="dash"))
    fig.add_hline(y=ek_mean, line=dict(color="#1f77b4", dash="dash"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="durchsuchte Kanten (Mittel)")
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.2), height=height + 40)
    return fig


def build_scaling(rows, height=340):
    """Durchsuchte Kanten gegen die Kantenzahl (doppelt logarithmisch): Push-Relabel (drei Varianten), Dinic, Edmonds-Karp; dazu die Kantenzahl selbst."""
    fig = go.Figure()
    m = [r["m"] for r in rows]
    for key, label, color, dash in (("pr", "Push-Relabel (FIFO, beide Heuristiken)", "#ff7f0e", "solid"), ("pr_hl", "Push-Relabel (Highest-Label, beide)", "#9467bd", "dot"),
                                    ("pr_none", "Push-Relabel ohne Heuristiken", "#d62728", "dot"), ("dinic", "Dinic", "#2ca02c", "solid"), ("ek", "Edmonds-Karp", "#1f77b4", "solid")):
        fig.add_trace(go.Scatter(x=m, y=[r[key] for r in rows], mode="lines+markers", name=label, line=dict(color=color, dash=dash)))
    fig.add_trace(go.Scatter(x=m, y=m, mode="lines", name="Kanten des Netzes", line=dict(color="#555", dash="dashdot")))
    fig.update_xaxes(title="Kanten des Netzes", type="log")
    fig.update_yaxes(title="durchsuchte Kanten", type="log")
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.4), height=height + 70)
    return fig


def build_phase2(rows, height=340):
    """Anteil von Phase 2 an Operationen und durchsuchten Kanten und Anteil der Netze ohne Phase-2-Arbeit, je Auslastung."""
    fig = go.Figure()
    x = [r["load"] for r in rows]
    fig.add_trace(go.Scatter(x=x, y=[100 * r["scan_share2"] for r in rows], mode="lines+markers", name="Phase 2: Anteil der durchsuchten Kanten", line=dict(color="#1f77b4")))
    fig.add_trace(go.Scatter(x=x, y=[100 * r["ops_share2"] for r in rows], mode="lines+markers", name="Phase 2: Anteil der Operationen", line=dict(color="#ff7f0e")))
    fig.add_trace(go.Scatter(x=x, y=[100 * r["share_no_phase2"] for r in rows], mode="lines+markers", name="Netze ganz ohne Phase-2-Arbeit", line=dict(color="#555", dash="dot")))
    fig.update_xaxes(title="Auslastung: Nachfrage in % der Werkskapazität")
    fig.update_yaxes(title="Anteil [%]", range=[0, 100])
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.3), height=height + 50)
    return fig
