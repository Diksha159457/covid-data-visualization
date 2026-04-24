from pathlib import Path

import folium
import pandas as pd


DATA_URL = "https://raw.githubusercontent.com/datasets/covid-19/main/data/countries-aggregated.csv"
OUTPUT_FILE = Path("covid_world_map.html")
COUNTRY_COORDS = {
    "India": (20.5937, 78.9629),
    "US": (37.0902, -95.7129),
    "Brazil": (-14.2350, -51.9253),
    "France": (46.2276, 2.2137),
    "United Kingdom": (55.3781, -3.4360),
}


def load_latest_data() -> pd.DataFrame:
    dataset = pd.read_csv(DATA_URL)
    latest_date = dataset["Date"].max()
    latest = dataset.loc[dataset["Date"] == latest_date].copy()
    latest["latitude"] = latest["Country"].map(lambda name: COUNTRY_COORDS.get(name, (None, None))[0])
    latest["longitude"] = latest["Country"].map(lambda name: COUNTRY_COORDS.get(name, (None, None))[1])
    return latest.dropna(subset=["latitude", "longitude"])


def build_map(rows: pd.DataFrame) -> folium.Map:
    world_map = folium.Map(location=[20, 0], zoom_start=2, tiles="OpenStreetMap")

    for _, row in rows.iterrows():
        radius = max(6, min(20, row["Confirmed"] / 1_000_000))
        popup = (
            f"<b>{row['Country']}</b><br>"
            f"Confirmed: {int(row['Confirmed']):,}<br>"
            f"Recovered: {int(row['Recovered']):,}<br>"
            f"Deaths: {int(row['Deaths']):,}"
        )
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=radius,
            color="#c2410c",
            fill=True,
            fill_color="#fb923c",
            fill_opacity=0.75,
            popup=folium.Popup(popup, max_width=260),
        ).add_to(world_map)

    return world_map


def main() -> None:
    latest_rows = load_latest_data()
    world_map = build_map(latest_rows)
    world_map.save(OUTPUT_FILE)
    print(f"Saved interactive map to {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
