from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


HISTORY_URL = "https://raw.githubusercontent.com/datasets/covid-19/main/data/countries-aggregated.csv"
LATEST_URL = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/latest/owid-covid-latest.csv"
OUTPUT_FILE = Path("covid_world_map.html")
TRACKED_COUNTRIES = ["United States", "India", "Brazil", "United Kingdom", "France"]


def load_latest_data() -> pd.DataFrame:
    latest = pd.read_csv(LATEST_URL)
    latest = latest[~latest["iso_code"].str.startswith("OWID_")].copy()
    latest = latest[latest["continent"].notna()].copy()
    latest["population"] = latest["population"].fillna(0)
    return latest


def load_history_data() -> pd.DataFrame:
    history = pd.read_csv(
        HISTORY_URL,
        usecols=["Date", "Country", "Confirmed"],
        parse_dates=["Date"],
    )
    history = history.rename(columns={"Date": "date", "Country": "location", "Confirmed": "confirmed"})
    history = history[history["location"].isin(TRACKED_COUNTRIES)].copy()
    history = history.sort_values(["location", "date"])
    history["new_cases"] = history.groupby("location")["confirmed"].diff().clip(lower=0).fillna(0)
    history["new_cases_7d_avg"] = (
        history.groupby("location")["new_cases"].rolling(window=7, min_periods=1).mean().reset_index(level=0, drop=True)
    )
    recent_cutoff = history["date"].max() - pd.Timedelta(days=180)
    return history[history["date"] >= recent_cutoff].copy()


def format_number(value: float | int | None) -> str:
    if pd.isna(value) or value is None:
        return "N/A"
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


def build_payload() -> dict[str, object]:
    latest = load_latest_data()
    history = load_history_data()
    world = pd.read_csv(LATEST_URL)
    world_row = world.loc[world["location"] == "World"].iloc[0]

    top_cases = (
        latest.nlargest(12, "total_cases")[["location", "total_cases", "continent"]]
        .fillna(0)
        .to_dict(orient="records")
    )

    vaccination_leaders = (
        latest[latest["population"] >= 20_000_000]
        .nlargest(12, "people_fully_vaccinated_per_hundred")[
            ["location", "people_fully_vaccinated_per_hundred", "continent"]
        ]
        .fillna(0)
        .to_dict(orient="records")
    )

    choropleth = (
        latest[["iso_code", "location", "total_cases_per_million", "total_deaths_per_million", "continent"]]
        .fillna(0)
        .to_dict(orient="records")
    )

    scatter = (
        latest[latest["population"] >= 5_000_000][
            [
                "location",
                "continent",
                "population",
                "total_cases_per_million",
                "total_deaths_per_million",
                "people_fully_vaccinated_per_hundred",
            ]
        ]
        .fillna(0)
        .to_dict(orient="records")
    )

    trend = (
        history[["date", "location", "confirmed", "new_cases_7d_avg"]]
        .fillna(0)
        .assign(date=history["date"].dt.strftime("%Y-%m-%d"))
        .to_dict(orient="records")
    )

    latest_date = pd.to_datetime(world_row["last_updated_date"]).strftime("%B %d, %Y")
    return {
        "summary": {
            "reported_on": latest_date,
            "total_cases": format_number(world_row.get("total_cases")),
            "total_deaths": format_number(world_row.get("total_deaths")),
            "people_vaccinated": format_number(world_row.get("people_vaccinated")),
            "population": format_number(world_row.get("population")),
        },
        "top_cases": top_cases,
        "vaccination_leaders": vaccination_leaders,
        "choropleth": choropleth,
        "scatter": scatter,
        "trend": trend,
    }


