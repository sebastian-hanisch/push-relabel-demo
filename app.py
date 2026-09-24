"""Push-Relabel - Fluss ohne Wege - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo EIN Verfahren - Push-Relabel mit Überschüssen und Höhen - und lässt stattdessen das Beispiel wachsen.
Drittes Stück der Netzwerkfluss-Linie der "Konzepte"-Reihe, Kontrast zu "Edmonds-Karp" und "Dinic": Fluss entsteht nicht über Wege, sondern lokal. Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import time

import streamlit as st

import pr_constants as C
import pr_evaluation as ev
import pr_scenario as sc
from pr_presets import (
    KEPT,
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    seed_widget,
    sync_query_params,
)
from pr_scenario import build
from pr_visualization import (
    build_configs,
    build_flow,
    build_heights,
    build_phase2,
    build_phase_bars,
    build_scaling,
    build_scans_hist,
    build_state,
)

st.set_page_config(page_title="Push-Relabel – Sebastian Hanisch", layout="wide")

SEL_SHORT = {"fifo": "FIFO", "highest": "Highest-Label", "generic": "beliebig"}
HEUR_SHORT = {"none": "keine Heuristik", "gap": "nur Gap", "both": "Gap + Global Relabeling"}


def _pct(x, digits=0):
    return "–" if x is None else f"{x:.{digits}f} %".replace(".", ",")


def _share(x):
    """Anteil (0..1) als 'nn %'."""
    return f"{100 * x:.0f} %"


def _f(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _int(x):
    return f"{int(round(x)):,}".replace(",", " ")


def _stage_text(stage_caps):
    parts = [f"{sc.KIND_LABELS[k]} {v}" for k, v in stage_caps.items() if k in ev.STAGE_KINDS]
    return ", ".join(parts)


@st.cache_resource(show_spinner=False, max_entries=32)
def _analysis(params, selection, heuristics):
    return ev.analyse(build(*params), selection, heuristics)


st.title("🌊 Push-Relabel – Fluss ohne Wege")
st.markdown(
    """
Edmonds-Karp und Dinic bauen den Fluss aus **Wegen** von S nach T. **Push-Relabel** kommt ohne einen einzigen Weg aus: zu Beginn werden alle Kanten aus S gefüllt, dadurch haben die Werke **Überschuss**, mehr als sie weiterleiten können.
Jeder Knoten hat eine **Höhe**; ein Knoten mit Überschuss schiebt ihn (**push**) an einen Nachbarn, der genau eine Stufe tiefer liegt, und **hebt sich an** (**relabel**), wenn keiner mehr tiefer liegt.
Alles ist lokal - kein Knoten kennt einen ganzen Weg. Am Ende von **Phase 1** liegt in T der maximale Fluss, und die Knoten, die T nicht mehr erreichen, sind der **minimale Schnitt**; in **Phase 2** fließt der Rest des Überschusses zurück zur Quelle.
Diese Demo zeigt, wie das im Netz und im **Höhenschema** aussieht, was **Gap** und **Global Relabeling** leisten - und dass Push-Relabel auf den Netzen dieser Demo **nicht** schneller ist als Dinic.
"""
)
st.caption(
    "Anders als die Fall-Demos im Portfolio, die an einem Anwendungsfall mehrere Verfahren vergleichen, zeigt diese Demo - drittes Stück der Netzwerkfluss-Linie der \"Konzepte\"-Reihe, Kontrast zu den Demos \"Edmonds-Karp\" und \"Dinic\" - **ein** Verfahren an einem wachsenden Beispiel. "
    "Dieselben Höhen und Überschüsse stecken in **Cost Scaling** (Push-Relabel mit ε-optimalen Kosten, Konvergenz mit der ε-Skalierung der Auktion aus der Matching-Linie): gebaut. Die Kosten selbst entscheiden hier noch nicht (**Successive Shortest Paths**, gebaut)."
)

with st.expander("So funktioniert Push-Relabel", expanded=True):
    st.markdown(
        """
