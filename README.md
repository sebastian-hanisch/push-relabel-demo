# Push-Relabel – Fluss ohne Wege – Streamlit-Demo

*(noch nicht deployed)*

Drittes Stück der **Netzwerkfluss-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", Kontrast zu [Edmonds-Karp](https://github.com/sebastian-hanisch/edmonds-karp-demo) und [Dinic](https://github.com/sebastian-hanisch/dinic-demo):
anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo **ein** Verfahren – **Push-Relabel** (Goldberg und Tarjan, 1988) – an einem wachsenden Beispiel.
Edmonds-Karp und Dinic bauen den Fluss aus **Wegen**. Push-Relabel kommt ohne einen einzigen Weg aus: zu Beginn werden alle Kanten aus S gefüllt (ein **Preflow**), die Werke haben **Überschuss**; jeder Knoten hat eine **Höhe**, schiebt seinen Überschuss (**push**) über eine Kante genau eine Stufe bergab und hebt sich an (**relabel**), wenn keine Kante mehr bergab führt.
Alles ist lokal. Am Ende von **Phase 1** liegt in T der maximale Fluss, die Knoten, die T nicht mehr erreichen, sind der **minimale Schnitt**; in **Phase 2** fließt der restliche Überschuss zurück nach S. Vehikel wie in den Vorgänger-Demos: ein Distributionsnetz (Werke → Verteilzentren → Filialen), dazu Einheitsnetze.