def render_dashboard(payload: dict[str, object]) -> str:
    payload_json = json.dumps(payload)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>COVID-19 Global Analytics Dashboard</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {{
      --bg: #08111f;
      --panel: rgba(11, 23, 40, 0.78);
      --panel-strong: #0f1d33;
      --border: rgba(148, 163, 184, 0.18);
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --accent-2: #22c55e;
      --danger: #f97316;
      --shadow: 0 24px 60px rgba(8, 15, 30, 0.45);
    }}

    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.18), transparent 30%),
        radial-gradient(circle at top right, rgba(34, 197, 94, 0.14), transparent 24%),
        linear-gradient(180deg, #08111f 0%, #020617 100%);
      min-height: 100vh;
    }}

    .shell {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}

    .hero {{
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 20px;
      margin-bottom: 20px;
    }}

    .hero-card,
    .metric,
    .chart-card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
    }}

    .hero-card {{
      padding: 28px;
    }}

    .eyebrow {{
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--accent);
      font-size: 12px;
      margin-bottom: 14px;
    }}

    h1 {{
      margin: 0 0 12px;
      font-size: clamp(32px, 5vw, 56px);
      line-height: 1.02;
    }}

    .subtitle {{
      margin: 0;
      font-size: 17px;
      line-height: 1.7;
      color: var(--muted);
      max-width: 62ch;
    }}

    .meta {{
      margin-top: 18px;
      color: var(--text);
      font-weight: 600;
    }}

    .metrics {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}

    .metric {{
      padding: 20px;
    }}

    .metric-label {{
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 10px;
    }}

    .metric-value {{
      font-size: clamp(24px, 3vw, 34px);
      font-weight: 700;
      margin-bottom: 8px;
    }}

    .metric-note {{
      font-size: 13px;
      color: var(--muted);
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 20px;
    }}

    .chart-card {{
      padding: 18px 18px 8px;
      min-height: 420px;
    }}

    .chart-title {{
      margin: 4px 8px 2px;
      font-size: 20px;
      font-weight: 700;
    }}

    .chart-copy {{
      margin: 0 8px 12px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.6;
    }}

    .plot {{
      width: 100%;
      height: 330px;
    }}

    .wide {{
      grid-column: 1 / -1;
      min-height: 560px;
    }}

    .wide .plot {{
      height: 470px;
    }}

    @media (max-width: 960px) {{
      .hero,
      .grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <article class="hero-card">
        <div class="eyebrow">Portfolio Project • Public Health Analytics</div>
        <h1>COVID-19 Global Analytics Dashboard</h1>
        <p class="subtitle">
          A richer static dashboard built from public Our World in Data feeds. This version goes beyond a basic map
          by combining global KPI cards, country comparisons, a choropleth, vaccination ranking, and six-month trend
          analysis into a single shareable artifact.
        </p>
        <div class="meta">Latest reporting date: <span id="reported-on"></span></div>
      </article>
      <section class="metrics">
        <article class="metric">
          <div class="metric-label">Total Cases</div>
          <div class="metric-value" id="total-cases"></div>
          <div class="metric-note">Cumulative cases reported globally</div>
        </article>
        <article class="metric">
          <div class="metric-label">Total Deaths</div>
          <div class="metric-value" id="total-deaths"></div>
          <div class="metric-note">Cumulative deaths reported globally</div>
        </article>
        <article class="metric">
          <div class="metric-label">People Vaccinated</div>
          <div class="metric-value" id="people-vaccinated"></div>
          <div class="metric-note">People with at least one dose</div>
        </article>
        <article class="metric">
          <div class="metric-label">Population Covered</div>
          <div class="metric-value" id="population"></div>
          <div class="metric-note">World population in the source snapshot</div>
        </article>
      </section>
    </section>

    <section class="grid">
      <article class="chart-card wide">
        <h2 class="chart-title">Global Choropleth: Cases Per Million</h2>
        <p class="chart-copy">Country-level comparison using the latest available Our World in Data snapshot.</p>
        <div class="plot" id="choropleth"></div>
      </article>

      <article class="chart-card">
        <h2 class="chart-title">Top 12 Countries by Total Cases</h2>
        <p class="chart-copy">Absolute case count keeps the ranking intuitive for recruiters reviewing the project quickly.</p>
        <div class="plot" id="top-cases"></div>
      </article>

      <article class="chart-card">
        <h2 class="chart-title">Vaccination Leaders</h2>
        <p class="chart-copy">Top countries by fully vaccinated population share, filtered to sizable populations.</p>
        <div class="plot" id="vaccinations"></div>
      </article>

      <article class="chart-card">
        <h2 class="chart-title">Tracked Country Trends</h2>
        <p class="chart-copy">Six-month rolling seven-day average of new cases for five frequently compared countries.</p>
        <div class="plot" id="trend"></div>
      </article>

      <article class="chart-card">
        <h2 class="chart-title">Cases vs Deaths Per Million</h2>
        <p class="chart-copy">Bubble size represents population so the chart balances scale with severity.</p>
        <div class="plot" id="scatter"></div>
      </article>
    </section>
  </main>

  <script>
    const payload = {payload_json};
    const summary = payload.summary;

    document.getElementById("reported-on").textContent = summary.reported_on;
    document.getElementById("total-cases").textContent = summary.total_cases;
    document.getElementById("total-deaths").textContent = summary.total_deaths;
    document.getElementById("people-vaccinated").textContent = summary.people_vaccinated;
    document.getElementById("population").textContent = summary.population;

    const baseLayout = {{
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: {{ color: "#e2e8f0", family: "Inter, sans-serif" }},
      margin: {{ t: 20, r: 20, b: 50, l: 55 }},
    }};

    Plotly.newPlot("choropleth", [{{
      type: "choropleth",
      locations: payload.choropleth.map(d => d.iso_code),
      z: payload.choropleth.map(d => d.total_cases_per_million),
      text: payload.choropleth.map(d => d.location),
      customdata: payload.choropleth.map(d => [d.total_deaths_per_million, d.continent]),
      colorscale: "Turbo",
      marker: {{ line: {{ color: "rgba(15, 23, 42, 0.4)", width: 0.4 }} }},
      colorbar: {{ title: "Cases / 1M" }},
      hovertemplate: "<b>%{{text}}</b><br>Continent: %{{customdata[1]}}<br>Cases per million: %{{z:.0f}}<br>Deaths per million: %{{customdata[0]:.0f}}<extra></extra>"
    }}], {{
      ...baseLayout,
      geo: {{
        bgcolor: "rgba(0,0,0,0)",
        showframe: false,
        showcoastlines: false,
        projection: {{ type: "natural earth" }}
      }},
      margin: {{ t: 10, r: 0, b: 0, l: 0 }}
    }}, {{ responsive: true }});

    Plotly.newPlot("top-cases", [{{
      type: "bar",
      x: payload.top_cases.map(d => d.total_cases),
      y: payload.top_cases.map(d => d.location),
      orientation: "h",
      marker: {{ color: "#38bdf8" }},
      hovertemplate: "%{{y}}<br>Total cases: %{{x:,}}<extra></extra>"
    }}], {{
      ...baseLayout,
      xaxis: {{ title: "Total cases", gridcolor: "rgba(148,163,184,0.12)" }},
      yaxis: {{ automargin: true }},
      margin: {{ t: 10, r: 20, b: 50, l: 120 }}
    }}, {{ responsive: true }});

    Plotly.newPlot("vaccinations", [{{
      type: "bar",
      x: payload.vaccination_leaders.map(d => d.location),
      y: payload.vaccination_leaders.map(d => d.people_fully_vaccinated_per_hundred),
      marker: {{ color: "#22c55e" }},
      hovertemplate: "%{{x}}<br>Fully vaccinated per hundred: %{{y:.1f}}<extra></extra>"
    }}], {{
      ...baseLayout,
      xaxis: {{ tickangle: -35 }},
      yaxis: {{ title: "Fully vaccinated per 100", gridcolor: "rgba(148,163,184,0.12)" }}
    }}, {{ responsive: true }});

    const groupedTrend = payload.trend.reduce((acc, item) => {{
      acc[item.location] = acc[item.location] || [];
      acc[item.location].push(item);
      return acc;
    }}, {{}});
    const trendTraces = Object.entries(groupedTrend).map(([country, rows]) => ({{
      type: "scatter",
      mode: "lines",
      name: country,
      x: rows.map(r => r.date),
      y: rows.map(r => r.new_cases_7d_avg),
      hovertemplate: `${{country}}<br>%{{x}}<br>7-day average new cases: %{{y:.0f}}<extra></extra>`
    }}));
    Plotly.newPlot("trend", trendTraces, {{
      ...baseLayout,
      xaxis: {{ title: "Date" }},
      yaxis: {{ title: "7-day average new cases", gridcolor: "rgba(148,163,184,0.12)" }}
    }}, {{ responsive: true }});

    Plotly.newPlot("scatter", [{{
      type: "scatter",
      mode: "markers",
      x: payload.scatter.map(d => d.total_cases_per_million),
      y: payload.scatter.map(d => d.total_deaths_per_million),
      text: payload.scatter.map(d => d.location),
      customdata: payload.scatter.map(d => [d.continent, d.people_fully_vaccinated_per_hundred]),
      marker: {{
        size: payload.scatter.map(d => Math.max(10, Math.sqrt(d.population / 1000000) * 4)),
        color: payload.scatter.map(d => d.people_fully_vaccinated_per_hundred),
        colorscale: "Viridis",
        line: {{ color: "rgba(255,255,255,0.18)", width: 1 }},
        opacity: 0.82,
        colorbar: {{ title: "Fully vaccinated / 100" }}
      }},
      hovertemplate: "<b>%{{text}}</b><br>Continent: %{{customdata[0]}}<br>Cases per million: %{{x:.0f}}<br>Deaths per million: %{{y:.0f}}<br>Fully vaccinated / 100: %{{customdata[1]:.1f}}<extra></extra>"
    }}], {{
      ...baseLayout,
      xaxis: {{ title: "Cases per million", gridcolor: "rgba(148,163,184,0.12)" }},
      yaxis: {{ title: "Deaths per million", gridcolor: "rgba(148,163,184,0.12)" }}
    }}, {{ responsive: true }});
  </script>
</body>
</html>"""


def main() -> None:
    payload = build_payload()
    OUTPUT_FILE.write_text(render_dashboard(payload), encoding="utf-8")
    print(f"Saved advanced dashboard to {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