1. **Preflow:** alle Kanten aus S werden gesättigt. Kein Knoten muss mehr weiterleiten, als er bekommt - er darf aber **Überschuss** $e(v)>0$ halten. Solche Knoten heißen *aktiv*.
2. **Höhen:** $h(S)=n$, $h(T)=0$, alle anderen zu Beginn 0 (oder die exakte Entfernung zu T). Für jede Restkante $u\\to v$ gilt $h(u)\\le h(v)+1$ - eine Kante darf nie mehr als eine Stufe bergab führen.
3. **push:** ein aktiver Knoten schiebt Überschuss über eine **zulässige** Kante (Rest $>0$ und genau eine Stufe bergab). **relabel:** gibt es keine zulässige Kante, hebt er sich auf 1 + die kleinste Höhe eines Restnachbarn an. Ein Knoten heißt *entladen*, wenn sein Überschuss weg ist.
4. **Warum das genügt:** solange $h(S)=n$ ist, kann es keinen Weg von S nach T im Restgraphen geben (er hätte höchstens $n-1$ Kanten und fiele bei jeder um höchstens 1). Wenn kein Knoten unterhalb von Höhe $n$ mehr aktiv ist, steckt also der maximale Fluss in T, und die Knoten, die T nicht mehr erreichen, bilden die **Seite von S** eines minimalen Schnitts.
5. **Phase 2:** der übrige Überschuss steckt in Knoten, die T nicht erreichen; sie werden weiter angehoben (bis $2n-1$), bis alles zu S zurückgeflossen ist - erst dann ist der Preflow ein Fluss.
6. **Heuristiken:** **Gap** - gibt es keinen Knoten mehr auf Höhe $k<n$, erreicht keiner darüber T; sie springen auf $n+1$. **Global Relabeling** - alle $n$ Relabels werden die Höhen durch die exakten Entfernungen zu T ersetzt. **Knotenwahl:** Warteschlange, höchster Knoten oder beliebig.
        """
    )

st.caption("🎯 Schnellstart – ein Beispielnetz laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    net_key = st.selectbox(
        "Netz", list(C.NETS), key="net_select", format_func=lambda k: C.NETS[k],
        help="Ein zufälliges Distributionsnetz, oder eines der festen Einheitsnetze: die Treppe (lange Ketten) zeigt, wo Push-Relabel gegen Dinic gewinnt, die Zuordnungskette, wo es verliert.",
    )
    selection = st.radio(
        "Knotenwahl", list(C.SELECTION_LABELS), key="selection_radio", format_func=lambda k: C.SELECTION_LABELS[k],
        help="Welcher aktive Knoten als Nächster entladen wird. Mit Gap und Global Relabeling machen die drei bei den Standardeinstellungen kaum einen Unterschied (im Mittel 312, 319 und 322 durchsuchte Kanten).",
    )
    heuristics = st.radio(
        "Heuristiken", list(C.HEURISTICS_LABELS), key="heuristics_radio", format_func=lambda k: C.HEURISTICS_LABELS[k],
        help="Ohne Heuristiken braucht Push-Relabel bei den Standardeinstellungen im Mittel 1179 durchsuchte Kanten (Warteschlange), mit Gap 408, mit Gap und Global Relabeling 312. Dinic braucht 254, Edmonds-Karp 525.",
    )
    if net_key == "random":
        seed_widget("p_slider")
        p = st.slider("Werke", *bounds("p_slider"), key="p_slider", help="Anzahl der Werke (oben im Netz).")
        st.session_state[KEPT["p_slider"]] = p
        seed_widget("d_slider")
        d = st.slider("Verteilzentren", *bounds("d_slider"), key="d_slider", help="Anzahl der Verteilzentren; jedes hat einen Durchsatz von 30 bis 60 % der gesamten Werkskapazität.")
        st.session_state[KEPT["d_slider"]] = d
        seed_widget("s_slider")
        s = st.slider("Filialen", *bounds("s_slider"), key="s_slider", help="Anzahl der Filialen (unten im Netz).")
        st.session_state[KEPT["s_slider"]] = s
        seed_widget("density_slider")
        density = st.slider("Netzdichte [%]", *bounds("density_slider"), key="density_slider", step=10, help="Anteil der möglichen Lanes (Werk → Verteilzentrum, Verteilzentrum → Filiale), die es gibt.")
        st.session_state[KEPT["density_slider"]] = density
        seed_widget("spread_slider")
        spread = st.slider("Streuung der Lane-Breiten [%]", *bounds("spread_slider"), key="spread_slider", step=25, help="0 = alle Lanes einer Stufe gleich breit, 100 = Kapazitäten gleichverteilt von 1 bis zum Doppelten der Grundbreite.")
        st.session_state[KEPT["spread_slider"]] = spread
        seed_widget("load_slider")
        load = st.slider("Auslastung [% der Werkskapazität]", *bounds("load_slider"), key="load_slider", step=10, help="Gesamtnachfrage der Filialen in Prozent der gesamten Werkskapazität. Je niedriger, desto mehr Überschuss muss in Phase 2 zurück zu S: bei 40 % sind es 19 % der Operationen, bei 160 % nur noch 3 %.")
        st.session_state[KEPT["load_slider"]] = load
        seed_widget("seed_input")
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.session_state[KEPT["seed_input"]] = seed
        st.button("🎲 Neues Netz generieren", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Zufalls-Seed. Die Verteilungen über 100 feste Netze weiter unten ändern sich dabei nicht - nur die Marke „Ihre Ziehung“ wandert.")
    else:
        p = int(st.session_state.get(KEPT["p_slider"], C.DEFAULT_P))
        d = int(st.session_state.get(KEPT["d_slider"], C.DEFAULT_D))
        s = int(st.session_state.get(KEPT["s_slider"], C.DEFAULT_S))
        density = int(st.session_state.get(KEPT["density_slider"], C.DEFAULT_DENSITY))
        spread = int(st.session_state.get(KEPT["spread_slider"], C.DEFAULT_SPREAD))
        load = int(st.session_state.get(KEPT["load_slider"], C.DEFAULT_LOAD))
        seed = int(st.session_state.get(KEPT["seed_input"], C.DEFAULT_SEED))
        st.caption("Dieses Netz ist fest - es gibt nichts zu erzeugen. Zahl der Werke, Verteilzentren und Filialen, Netzdichte, Streuung, Auslastung und Seed gehören zum zufälligen Netz.")

sync_query_params({"net_select": net_key, "selection_radio": selection, "heuristics_radio": heuristics, "p_slider": int(p), "d_slider": int(d), "s_slider": int(s),
                   "density_slider": int(density), "spread_slider": int(spread), "load_slider": int(load), "seed_input": int(seed)})

# feste Netze ignorieren die Zufallsregler: sonst würden gleiche Netze unter verschiedenen Schlüsseln mehrfach berechnet
params = (net_key, int(p), int(d), int(s), int(density), int(spread), int(load), int(seed))
if net_key in C.FIXED_NETS:
    params = (net_key, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, C.DEFAULT_SEED)
with st.spinner("Rechne..."):
    a = _analysis(params, selection, heuristics)
net, res = a.net, a.result
level, code, dat = ev.verdict(a)
settings = (int(p), int(d), int(s), int(density), int(spread), int(load))
frames = res.frames
n_frames = len(frames) + 1                       # dazu das Endbild mit dem Beweis

# --- Entladungen in Aktion ------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Entladungen in Aktion")
if st.session_state.get("pr_step_owner") != (params, selection, heuristics):
    st.session_state["pr_step"] = n_frames - 1
    st.session_state["pr_step_owner"] = (params, selection, heuristics)
step_col, play_col = st.columns([5, 2])
with step_col:
    step = st.slider("Bild", 0, n_frames - 1, key="pr_step", help="Bild 0 ist der Preflow nach dem Sättigen der Kanten aus S; jedes weitere Bild ist eine Entladung (ein Knoten wird geleert); ganz rechts der fertige Fluss und der Beweis.")
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch")
view_slot = st.empty()


def _pushes_text(frame):
    return ", ".join(f"{amount} → {net.names[_head(e)]}" for e, amount in frame.pushes)


def _head(e):
    u, v = net.arcs[e // 2][0], net.arcs[e // 2][1]
    return v if e % 2 == 0 else u


def _render(k):
    """Bild k: links das Netz mit Überschüssen und Höhen, rechts das Höhenschema; am Ende der Beweis."""
    with view_slot.container():
        c1, c2 = st.columns(2)
        if k >= len(frames):
            c1.markdown(f"**Fertiger Fluss** - Flusswert {res.value}")
            c1.plotly_chart(build_flow(net, res.flow), width="stretch", key=f"result_map_{k}")
            c2.markdown(f"**Beweis:** ein Schnitt der Kapazität {res.cut_capacity}")
            c2.plotly_chart(build_flow(net, res.flow, cut=res.cut_arcs, reach=res.s_side), width="stretch", key=f"proof_map_{k}")
            st.caption(f"Der Schnitt trennt die {dat['s_side']} grünen Knoten (von T aus nicht mehr erreichbar, Höhe ≥ n) von den übrigen; seine {len(res.cut_arcs)} roten Kanten sind alle voll, ihre Kapazitäten summieren sich auf {res.cut_capacity} - genau der Flusswert. "
                       f"Er ist die **größte** Seite von S unter den minimalen Schnitten; Edmonds-Karp und Dinic finden die kleinste ({dat['ek_side']} Knoten)" + (" - hier fallen beide zusammen, der Schnitt ist eindeutig." if dat["same_cut"] else " - hier sind es verschiedene Schnitte gleicher Kapazität."))
            return
        f = frames[k]
        if f.kind == "start":
            c1.markdown("**Start:** der Preflow")
            c2.markdown(f"**Höhenschema** - S auf Höhe {net.n}")
            cap = (f"Alle Kanten aus S sind gesättigt: {sum(f.excess)} Einheiten stehen jetzt in den Werken (rote Ringe mit Überschuss), S hat {f.excess[net.s]}. Die Höhe von S ist n = {net.n}, T hat 0"
                   + (f"; alle anderen Höhen sind die exakten Entfernungen zu T (Global Relabeling, {f.scanned} durchsuchte Kanten)." if f.global_relabel else "; alle anderen Knoten stehen auf 0."))
        elif f.kind == "phase1_end":
            c1.markdown(f"**Ende von Phase 1:** {f.value} Einheiten in T")
            c2.markdown(f"**Höhenschema** - {dat['s_side']} Knoten erreichen T nicht mehr")
            stuck = sum(f.excess[v] for v in range(net.n) if v not in (net.s, net.t) and f.heights[v] >= net.n)
            cap = (f"Kein Knoten unterhalb von Höhe {net.n} hat noch Überschuss. In T liegen {f.value} Einheiten: das ist der **maximale Fluss**. Die {dat['s_side']} Knoten auf Höhe ≥ {net.n} erreichen T nicht mehr; "
                   f"ihr Überschuss ({stuck}) muss in Phase 2 noch zurück zu S.")
        else:
            c1.markdown(f"**Entladung {sum(1 for x in frames[:k + 1] if x.kind == 'discharge')}** (Phase {f.phase}): {net.names[f.node]}")
            c2.markdown(f"**Höhenschema** - Phase {f.phase}")
            parts = []
            if f.pushes:
                parts.append("schiebt " + _pushes_text(f))
            if f.relabels:
                parts.append("hebt sich " + ", ".join(f"von {old} auf {new}" for old, new in f.relabels) + " an")
            cap = f"{net.names[f.node]} " + " und ".join(parts) + f" ({f.scanned} Kanten durchsucht)."
            if f.gap:
                cap += " **Gap:** keine Höhe unterhalb von n ist mehr besetzt - alle Knoten darüber springen auf n + 1, sie erreichen T nicht mehr."
            if f.global_relabel:
                cap += " Danach **Global Relabeling**: alle Höhen werden durch die exakten Entfernungen ersetzt."
        c1.plotly_chart(build_state(net, f), width="stretch", key=f"state_map_{k}")
        c2.plotly_chart(build_heights(net, f), width="stretch", key=f"heights_map_{k}")
        st.caption(cap)


if auto_play:
    for k in range(n_frames):
        _render(k)
        time.sleep(min(0.6, 8.0 / max(n_frames, 1)))
    step = n_frames - 1
else:
    _render(step)

st.plotly_chart(build_phase_bars(res), width="stretch", key="phase_chart")
st.caption("Links: Knotenfarbe = Höhe, Knotengröße ~ Überschuss (rot umringt, mit Menge); dicker schwarzer Ring = der entladene Knoten; grüne Kanten = Pushes dieser Entladung (mit Menge). Rechts das Höhenschema: dunkel = zulässige Restkante (genau eine Stufe bergab) - nur über sie wird geschoben; "
           "gestrichelte Linie = Höhe von S (n). Unten die Operationen und durchsuchten Kanten je Phase.")

st.markdown("---")

# --- Fluss ohne Wege: schneller? -----------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Fluss ohne Wege – schneller als Dinic?")
st.caption("**Entladungen** = wie oft ein Knoten geleert wird (je ein Bild); **Operationen** = Pushes und Relabels; **durchsuchte Kanten** = Aufwand in derselben Währung wie bei Edmonds-Karp und Dinic (jede angesehene Restkante, auch beim Anheben und beim Global Relabeling).")
m1, m2, m3, m4 = st.columns(4)
if net.logistic:
    m1.metric("Flusswert", f"{dat['value']} von {dat['demand']}", delta=f"{_f(dat['share'])} % der Nachfrage", delta_color="off", help="Größte Liefermenge des Netzes und die Gesamtnachfrage der Filialen.")
else:
    m1.metric("Flusswert", f"{dat['value']}", help="Größte Menge von S nach T.")
m2.metric("Entladungen", f"{dat['discharges']}", delta=f"Phase 1: {dat['discharges1']}, Phase 2: {dat['discharges2']}", delta_color="off", help="Jede Entladung leert einen Knoten (Pushes und, wenn nötig, Relabels).")
m3.metric("Operationen", f"{dat['pushes'] + dat['relabels']}", delta=f"{dat['pushes']} Pushes, {dat['relabels']} Relabels", delta_color="off",
          help=f"Von den {dat['pushes']} Pushes sättigen {dat['pushes_sat']} die Kante. Gap-Ereignisse: {dat['gaps']}, Global Relabelings: {dat['globals']}.")
m4.metric("Durchsuchte Kanten", f"{dat['scanned']}", delta=f"Dinic {dat['dinic_scanned']}, Edmonds-Karp {dat['ek_scanned']}", delta_color="off",
          help=f"Phase 1: {dat['scanned1']}, Phase 2: {dat['scanned2']}. Dinic und Edmonds-Karp durchsuchen auf demselben Netz {dat['dinic_scanned']} bzw. {dat['ek_scanned']} Kanten.")

if code == "delivered":
    st.success(f"✅ Die gesamte Nachfrage ({dat['demand']}) wird geliefert; die Seite von S des Schnitts hat {dat['s_side']} Knoten. Push-Relabel durchsucht {dat['scanned']} Kanten, Dinic {dat['dinic_scanned']}, Edmonds-Karp {dat['ek_scanned']}.")
elif code == "disconnected":
    st.warning("⚠️ Es kommt gar nichts an: kein Weg führt von einem Werk über ein Verteilzentrum zu einer Filiale. Der Flusswert ist 0, Phase 1 ist nach dem Preflow sofort fertig, und der gesamte Überschuss geht in Phase 2 zurück zu S.")
elif code == "bottleneck":
    covered = dat["stage_caps"].get(sc.K_DEMAND, 0)
    extra = f" (dazu {covered} Einheiten Nachfrage schon gedeckter Filialen)" if covered else ""
    st.warning(f"⚠️ Das Netz schafft höchstens **{dat['value']} von {dat['demand']}** Einheiten ({_f(dat['share'], 0)} %). Engpass: **{_stage_text(dat['stage_caps'])}**{extra}. "
               f"Push-Relabel durchsucht {dat['scanned']} Kanten, Dinic {dat['dinic_scanned']}, Edmonds-Karp {dat['ek_scanned']}.")
else:
    st.info(f"ℹ️ Flusswert {dat['value']}; die Seite von S des Schnitts hat {dat['s_side']} Knoten (bei Edmonds-Karp {dat['ek_side']}). Push-Relabel durchsucht {dat['scanned']} Kanten, Dinic {dat['dinic_scanned']}, Edmonds-Karp {dat['ek_scanned']}.")

if net_key in C.FIXED_NETS:
    st.info("Festes Netz: es gibt nur diese eine Ziehung. Für die Verteilungen über viele Netze ein zufälliges Distributionsnetz wählen.")
else:
    st.markdown(f"**Nicht nur dieses eine Netz:** {len(C.DIST_SEEDS)} feste Netze mit denselben Einstellungen (Werke {p}, Verteilzentren {d}, Filialen {s}, Netzdichte {density} %, Streuung {spread} %, Auslastung {load} %), getrennt vom Seed oben; Knotenwahl und Heuristiken wie eingestellt.")
    dist = ev.distribution(*settings, selection, heuristics)
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Entladungen", _f(dist["discharges_mean"], 1), delta=f"Median {_f(dist['discharges_median'], 0)}, höchstens {dist['discharges_max']}", delta_color="off", help="Mittel über die Netze.")
    p2.metric("Operationen", _f(dist["pushes_mean"] + dist["relabels_mean"], 1), delta=f"{_f(dist['pushes_mean'], 1)} Pushes, {_f(dist['relabels_mean'], 1)} Relabels", delta_color="off", help="Pushes und Relabels im Mittel.")
    p3.metric("Durchsuchte Kanten", _f(dist["scanned_mean"], 0), delta=f"Dinic {_f(dist['dinic_mean'], 0)}, Edmonds-Karp {_f(dist['ek_mean'], 0)}", delta_color="off", help="Mittel über die Netze: Push-Relabel gegen Dinic und Edmonds-Karp.")
    p4.metric("Höchstens so viele wie Dinic", _share(dist["share_le_dinic"]), delta=f"Edmonds-Karp: {_share(dist['share_le_ek'])}", delta_color="off", help="Anteil der Netze, in denen Push-Relabel höchstens so viele Kanten durchsucht wie Dinic; im Delta der Anteil gegen Edmonds-Karp.")
    if dist["share_le_dinic"] >= 0.5:
        st.success(f"✅ In {_share(dist['share_le_dinic'])} der {dist['n_seeds']} Netze durchsucht Push-Relabel höchstens so viele Kanten wie Dinic - im Mittel {_f(dist['scanned_mean'], 0)} statt {_f(dist['dinic_mean'], 0)}.")
    else:
        st.warning(f"⚠️ Nur in {_share(dist['share_le_dinic'])} der {dist['n_seeds']} Netze durchsucht Push-Relabel höchstens so viele Kanten wie Dinic (im Mittel {_f(dist['scanned_mean'], 0)} gegen {_f(dist['dinic_mean'], 0)}), in {_share(dist['share_le_ek'])} höchstens so viele wie Edmonds-Karp ({_f(dist['ek_mean'], 0)}).")
    st.plotly_chart(build_scans_hist(dist["cols"]["scanned"], dist["cols"]["dinic"], dist["cols"]["ek"], current=dat["scanned"] if net.logistic else None), width="stretch", key="scans_hist")
    st.markdown("**Aufwand im Vergleich** (Mittel und Median über die Netze; durchsuchte Kanten statt Sekunden):")
    st.table({"Verfahren": [f"Push-Relabel ({SEL_SHORT[selection]}, {HEUR_SHORT[heuristics]})", "Dinic", "Edmonds-Karp"],
              "durchsuchte Kanten (Mittel)": [_f(dist["scanned_mean"], 0), _f(dist["dinic_mean"], 0), _f(dist["ek_mean"], 0)],
              "durchsuchte Kanten (Median)": [_f(dist["scanned_median"], 0), _f(dist["dinic_median"], 0), _f(dist["ek_median"], 0)],
              "größter Wert": [dist["scanned_max"], dist["dinic_max"], dist["ek_max"]]})
    st.caption(f"Das Netz hat im Mittel {_f(dist['edges_mean'], 0)} Kanten und {_f(dist['nodes_mean'], 0)} Knoten. Push-Relabel legt den Fluss nicht über Wege, sondern lokal - dafür pflegt es Höhen. Auf diesen kleinen, geschichteten Netzen mit lauter gleich langen Wegen ist das der größere Aufwand als Dinics Niveaugraph.")

st.markdown("---")

# --- Vergleich -----------------------------------------------------------------------------------------------------------------------------

with st.expander("🔧 Wie wir das erreichen – Verfahren im Vergleich"):
    st.markdown("**Was jede Konfiguration für das Netz oben findet**")
    rows = []
    for sel, heur in ev.CONFIGS:
        r = ev.run(net, sel, heur, keep_trace=False)
        rows.append((f"{SEL_SHORT[sel]}, {HEUR_SHORT[heur]}", r.value, r.discharges, r.pushes, r.relabels, r.scanned))
    rows.append(("Dinic", dat["value"], "–", "–", "–", dat["dinic_scanned"]))
    rows.append(("Edmonds-Karp", dat["value"], "–", "–", "–", dat["ek_scanned"]))
    st.table({"Verfahren": [r[0] for r in rows], "Flusswert": [r[1] for r in rows], "Entladungen": [str(r[2]) for r in rows], "Pushes": [str(r[3]) for r in rows], "Relabels": [str(r[4]) for r in rows], "durchsuchte Kanten": [r[5] for r in rows]})
    st.caption("Alle Konfigurationen erreichen denselben Flusswert und denselben Schnitt (die größte Seite von S). Sie unterscheiden sich nur im Aufwand.")
    st.markdown("**Protokoll der Entladungen** (aktuelle Einstellung)")
    log = [(k, f) for k, f in enumerate(frames) if f.kind == "discharge"]
    if log:
        st.dataframe({"Bild": [k for k, _ in log], "Phase": [f.phase for _, f in log], "Knoten": [net.names[f.node] for _, f in log], "Pushes": [_pushes_text(f) for _, f in log],
                      "Relabels": [", ".join(f"{o} → {nw}" for o, nw in f.relabels) for _, f in log], "Gap": ["ja" if f.gap else "" for _, f in log], "durchsuchte Kanten": [f.scanned for _, f in log]}, hide_index=True, width="stretch")
    else:
        st.caption("Keine Entladung.")

st.markdown("---")

# --- Experimente -------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Was leisten Gap und Global Relabeling – und die Knotenwahl?")
if net_key in C.FIXED_NETS:
    st.info("Für die Verteilung über viele Netze ein zufälliges Distributionsnetz wählen. Für das feste Netz oben zeigt der Vergleich im Expander alle neun Konfigurationen.")
else:
    cfg_rows = ev.config_table(*settings)
    base = {(r["selection"], r["heuristics"]): r for r in cfg_rows}
    dist = ev.distribution(*settings, selection, heuristics)
    st.plotly_chart(build_configs(cfg_rows, dist["dinic_mean"], dist["ek_mean"]), width="stretch", key="config_chart")
    st.table({"Knotenwahl": [SEL_SHORT[r["selection"]] for r in cfg_rows], "Heuristiken": [HEUR_SHORT[r["heuristics"]] for r in cfg_rows], "durchsuchte Kanten (Mittel)": [_f(r["scanned_mean"], 0) for r in cfg_rows],
              "durchsuchte Kanten (Median)": [_f(r["scanned_median"], 0) for r in cfg_rows], "Relabels": [_f(r["relabels_mean"], 1) for r in cfg_rows], "Pushes": [_f(r["pushes_mean"], 1) for r in cfg_rows],
              "Gap-Ereignisse": [_f(r["gaps_mean"], 2) for r in cfg_rows], "Global Relabelings": [_f(r["globals_mean"], 1) for r in cfg_rows]})
    none, gap, both = (base[("fifo", h)]["scanned_mean"] for h in ("none", "gap", "both"))
    st.caption(f"Mittel über {len(C.DIST_SEEDS)} feste Netze, Werke, Verteilzentren, Filialen, Netzdichte, Streuung und Auslastung wie oben. Bei der Warteschlange spart **Gap** den Faktor {_f(none / gap, 1)} ({_f(none, 0)} → {_f(gap, 0)} durchsuchte Kanten), **Global Relabeling** dazu noch {_f(gap / both, 1)} ({_f(gap, 0)} → {_f(both, 0)}) und senkt die Relabels von {_f(base[('fifo', 'gap')]['relabels_mean'], 1)} auf {_f(base[('fifo', 'both')]['relabels_mean'], 1)}. "
               f"Ohne Heuristiken ist Push-Relabel mit {_f(none, 0)} teurer als Edmonds-Karp ({_f(dist['ek_mean'], 0)}). Die **Knotenwahl** spielt mit beiden Heuristiken kaum eine Rolle; ohne sie ist der höchste Knoten am besten.")

st.subheader("🔬 Phase 2: warum muss Überschuss zurück?")
st.caption("Zu Beginn werden **alle** Kanten aus S gefüllt - auch wenn die Werke mehr anbieten, als die Filialen brauchen. Alles, was T nicht erreicht, muss in Phase 2 zurück zu S. Je niedriger die Auslastung, desto mehr Überschuss.")
if net_key in C.FIXED_NETS:
    st.info("Für dieses Experiment ein zufälliges Distributionsnetz wählen.")
else:
    if st.button("Auslastung von 40 bis 160 % durchfahren (40 Netze je Wert, dauert wenige Sekunden)", key="phase2_start"):
        st.session_state["phase2_on"] = settings[:5]
    if st.session_state.get("phase2_on") == settings[:5]:
        with st.spinner(f"Rechne {len(C.LOAD_SWEEP)} Auslastungen × {len(C.SWEEP_SEEDS)} Netze..."):
            p2_rows = ev.phase2_sweep(*settings[:5])
        st.plotly_chart(build_phase2(p2_rows), width="stretch", key="phase_share_chart")
        st.table({"Auslastung": [f"{r['load']} %" for r in p2_rows], "Ø geliefert": [f"{r['served_mean']:.0f} %" for r in p2_rows], "Phase 2: Anteil der Operationen": [_share(r["ops_share2"]) for r in p2_rows],
                  "Phase 2: Anteil der durchsuchten Kanten": [_share(r["scan_share2"]) for r in p2_rows], "Netze ohne Phase-2-Arbeit": [_share(r["share_no_phase2"]) for r in p2_rows]})
        st.caption("Mittel über 40 feste Netze je Auslastung (Warteschlange, Gap + Global Relabeling). Der Anteil der Operationen sinkt mit der Auslastung, weil weniger Überschuss übrig bleibt - der Anteil der durchsuchten Kanten bleibt dagegen etwa gleich: jede Phase beginnt mit einem Global Relabeling über das ganze Netz. "
                   "Ab 120 % Auslastung gibt es Netze, in denen die Werke gar nichts zurückbekommen: alles wird gebraucht.")

st.subheader("🔬 Skalierung: wo gewinnt Push-Relabel?")
st.caption("Die Literatur nennt Push-Relabel das schnellste Verfahren für große, dichte Netze. Wie verhält es sich hier gegenüber Dinic und Edmonds-Karp, wenn das Netz wächst und dichter wird?")
if st.button("Netze von 12 bis 166 Knoten durchrechnen (dauert einige Sekunden)", key="scaling_start"):
    st.session_state["scaling_on"] = True
if st.session_state.get("scaling_on"):
    with st.spinner("Rechne 6 Netzgrößen × 10 Netze × 5 Verfahren..."):
        sc_rows = ev.scaling()
        dense = ev.scaling(sizes=(C.DENSE_SETTINGS[:3],), density=C.DENSE_SETTINGS[3])[0]
    slopes = ev.slopes(sc_rows)
    st.plotly_chart(build_scaling(sc_rows), width="stretch", key="scaling_chart")
    st.table({"Werke / DCs / Filialen": [f"{r['size'][0]} / {r['size'][1]} / {r['size'][2]}" for r in sc_rows], "Knoten": [_f(r["n"], 0) for r in sc_rows], "Kanten": [_f(r["m"], 0) for r in sc_rows],
              "Push-Relabel": [_int(r["pr"]) for r in sc_rows], "Highest-Label": [_int(r["pr_hl"]) for r in sc_rows], "ohne Heuristiken": [_int(r["pr_none"]) for r in sc_rows],
              "Dinic": [_int(r["dinic"]) for r in sc_rows], "Edmonds-Karp": [_int(r["ek"]) for r in sc_rows], "Push-Relabel ÷ Dinic": [_f(r["pr"] / r["dinic"], 2) for r in sc_rows]})
    st.caption(f"Mittel über 10 feste Netze je Größe (Netzdichte 60 %, Streuung und Auslastung auf den Standardwerten). Steigung im doppelt logarithmischen Diagramm: Push-Relabel {_f(slopes['pr'], 2)}, Highest-Label {_f(slopes['pr_hl'], 2)}, ohne Heuristiken {_f(slopes['pr_none'], 2)}, Dinic {_f(slopes['dinic'], 2)}, Edmonds-Karp {_f(slopes['ek'], 2)}. "
               f"Push-Relabel wächst wie Dinic etwa linear mit dem Netz, bleibt aber in jeder Größe darüber ({_f(min(r['pr'] / r['dinic'] for r in sc_rows), 2)}- bis {_f(max(r['pr'] / r['dinic'] for r in sc_rows), 2)}-fach). "
               f"Auch beim größten Netz mit Netzdichte 100 % ({_f(dense['m'], 0)} Kanten) durchsucht Push-Relabel {_int(dense['pr'])} Kanten, Dinic {_int(dense['dinic'])}, Edmonds-Karp {_int(dense['ek'])}. Highest-Label ist nur beim kleinsten Netz (12 Knoten) besser als die Warteschlange, ab 19 Knoten schlechter.")

st.subheader("🔬 Schranken gegen Realität")
if net_key in C.FIXED_NETS:
    st.info("Für die Schranken über viele Netze ein zufälliges Distributionsnetz wählen.")
else:
    dist = ev.distribution(*settings, selection, heuristics)
    b1, b2, b3 = st.columns(3)
    b1.metric("Relabels ÷ 2n²", _pct(100 * dist["relabel_ratio_mean"], 1), delta=f"höchstens {_pct(100 * dist['relabel_ratio_max'], 1)}", delta_color="off", help="Gemessene Relabels im Verhältnis zur Schranke 2n² (Mittel, Maximum über die Netze).")
    b2.metric("Höchste Höhe ÷ (2n − 1)", _pct(100 * dist["height_ratio_max"], 0), delta="Maximum über die Netze", delta_color="off", help="Keine Höhe kann 2n − 1 überschreiten.")
    b3.metric("Pushes ÷ n²·m", _pct(100 * dist["push_ratio_mean"], 2), delta=f"höchstens {_pct(100 * dist['push_ratio_max'], 2)}", delta_color="off", help="Gemessene Pushes im Verhältnis zur Schranke n²·m für die Pushes (Mittel, Maximum).")
    st.caption("Die Schranken sind Worst-Case-Aussagen: höchstens $2n^2$ Relabels, Höhen höchstens $2n-1$, insgesamt $O(n^2 m)$ Operationen. Gemessen sind es auf diesen Netzen Bruchteile davon - die Schranke sagt nichts darüber, wie schnell es in der Praxis geht.")

st.subheader("🔬 Der andere Schnitt")
if net_key in C.FIXED_NETS:
    st.info(f"Auf dem festen Netz oben: die Seite von S hat {dat['s_side']} Knoten, bei Edmonds-Karp {dat['ek_side']} - beide Schnitte haben dieselbe Kapazität {dat['cut_capacity']}. Für die Verteilung ein zufälliges Distributionsnetz wählen.")
else:
    dist = ev.distribution(*settings, selection, heuristics)
    c1, c2, c3 = st.columns(3)
    c1.metric("Derselbe Schnitt wie Edmonds-Karp", _share(dist["share_same_cut"]), help="Anteil der Netze, in denen die Seite von S bei Push-Relabel (Knoten, die T nicht mehr erreichen) genau die Menge der von S erreichbaren Knoten bei Edmonds-Karp und Dinic ist.")
    c2.metric("Sonst: mehr Knoten (Mittel)", _f(dist["extra_nodes_mean"], 1), delta=f"höchstens {dist['extra_nodes_max']}", delta_color="off", help="In den übrigen Netzen hat die Seite von S bei Push-Relabel so viele Knoten mehr.")
    c3.metric("Nachfrage ganz gedeckt", _share(dist["share_all_served"]), help="Anteil der Netze, in denen der Flusswert die Gesamtnachfrage erreicht.")
    st.caption("Ein Netz kann mehrere minimale Schnitte haben. Edmonds-Karp und Dinic finden die **kleinste** Seite von S (alles, was von S aus noch erreichbar ist), Push-Relabel die **größte** (alles, was T nicht mehr erreicht). Sie fallen genau dann zusammen, wenn der Schnitt eindeutig ist - hier in 80 % der Netze, sonst ist die Seite von S bei Push-Relabel um einen bis 16 Knoten größer.")

st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Nur die Menge zählt** | Push-Relabel schiebt Überschuss dorthin, wo Höhe und Rest es erlauben, ohne Preise zu kennen: welche Lanes der Fluss benutzt, entscheidet die Reihenfolge, nicht das Geld. | **Successive Shortest Paths**: der billigste Weg entscheidet; **Cost Scaling**: Push-Relabel mit ε-optimalen Kosten |
| **Das Verfahren ist schneller als Wege** | Auf den kleinen, geschichteten Netzen dieser Demo durchsucht es mit beiden Heuristiken im Mittel etwa ein Viertel mehr Kanten als Dinic und ist nur in jedem fünften Netz gleich gut. Der Vorteil aus der Literatur zeigt sich erst bei großen, dichten Netzen und in Implementierungen mit Feinschliff. | Die Treppe zeigt, wo es gewinnt: viele Phasen bei Dinic, keine Wege bei Push-Relabel |
| **Die Heuristiken sind Teil des Verfahrens** | Ohne Gap und Global Relabeling ist Push-Relabel auf diesen Netzen teurer als Edmonds-Karp. Ihre Wirkung ist Erfahrung, keine Worst-Case-Garantie: die Schranke $O(n^2 m)$ bleibt. | Nächstes Stück der Linie |
| **Sequentielle Rechnung** | Push-Relabel ist lokal und deshalb parallelisierbar - das lässt sich hier nicht messen, gezählt wird nacheinander. | Nicht Thema dieser Linie |
| **Ein Gut, teilbar** | Alle Waren sind gleich und beliebig teilbar. Mehrere Güter auf gemeinsamen Kanten machen den Fluss im Allgemeinen gebrochen. | **Mehrgüterfluss** (gebaut: multicommodity-demo) |
"""
)
st.caption("Die Netzwerkfluss-Linie ist als Ganzes geplant: Edmonds-Karp, Dinic, Push-Relabel (dieses Stück), Successive Shortest Paths (gebaut), Cycle-Canceling (gebaut), Cost Scaling (gebaut), Mehrgüterfluss (gebaut), Column Generation (gebaut), Garg-Könemann (gebaut), Fixkosten-Netzwerkdesign (gebaut), Benders-Zerlegung und Slope Scaling - bisher sind die ersten zehn gebaut.")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** Gerichteter Graph $G=(V,E)$ mit Quelle $s$, Senke $t$, ganzzahligen Kapazitäten $c_e$, $n=|V|$. Ein **Preflow** $f$ erfüllt $0\le f_e\le c_e$ und $e_f(v)=\sum_{e\in\delta^-(v)}f_e-\sum_{e\in\delta^+(v)}f_e\ge 0$ für alle $v\ne s,t$ (Überschuss). Ein Fluss ist ein Preflow mit $e_f(v)=0$ für alle $v\ne s,t$.

