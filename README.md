# COVID-19 Global Data Visualization

A small data visualization project that turns public COVID-19 country-level data into an interactive world map. The repository includes a Jupyter notebook for exploration, a Python script for map generation, and an exported HTML dashboard for quick viewing.

## Highlights

- Loads public COVID-19 country data
- Filters to the latest available reporting date
- Plots selected countries on an interactive Folium map
- Exports the finished visualization as a standalone HTML file

## Tech Stack

- Python
- Pandas
- Folium
- Jupyter Notebook

## Project Files

```text
covid-data-visualization/
├── covid_project.ipynb
├── script.py
├── covid_world_map.html
├── requirements.txt
└── README.md
```

## Run Locally

```bash
git clone https://github.com/Diksha159457/covid-data-visualization.git
cd covid-data-visualization
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python script.py
```

The script regenerates `covid_world_map.html` using the latest dataset available from the source URL.

## Deployment

This repository includes a GitHub Pages workflow in `.github/workflows/deploy-pages.yml`.

- On every push to `main`, GitHub Actions publishes `covid_world_map.html` as a static site.
- After GitHub Pages is enabled for the repository, the public URL should be:
  `https://diksha159457.github.io/covid-data-visualization/`

## Resume Value

This project demonstrates data wrangling, basic geospatial visualization, and exporting analysis results into a shareable interactive HTML artifact.

## Future Improvements

- Plot a larger country set with geocoded coordinates
- Add choropleth layers and time-based trend views
- Deploy the generated map as a hosted static page

## License

MIT. See [LICENSE](LICENSE).
