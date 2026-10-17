"""Literatur-Referenzwerte für Push-Relabel (ORACLE-PLAYBOOK §5.1). Jeder Wert steht in einer Quelle, die beim Schreiben eingesehen wurde (Stand der Einsicht 2026-10-17); nichts davon ist mit dem Code der Demo erzeugt.

1. scipy 1.18.1, Dokumentation von `scipy.sparse.csgraph.maximum_flow` (Abschnitt Examples, Dokumentationstext der installierten Bibliothek im Test-venv, gelesen über `maximum_flow.__doc__`):
   "A less trivial example is given in [2]_, Chapter 26.1" mit der Kapazitätsmatrix
   [[0,16,13,0,0,0],[0,0,10,12,0,0],[0,4,0,0,14,0],[0,0,9,0,0,20],[0,0,0,7,0,4],[0,0,0,0,0,0]], Quelle 0, Senke 5, Ergebnis `flow_value` = 23.
   (Das Buch selbst, Cormen u. a., Kapitel 26.1, wurde nicht eingesehen; der Wert 23 stammt aus der scipy-Dokumentation.) Die S-Seite {0, 1, 2, 4} ist von Hand gerechnet:
   Schnittkanten 1->3 (12), 4->3 (7), 4->5 (4) = 23; der Knoten 3 erreicht T über 3->5 (20, mit höchstens 19 Zufluss nicht voll).
2. networkx 3.7, Dokumentation von `networkx.maximum_flow` (Datei networkx/algorithms/flow/maxflow.py, Abschnitt Examples, Zeilen 136-153, im Test-venv gelesen):
   Kanten x->a 3, x->b 1, a->c 3, b->c 5, b->d 4, d->e 2, c->y 2, e->y 3; `flow_value` = 3.0 und `flow_dict["x"]["b"]` = 1.0.
3. Princeton COS 226, Vorlesung 22 "Mincost Flow" (Abschnitt "Mincost flow" mit der Tabelle der drei Maximalflüsse, PDF https://www.cs.princeton.edu/courses/archive/spr02/cs226/lectures/mincost.4up.pdf, Frühjahr 2002, als Text gelesen):
   Netz mit den Kanten (Kapazität) 0-1 (3), 0-2 (3), 1-3 (2), 1-4 (2), 2-3 (1), 2-4 (2), 3-5 (2), 4-5 (2); die dort gezeigten Maximalflüsse (Kosten 21, 20, 22) haben alle den Wert 4
   (Fluss aus 0: 1 + 3, 2 + 2, 2 + 2). Die S-Seite aller Knoten außer T ist von Hand gerechnet: beide Kanten nach T (2 + 2) sind voll, also kann kein Knoten T erreichen.
Offen (nicht einsehbar oder ohne Zahl im Text): Goldberg und Tarjan 1988 (Originalarbeit, nicht frei zugänglich), Cormen u. a. Kapitel 26 (Buch), das Beispiel der englischen Wikipedia
(Kapazitäten und Höhen nur als Bilder, im Text keine Ergebnisse), das Arbeitsblatt der Pomona-Vorlesung (Adresse lieferte 404)."""

import pytest

import pr_algorithm as pr
import pr_scenario as sc

CONFIGS = [(sel, gap, glob) for sel in pr.SELECTIONS for gap in (True, False) for glob in (True, False)]


def _net(n, arcs, s, t):
    return sc.Net(tuple(f"n{i}" for i in range(n)), tuple(f"n{i}" for i in range(n)), tuple((i, 0) for i in range(n)), tuple((u, v, c, 1, sc.K_OTHER) for u, v, c in arcs), s, t, False)


SCIPY_MATRIX = [[0, 16, 13, 0, 0, 0], [0, 0, 10, 12, 0, 0], [0, 4, 0, 0, 14, 0], [0, 0, 9, 0, 0, 20], [0, 0, 0, 7, 0, 4], [0, 0, 0, 0, 0, 0]]


@pytest.mark.parametrize("cfg", CONFIGS)
def test_scipy_documentation_example_flow_value_23(cfg):
    arcs = [(u, v, c) for u, row in enumerate(SCIPY_MATRIX) for v, c in enumerate(row) if c]
    res = pr.push_relabel(_net(6, arcs, 0, 5), *cfg)
    assert res.value == 23 == res.cut_capacity
    assert [v for v in range(6) if res.s_side[v]] == [0, 1, 2, 4]


@pytest.mark.parametrize("cfg", CONFIGS)
def test_networkx_documentation_example_flow_value_3(cfg):
    names = ["x", "y", "a", "b", "c", "d", "e"]                         # x = S (0), y = T (1)
    idx = {nm: i for i, nm in enumerate(names)}
    edges = [("x", "a", 3), ("x", "b", 1), ("a", "c", 3), ("b", "c", 5), ("b", "d", 4), ("d", "e", 2), ("c", "y", 2), ("e", "y", 3)]
    net = _net(7, [(idx[u], idx[v], c) for u, v, c in edges], 0, 1)
    res = pr.push_relabel(net, *cfg)
    assert res.value == 3
    assert res.flow[1] == 1                                             # flow_dict["x"]["b"] == 1.0 laut Dokumentation (Kante x->b ist die zweite)


@pytest.mark.parametrize("cfg", CONFIGS)
def test_princeton_mincost_lecture_network_has_max_flow_4(cfg):
    arcs = [(0, 1, 3), (0, 2, 3), (1, 3, 2), (1, 4, 2), (2, 3, 1), (2, 4, 2), (3, 5, 2), (4, 5, 2)]
    res = pr.push_relabel(_net(6, arcs, 0, 5), *cfg)
    assert res.value == 4 == res.cut_capacity
    assert res.s_side == (True, True, True, True, True, False)
    assert res.cut_arcs == (6, 7)
