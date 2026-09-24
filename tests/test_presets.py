"""Presets: vollständig, in den Grenzen, und jedes Beispielnetz zeigt, was sein Hilfetext behauptet."""

import pytest

import pr_constants as C
import pr_evaluation as ev
import pr_presets as P
import pr_scenario as sc

KEYS = set(P.PRESET_KEYS)


def _net(p):
    return sc.build(p["net"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"], p["seed"])


def _analyse(p):
    return ev.analyse(_net(p), p["selection"], p["heuristics"])


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESETS) == 8
    assert all(C.PRESET_HELP[name].strip() for name in C.PRESETS)
    for name, p in C.PRESETS.items():
        assert set(p) == KEYS, name


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_values_are_inside_the_bounds_and_on_the_step_grid(name):
    p = C.PRESETS[name]
    assert p["net"] in C.NETS and p["selection"] in C.SELECTION_LABELS and p["heuristics"] in C.HEURISTICS_LABELS
    for key, state_key in P.PRESET_KEYS.items():
        spec = P.SETTING_SPECS[state_key]
        if spec.lo is not None:
            assert spec.lo <= p[key] <= spec.hi, (name, key)
    assert (p["density"] - C.DENSITY_MIN) % 10 == 0 and p["spread"] % 25 == 0 and (p["load"] - C.LOAD_MIN) % 10 == 0


def test_setting_specs_have_room_to_move():
    """Ein Regler mit lo == hi würde Streamlit abstürzen lassen."""
    assert all(spec.lo < spec.hi for spec in P.SETTING_SPECS.values() if spec.lo is not None)


def test_presets_use_seeds_outside_the_distribution_set():
    for name, p in C.PRESETS.items():
        assert p["seed"] not in C.DIST_SEEDS, name


def test_defaults_equal_the_random_net_preset():
    p = C.PRESETS["🚚 Zufallsnetz"]
    assert (p["net"], p["selection"], p["heuristics"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"], p["seed"]) == (
        C.DEFAULT_NET, C.DEFAULT_SELECTION, C.DEFAULT_HEURISTICS, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, C.DEFAULT_SEED)


def test_the_configuration_presets_share_the_default_net():
    base = C.PRESETS["🚚 Zufallsnetz"]
    for name in ("🏔️ Highest-Label", "🎲 Beliebiger Knoten", "🐢 Ohne Heuristiken", "🕳️ Nur Gap"):
        p = C.PRESETS[name]
        assert all(p[k] == base[k] for k in ("net", "p", "d", "s", "density", "spread", "load", "seed"))
    assert {C.PRESETS[n]["selection"] for n in ("🏔️ Highest-Label", "🎲 Beliebiger Knoten")} == {"highest", "generic"}
    assert {C.PRESETS[n]["heuristics"] for n in ("🐢 Ohne Heuristiken", "🕳️ Nur Gap")} == {"none", "gap"}


def test_fixed_presets_hide_the_random_controls():
    assert {n for n, p in C.PRESETS.items() if p["net"] in C.FIXED_NETS} == {"🪜 Treppe", "💑 Zuordnung als Fluss"}


def test_default_net_is_a_typical_draw():
    """Das Beispielnetz liegt bei den durchsuchten Kanten im Bereich des Medians (±15 %), hat 5 bis 20 Relabels und mindestens ein Gap-Ereignis."""
    p = C.PRESETS["🚚 Zufallsnetz"]
    dist = ev.distribution(p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"])
    r = _analyse(p).result
    assert abs(r.scanned - dist["scanned_median"]) <= 0.15 * dist["scanned_median"] and 5 <= r.relabels <= 20 and r.gaps >= 1 and r.by_phase[1][0] > 0


def test_the_presets_show_both_good_and_bad_news():
    """Positive UND negative Aussagen: auf der Treppe gewinnt Push-Relabel gegen Dinic, auf der Zuordnungskette und im Zufallsnetz verliert es; ohne Heuristiken ist es teurer als Edmonds-Karp."""
    a = {name: _analyse(p) for name, p in C.PRESETS.items()}
    assert a["🪜 Treppe"].result.scanned < a["🪜 Treppe"].dinic.scanned_total
    for name in ("🚚 Zufallsnetz", "💑 Zuordnung als Fluss"):
        assert a[name].result.scanned > a[name].dinic.scanned_total
    assert a["🐢 Ohne Heuristiken"].result.scanned > a["🐢 Ohne Heuristiken"].edmonds_karp.scanned_total
