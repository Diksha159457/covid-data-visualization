import json
import re

import pandas as pd
import pytest

import script


@pytest.fixture(scope="module")
def sources():
    return script.load_snapshot()


@pytest.fixture(scope="module")
def payload(sources):
    return script.build_payload(*sources)


def _embedded(html: str) -> dict:
    raw = re.search(r"const payload = (\{.*?\});\n", html, re.S).group(1)
    return json.loads(raw.replace("<\\/", "</"))


@pytest.mark.parametrize(
    "value,expected",
    [
        (1_234_567_890, "1.23B"),
        (5_600_000, "5.60M"),
        (12_300, "12.3K"),
        (999, "999"),
        (None, "N/A"),
        (float("nan"), "N/A"),
    ],
)
def test_format_number(value, expected):
    assert script.format_number(value) == expected


def test_all_tracked_countries_present_in_trend(payload):
    # v1 silently dropped the United States: the source calls it "US"
    assert {row["location"] for row in payload["trend"]} == set(script.TRACKED_COUNTRIES)


def test_trend_is_per_million_and_non_negative(payload):
    trend = pd.DataFrame(payload["trend"])
    assert (trend["new_cases_7d_per_million"] >= 0).all()
    us = trend[trend["location"] == "United States"]
    assert us["new_cases_7d_per_million"].max() < us["new_cases_7d_avg"].max()


def test_vaccination_leaders_use_last_reported_values(payload):
    # v1 showed 10 of 12 "leaders" at 0% because the OWID latest file was sparse
    rates = [row["people_fully_vaccinated_per_hundred"] for row in payload["vaccination_leaders"]]
    assert len(rates) == 12 and min(rates) > 50
    assert rates == sorted(rates, reverse=True)


def test_world_aggregates_excluded_from_country_charts(payload):
    names = {row["location"] for row in payload["choropleth"]}
    assert "World" not in names and "Asia" not in names and len(names) > 150


def test_missing_world_row_is_an_error(sources):
    latest, history, vacc = sources
    with pytest.raises(ValueError, match="World"):
        script.build_payload(latest[latest["location"] != "World"], history, vacc)


def test_missing_tracked_country_is_an_error(sources):
    latest, history, vacc = sources
    with pytest.raises(ValueError, match="missing tracked countries"):
        script.build_payload(latest, history[history["Country"] != "India"], vacc)


def test_render_escapes_script_breakout(payload):
    evil = json.loads(json.dumps(payload))
    evil["top_cases"][0]["location"] = "</script><script>alert(1)</script>"
    html = script.render_dashboard(evil)
    assert "</script><script>alert(1)" not in html
    assert _embedded(html)["top_cases"][0]["location"].startswith("</script>")


def test_render_rejects_nan(payload):
    bad = json.loads(json.dumps(payload))
    bad["summary"]["total_cases"] = float("nan")
    with pytest.raises(ValueError):
        script.render_dashboard(bad)


def test_committed_dashboard_matches_snapshot(payload):
    """Fails if the HTML wasn't regenerated after changing the script or data."""
    committed = _embedded(script.OUTPUT_FILE.read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(payload))


def test_cli_builds_from_snapshot(tmp_path):
    out = tmp_path / "dash.html"
    script.main(["--output", str(out)])
    assert "<title>COVID-19 Global Analytics Dashboard</title>" in out.read_text()