**Gültige Markierung.** $h:V\to\mathbb N$ mit $h(s)=n$, $h(t)=0$ und $h(u)\le h(v)+1$ für jede Restkante $(u,v)$ des Restgraphen $G_f$. Eine Restkante heißt *zulässig*, wenn $h(u)=h(v)+1$.

**Operationen.** *push*$(u,v)$ für aktives $u$ ($e_f(u)>0$) und zulässige Restkante: schiebe $\delta=\min(e_f(u),r_{uv})$. *relabel*$(u)$, wenn $u$ aktiv ist und keine Restkante zulässig: $h(u)\leftarrow 1+\min\{h(v):(u,v)\in G_f\}$. Beide erhalten die gültige Markierung; ein relabel hebt $h(u)$ um mindestens 1.

**Lemma (kein Weg).** Ist $h$ gültig, gibt es in $G_f$ keinen $s$-$t$-Weg: er hätte höchstens $n-1$ Kanten, jede senkt $h$ um höchstens 1, aber $h(s)-h(t)=n$.

**Phase 1.** Es werden nur Knoten mit $h(v)<n$ entladen. Am Ende ist $e_f(t)$ der maximale Flusswert: Sei $Z$ die Menge der Knoten, die $t$ in $G_f$ *nicht* erreichen (sie enthält $s$). Jede Kante aus $Z$ heraus ist voll, jede hinein leer - $c(Z,\bar Z)=e_f(t)$, also ist $Z$ die (größte) $s$-Seite eines minimalen Schnitts.