**Einordnung in die Reihe (die Kanten des Graphen):** Kontrast, kein Fix: Push-Relabel löst dasselbe Problem wie Edmonds-Karp und Dinic mit einer anderen Bauweise (lokal statt über Wege). Es ist unabhängig von der Weglänge, pflegt dafür Höhen, und seine Praxis hängt an zwei Heuristiken (Gap, Global Relabeling).
Das Stück danach, **Cost Scaling** (gebaut: [cost-scaling-demo](https://github.com/sebastian-hanisch/cost-scaling-demo)), ist Push-Relabel mit ε-optimalen Kosten (Konvergenz mit der ε-Skalierung der Auktion aus der Matching-Linie); **Successive Shortest Paths** (gebaut: [ssp-demo](https://github.com/sebastian-hanisch/ssp-demo)) setzt an der Kostenblindheit an. Bisher gebaut: die ersten zehn Stücke.
```
edmonds-karp-demo (Wurzel: Restgraph, Rückkanten, Max-Flow = Min-Cut)                  [gebaut]
  ├─ dinic-demo (viele kürzeste Wege je Phase: Niveaugraph, blockierender Fluss)        [gebaut]
  ├─ push-relabel-demo (kein Weg: Überschüsse schieben, Höhen anheben)                 [dieses Stück]
  └─ ssp-demo (Kosten: der billigste Weg im Restgraphen, Potenziale)                    [gebaut]
       ├─ cycle-canceling-demo → Netzwerksimplex (network-flow-demo)                    [gebaut / gebaut als Fall-Demo]
       ├─ cost-scaling-demo (Push-Relabel + ε-Skalierung, das nutzt OR-Tools)           [gebaut]
       └─ multicommodity-demo (mehrere Güter teilen Kapazität: Kanten-LP, Preise)       [gebaut]
            ├─ mcf-column-generation-demo (Pfade als Spalten, Pricing = Dijkstra)       [gebaut]
            ├─ garg-koenemann-demo (Näherung mit Preisen, ohne LP-Löser)                [gebaut]
            └─ fixkosten-netzdesign-demo (Fixkosten: Schranke und Schnitte)             [gebaut]
                 ├─ Benders-Zerlegung (Entwurf im Master, Fluss im Teilproblem)         [geplant]
                 └─ Slope Scaling (Heuristik für große Netze)                           [geplant]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` belegt: die Lehrnetze von Hand, die Beispielnetze über ihre Seeds, die Verteilungen über 100 feste Netze (Seeds 100000–100099, dieselben wie in den Vorgänger-Demos). Standard: 3 Werke, 3 Verteilzentren, 8 Filialen, Netzdichte 60 %, Streuung 50 %, Auslastung 90 %, Warteschlange (FIFO) mit Gap und Global Relabeling. Dinic und Edmonds-Karp sind aus den Vorgänger-Demos kopiert; ein Test bewacht die Kopien (52 475 bzw. 25 367 durchsuchte Kanten über die 100 Netze).

| Frage | Ergebnis |
|---|---|
| Wird der Fluss maximal? | ✅ Ja, in allen neun Kombinationen aus Knotenwahl und Heuristiken; unabhängig gegen `networkx` (`maximum_flow` mit `preflow_push` und `dinitz`, `minimum_cut`) und `scipy` (`maximum_flow`) geprüft, dazu Brute-Force-Aufzählung aller Schnitte auf Kleinstnetzen. Der fertige Fluss ist zulässig und erhält an allen Knoten außer S und T. |
| Stimmen die Invarianten? | ✅ Nach jeder Entladung (aus dem Trace geprüft, alle neun Konfigurationen): gültige Markierung (h(S) = n, h(T) = 0, jede Restkante höchstens eine Stufe bergab), Überschuss ≥ 0 und gleich Zufluss minus Abfluss, Höhen sinken nie und bleiben unter 2n, jedes relabel hebt strikt, Pushes gehen nur über zulässige Kanten; am Ende von Phase 1 hat kein Knoten unterhalb von Höhe n Überschuss. |
| Ist es schneller als Dinic? | ❌ Nein: 312 durchsuchte Kanten gegen 254 bei Dinic (Faktor 1,23) und 525 bei Edmonds-Karp; gleich gut oder besser als Dinic nur in 20 von 100 Netzen, als Edmonds-Karp in 97. Im Beispielnetz: 281 gegen 220 und 621. |
| Was leisten die Heuristiken? | ✅ Warteschlange: ohne Heuristiken 1179 durchsuchte Kanten (Median 1332) und 135,7 Relabels; **Gap** senkt sie auf 408 (Faktor 2,9) und 47,5 Relabels, **Global Relabeling** dazu auf 312 (Faktor 1,3) und 15,5 Relabels. Ohne Heuristiken ist Push-Relabel mehr als doppelt so teuer wie Edmonds-Karp. |
| Und die Knotenwahl? | ⚠️ Mit beiden Heuristiken kaum ein Unterschied: Warteschlange 312, Highest-Label 319, beliebig 322. Ohne Heuristiken ist der höchste Knoten am besten (1074 gegen 1130 und 1179). |
| Wie wächst der Aufwand? | ⚠️ Steigung im doppelt logarithmischen Diagramm von 12 auf 166 Knoten: Push-Relabel 1,00, Highest-Label 1,12, ohne Heuristiken 1,76, Dinic 0,94, Edmonds-Karp 1,74. Push-Relabel bleibt bei jeder Größe über Dinic (1,15- bis 1,68-fach) und unter Edmonds-Karp – außer beim kleinsten Netz (121 gegen 111). Bei 166 Knoten: 8964 gegen 6189 (Dinic) und 208 698 (Edmonds-Karp, das 23-Fache). |
| Gewinnt es auf dichten Netzen? | ❌ Nicht auf diesen: das größte Netz mit Netzdichte 100 % (1832 Kanten): Push-Relabel 11 680, Dinic 9506, Edmonds-Karp 367 269 durchsuchte Kanten – das Verhältnis zu Dinic sinkt von 1,45 (Netzdichte 60 %) auf 1,23, kehrt sich aber nicht um. |
| Wo gewinnt es? | ✅ Auf der **Treppe** (fünf Ketten aus Einheitskanten, viele Phasen bei Dinic): 325 durchsuchte Kanten gegen 928 (Dinic) und 1345 (Edmonds-Karp); Push-Relabel ist von der Weglänge unabhängig. Auf der kurzen Zuordnungskette verliert es (185 gegen 69 und 100). |
| Wie viel ist Phase 2? | ⚠️ Der Überschuss aus den gesättigten Kanten von S muss zurück, auch wenn alles geliefert wird: bei Auslastung 40 % sind 19 % der Operationen Phase 2, bei 160 % noch 3 %; der Anteil der durchsuchten Kanten bleibt bei 23 bis 27 %, weil jede Phase mit einem Global Relabeling beginnt. Ab 120 % gibt es Netze ganz ohne Phase-2-Arbeit (20 %, bei 160 %: 25 %). Beispielnetz mit Auslastung 40 %: 18 der 47 Entladungen. |
| Derselbe Schnitt wie bei Edmonds-Karp? | ⚠️ In 80 von 100 Netzen (dort ist der Schnitt eindeutig); sonst hat die Seite von S bei Push-Relabel (Knoten, die T nicht erreichen) einen bis 16 Knoten mehr, im Mittel 3,35. Auf der Treppe: 41 Knoten gegen 1. Push-Relabel findet die **größte**, Edmonds-Karp und Dinic die **kleinste** Seite von S. |
| Schranken gegen Realität | ✅ Relabels im Mittel bei 2,1 % der Schranke 2n² (höchstens 3,2 %), höchste Höhe höchstens 68 % von 2n − 1, Pushes bei 0,5 % von n²·m (höchstens 0,7 %). |

## Was nicht funktioniert hat / Vorab-Hypothesen

Vor dem Schreiben der Texte wurde über die 100 Netze gemessen; einige Vermutungen aus dem Plan stimmten nicht:

- **„Push-Relabel gewinnt auf dichten Netzen.“** Nicht auf diesen Netzen: auch bei 100 % Dichte und 166 Knoten braucht es das 1,23-Fache von Dinic. Der Vorteil aus der Literatur gehört zu großen Netzen und feinen Implementierungen, nicht zu dieser sequentiellen Python-Rechnung mit gleich langen Wegen.
- **„Highest-Label ist der beste Knotenwahl.“** Nur ohne Heuristiken. Mit beiden Heuristiken ist die Warteschlange bei kleinen Netzen gleichauf und bei größeren besser: 166 Knoten: 14 674 gegen 8964 durchsuchte Kanten; nur beim kleinsten Netz (12 Knoten) liegt Highest-Label vorn.
- **„Phase 2 ist ein kleiner Nachtrag.“** Sie macht ein Viertel der durchsuchten Kanten aus und ist auch dann nötig, wenn die gesamte Nachfrage geliefert wird (Auslastung 40 %: 19 % der Operationen), denn die Werke bieten mehr an, als gebraucht wird.
- **„Ohne Heuristiken verliert es gegen Dinic.“** Zu schwach: es verliert auch gegen Edmonds-Karp (1179 gegen 525 im Mittel; bei 166 Knoten 471 487 gegen 208 698).
- **Fund beim Testen (Implementierung):** ein Global Relabeling in Phase 2 darf nur Knoten auf der Seite von S (Höhe ≥ n) anheben. Hob es alle Knoten an, die S erreichen, verletzte es die gültige Markierung für Kanten nach T (Höhe 15 gegen 0 bei Rest > 0) – ohne den Wert zu ändern, aber der Test der Invarianten je Entladung schlug an. Korrigiert; die höchste Höhe fiel dabei von 73 % auf 68 % von 2n − 1.
- **Abweichungen vom Plan:** Port 8672; kein PDF-Export; keine Kostenmessung (Push-Relabel ist wie Edmonds-Karp und Dinic kostenblind).
- Bestätigt wurde: ohne Heuristiken sind es viel mehr Relabels, Gap und Global Relabeling senken den Aufwand stark, und der Schnitt liegt am anderen Ende als bei Edmonds-Karp und Dinic.

## Was die Demo zeigt

- **Entladungen in Aktion:** Schritt-Slider und ▶️ über die Bilder: **Start** (der Preflow), je **Entladung** ein Bild (ein Knoten wird geleert: seine Pushes und Relabels, Gap und Global Relabeling werden vermerkt), das **Ende von Phase 1** mit Flusswert und Schnitt, die Bilder von Phase 2 (Überschuss zurück zu S) und am Schluss der fertige Fluss mit dem **Beweis**. Links das Netz (Knotenfarbe = Höhe, Größe ~ Überschuss, aktive Knoten rot umringt, der entladene Knoten schwarz, Pushes grün mit Menge), rechts das **Höhenschema** (x = Kartenposition, y = Höhe, zulässige Kanten – eine Stufe bergab – dunkel, Linie bei Höhe n). Darunter Operationen und durchsuchte Kanten je Phase.
- **Fluss ohne Wege – schneller als Dinic?** Flusswert, Entladungen, Operationen, durchsuchte Kanten gegen Dinic und Edmonds-Karp; Verteilung über 100 feste Netze (Histogramm mit der Marke „Ihre Ziehung“, Tabelle mit Mittel und Median).
- **Experimente (🔬):** Heuristiken × Knotenwahl (alle neun Kombinationen), Phase 2 über die Auslastung, Skalierung von 12 bis 166 Knoten und das dichte Netz, Schranken gegen Realität, der andere Schnitt.
- **Feste Netze** (Treppe, Zuordnung als Fluss) und zufällige Distributionsnetze; **Wo die Annahmen enden:** welches spätere Stück an welcher Schwäche ansetzt.

## Modell und Verfahren

- **Netz und Restgraph:** wie in den Vorgänger-Demos (Quelle S, Werke, Verteilzentren als Eingang und Ausgang gespalten, Filialen, Senke T; Restkanten als Paar 2i/2i+1); ganzzahlig, eigener Zufallsgenerator SplitMix64 statt `numpy.random`.
- **Preflow, Höhen, Operationen:** h(S) = n, h(T) = 0; push über eine zulässige Kante (Rest > 0, h(u) = h(v) + 1), relabel auf 1 + kleinste Restnachbarhöhe. Solange h(S) = n gilt, gibt es keinen S-T-Weg im Restgraphen; Phase 1 entlädt nur Knoten mit h < n.
- **Schnitt:** die Knoten, die T im Restgraphen nicht mehr erreichen, sind die (größte) Seite von S eines minimalen Schnitts; seine Kanten sind voll, seine Kapazität ist der Flusswert.
- **Phase 2:** die übrigen Überschüsse stecken in Knoten mit Höhe ≥ n; sie werden weiter angehoben (bis 2n − 1) und fließen zu S zurück.
- **Heuristiken:** Zeigerliste (current arc) je Knoten; **Gap** (keine besetzte Höhe k < n mehr: alle Knoten darüber springen auf n + 1); **Global Relabeling** (am Anfang und alle n Relabels: exakte Entfernungen zu T, in Phase 2 n + Entfernung zu S; Höhen sinken nie). Knotenwahl: Warteschlange, höchster Knoten, beliebig (kleinster Index).
- **Laufzeit:** O(n²m) für beliebige Knotenwahl, O(n²√m) mit Highest-Label; gemessen als durchsuchte Kanten (jede in Entladung, relabel oder Global Relabeling angesehene Restkante) und als Operationen.

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `pr_constants.py` | Regler-Grenzen, Presets und Hilfetexte, feste Seed-Mengen |
| `pr_presets.py` | Permalink, Preset- und Zufalls-Seed-Logik (Standardmuster des Portfolios) |
| `pr_scenario.py` | Distributionsnetz, eigener Zufallsgenerator, Lehrnetze (Treppe, Zuordnungskette) |
| `pr_algorithm.py` | Push-Relabel: Preflow, push, relabel, Zeigerliste, Gap, Global Relabeling, beide Phasen, Schnitt, Trace je Entladung |
| `pr_dinic.py`, `pr_edmonds_karp.py` | Kopien der Vorgänger-Demos als Vergleichsbasis (ohne Import, durch einen Test bewacht) |
| `pr_evaluation.py` | Urteil, Verteilungen, neun Konfigurationen, Phase 2, Skalierung, Schranken, Schnitt |
| `pr_visualization.py` | Plotly-Abbildungen (Achsen gesperrt für Touch-Geräte; Hover über unsichtbare Marker entlang der Kanten) |
| `tests/` | Algorithmus (Handfälle, `networkx`/`scipy`/Brute Force als Gegenprobe, Invarianten je Entladung, Schnitt unabhängig nachgebaut, Global Relabeling gegen BFS-Entfernungen, Gap), Szenario und Auswertung, Presets, belegte Zahlen, AppTest-Rauchtests |

Alle Daten sind synthetisch; die Laufzeit braucht nur numpy, pandas, plotly und streamlit (scipy und networkx sind reine Testorakel).

## Lokal starten

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\streamlit run app.py
```

## Tests ausführen

```bash
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python -m pytest tests -v
```

Die Logik rechnet ausschließlich mit ganzen Zahlen; die im Text genannten Anteile und Mediane sind deshalb auf jeder Plattform identisch.
Die CI (`.github/workflows/tests.yml`) läuft auf Ubuntu mit Python 3.12, bei jedem Push und wöchentlich mit den jeweils neuesten Bibliotheksversionen.
