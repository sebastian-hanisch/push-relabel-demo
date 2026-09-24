"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen der Demo "Push-Relabel: Fluss ohne Wege"."""

# --- Regler (wie in der Edmonds-Karp- und der Dinic-Demo) ----------------------------------------------------------------------------------------
P_MIN, P_MAX, DEFAULT_P = 2, 6, 3            # Werke
D_MIN, D_MAX, DEFAULT_D = 2, 6, 3            # Verteilzentren
S_MIN, S_MAX, DEFAULT_S = 3, 12, 8           # Filialen
DENSITY_MIN, DENSITY_MAX, DEFAULT_DENSITY = 20, 100, 60   # Anteil vorhandener Lanes in ganzen Prozent, Schritt 10
SPREAD_MIN, SPREAD_MAX, DEFAULT_SPREAD = 0, 100, 50       # Streuung der Lane-Breiten in ganzen Prozent, Schritt 25
LOAD_MIN, LOAD_MAX, DEFAULT_LOAD = 40, 160, 90            # Gesamtnachfrage in Prozent der Werkskapazität, Schritt 10
DEFAULT_SEED = 8
SEED_MAX = 2_000_000_000

NETS = {
    "random": "Zufälliges Distributionsnetz",
    "stair": "Treppe (Einheitsnetz, fünf Ketten)",
    "assignment": "Zuordnung als Fluss (Kette, 5 + 5)",
}
DEFAULT_NET = "random"
FIXED_NETS = ("stair", "assignment")

SELECTION_LABELS = {"fifo": "Warteschlange (FIFO)", "highest": "Höchster Knoten (Highest-Label)", "generic": "Beliebiger Knoten (kleinster Index)"}
DEFAULT_SELECTION = "fifo"
HEURISTICS_LABELS = {"none": "Keine Heuristik", "gap": "Gap", "both": "Gap + Global Relabeling"}
DEFAULT_HEURISTICS = "both"
HEURISTICS_FLAGS = {"none": (False, False), "gap": (True, False), "both": (True, True)}     # (gap, global_relabel)

# --- feste Seed-Mengen (dieselben wie in der Edmonds-Karp-Demo; unabhängig vom Nutzer-Seed) -----------------------------------------
DIST_SEEDS = tuple(range(100000, 100100))
SWEEP_SEEDS = DIST_SEEDS[:40]
SCALE_SIZES = ((2, 2, 4), (3, 3, 8), (4, 4, 16), (6, 6, 32), (8, 8, 64), (12, 12, 128))   # (Werke, DCs, Filialen)
SCALE_SEEDS = DIST_SEEDS[:10]
LOAD_SWEEP = (40, 60, 80, 90, 100, 120, 140, 160)
DENSE_SETTINGS = (12, 12, 128, 100, 50, 90)   # das größte Netz mit Netzdichte 100 %

COLORS = {
    "flow": "#1f77b4", "path": "#2ca02c", "back": "#ff7f0e", "cut": "#d62728", "reach": "#2ca02c", "dead": "#9467bd",
    "unreach": "#8c8c8c", "faint": "rgba(150,150,150,0.45)", "node": "#111111", "optimal": "#d62728", "levels": "Viridis",
}

# --- Presets -----------------------------------------------------------------------------------------------------------------
_BASE = dict(net="random", selection=DEFAULT_SELECTION, heuristics=DEFAULT_HEURISTICS, p=DEFAULT_P, d=DEFAULT_D, s=DEFAULT_S, density=DEFAULT_DENSITY, spread=DEFAULT_SPREAD, load=DEFAULT_LOAD, seed=DEFAULT_SEED)
PRESETS = {
    "🚚 Zufallsnetz": {**_BASE},
    "🏔️ Highest-Label": {**_BASE, "selection": "highest"},
    "🎲 Beliebiger Knoten": {**_BASE, "selection": "generic"},
    "🐢 Ohne Heuristiken": {**_BASE, "heuristics": "none"},
    "🕳️ Nur Gap": {**_BASE, "heuristics": "gap"},
    "↩️ Viel Rückgabe": {**_BASE, "load": 40, "seed": 3},
    "🪜 Treppe": {**_BASE, "net": "stair"},
    "💑 Zuordnung als Fluss": {**_BASE, "net": "assignment"},
}
# Jede Zahl in diesen Texten ist in tests/test_claims.py belegt (Lehrnetze von Hand, Zufallsnetze über die Seeds der Presets)
PRESET_HELP = {
    "🚚 Zufallsnetz": "3 Werke, 3 Verteilzentren, 8 Filialen: das Netz schafft 80 von 83 Einheiten. Warteschlange mit Gap und Global Relabeling: 45 Entladungen (37 in Phase 1, 8 in Phase 2), 67 Pushes, 13 Relabels, 281 durchsuchte Kanten - Dinic braucht 220, Edmonds-Karp 621. Die Seite von S des Schnitts hat 17 Knoten, dieselben wie bei Edmonds-Karp.",
    "🏔️ Highest-Label": "Dasselbe Netz mit Highest-Label: 47 + 4 Entladungen, 72 Pushes, 16 Relabels, 309 durchsuchte Kanten - derselbe Fluss, kaum anderer Aufwand: mit beiden Heuristiken entscheidet die Knotenwahl wenig.",
    "🎲 Beliebiger Knoten": "Dasselbe Netz mit dem Knoten kleinsten Index: 42 + 11 Entladungen, 74 Pushes, 15 Relabels, 307 durchsuchte Kanten - auch ohne kluge Wahl kaum schlechter als Warteschlange (281) und Highest-Label (309).",
    "🐢 Ohne Heuristiken": "Dasselbe Netz ohne Gap und Global Relabeling: 217 statt 13 Relabels, 243 statt 45 Entladungen und 1810 statt 281 durchsuchte Kanten - fast das Dreifache von Edmonds-Karp (621).",
    "🕳️ Nur Gap": "Dasselbe Netz nur mit Gap: 62 Relabels und 535 durchsuchte Kanten. Ein einziges Gap-Ereignis holt alle Knoten, die T nicht mehr erreichen, aus der Arbeit; erst Global Relabeling bringt die Höhen ohne mühsames Anheben auf die richtigen Werte.",
    "↩️ Viel Rückgabe": "Auslastung 40 %: die gesamte Nachfrage (28) wird geliefert, aber die Werke bieten mehr, als gebraucht wird - der Überschuss muss zurück. Phase 2 hat 18 der 47 Entladungen und 102 der 322 durchsuchten Kanten (32 %).",
    "🪜 Treppe": "Fünf Ketten aus Einheitskanten (20 Fahrzeuge, 20 Aufträge): 65 Entladungen, 70 Pushes, 15 Relabels, 325 durchsuchte Kanten - Dinic braucht 928, Edmonds-Karp 1345, denn Push-Relabel ist von der Weglänge unabhängig. Der Schnitt liegt am anderen Ende: 41 Knoten auf der Seite von S statt 1 bei Edmonds-Karp.",
    "💑 Zuordnung als Fluss": "Fünf Fahrzeuge und fünf Aufträge in einer Kette, jede Kante Kapazität 1: 35 Entladungen, 36 Pushes, 12 Relabels, 185 durchsuchte Kanten - Dinic braucht hier nur 69, Edmonds-Karp 100. Auf kurzen, gleich langen Wegen sind Höhen der größere Aufwand.",
}