**Phase 2.** Der Überschuss steckt in Knoten mit $h\ge n$; sie werden weiter angehoben (Höhen bis $2n-1$), bis er nach $s$ zurückgeflossen ist. Ein Knoten mit Überschuss hat immer einen Restweg zu $s$ (Flusszerlegung), also endet das.

**Laufzeit.** Höchstens $2n-1$ Höhe je Knoten, also $O(n^2)$ Relabels; höchstens $O(nm)$ sättigende und $O(n^2m)$ nicht sättigende Pushes: **$O(n^2m)$** für beliebige Knotenwahl. Mit **Highest-Label** $O(n^2\sqrt m)$, mit Warteschlange (FIFO) $O(n^3)$. Die Zeigerliste (current arc) erhält diese Schranken.

**Gap.** Gibt es nach einem relabel keinen Knoten mehr auf Höhe $k<n$, kann kein Knoten $v$ mit $k<h(v)<n$ den Knoten $t$ erreichen (jede Restkante senkt $h$ höchstens um 1): sie werden auf $n+1$ gesetzt. **Global Relabeling** setzt $h(v)$ auf die exakte Entfernung zu $t$ in $G_f$ (Phase 2: $n$ + Entfernung zu $s$); die Höhen sinken dabei nie.

**Kosten.** Push-Relabel kennt keine Kosten; mit Kosten und $\varepsilon$-optimalen Preisen wird daraus **Cost Scaling** (Stück 6 der Linie, gebaut).

Implementiert in `pr_scenario.py` (Netze, eigener Zufallsgenerator), `pr_algorithm.py` (Preflow, push, relabel, Zeigerliste, Gap, Global Relabeling, beide Phasen, Schnitt), `pr_dinic.py` und `pr_edmonds_karp.py` (Kopien der Vorgänger-Demos als Vergleichsbasis), `pr_evaluation.py` (Kennzahlen, Verteilungen, Experimente).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
