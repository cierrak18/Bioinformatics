Air × Microbiome Explorer (Genus/Raw)

Interactive Shiny app for exploring air-pollution vs. nasal microbiome data.
This version supports genus-level filtering, an “All genera” view, heatmaps, and a full correlation panel (Pearson/Spearman/Kendall) with optional log scales and per-genus trend lines.

README:
----------------------------------------------------------

What’s new in this script?
- Basemap renders immediately (even before loading data).
- Works with your current combined.csv schema (year-based; lat/lon).
- Genus filter with an “All genera” option.
- Map points colored by pollutant category or by pollutant/microbiome value.
- Optional heatmap layers for pollutant and microbiome intensity.
- Correlation panel:
	- Scatter of concentration_ppm (x) vs chosen microbiome metric (y).
	- Methods: pearson, spearman, kendall with N, r, p readout.
	- Log10 toggles for x and y.
	- When “All genera” is selected: points auto-color by genus and show per-genus regression lines, plus an overall trend line.
	- Per-year correlation table for the current filters.

-----------------------------------------------------------
Data expected (combined.csv)

Required columns (case-sensitive except Genus is also accepted and normalized):
- city (chr)
- year (int) — used for the time slider
- genus (chr) — or Genus (will be renamed internally)
- pollutant (chr)
- concentration_ppm (num)
- lat, lon (num)

Numeric microbiome columns (choose one in the UI):
- rel_pct_abund, count, total_count_run

**If any required column is missing, the app will stop with a clear error message.**

-----------------------------------------------------------
Before you run:
1. Install R packages (once):
	install.packages(c("shiny","leaflet","leaflet.extras","dplyr","readr","DT","plotly"))
2. Place app.R and (optionally) combined.csv in the same folder.
3. (Optional) Prepare/refresh combined.csv using your pipeline. Make sure the columns above exist and lat/lon are numeric.

----------------------------------------------------------
Run the app
From R in the directory containing app.R:
	setwd("path/to/your/folder")  # if needed
	shiny::runApp() # or shiny::runApp("map_app.R")

- If no file is uploaded via the sidebar, the app will try to load the local combined.csv.
- You can also click Browse… to load a different CSV with the same schema.

-----------------------------------------------------------
Using the app
- Sidebar (left)
	- Pollutant metric: currently concentration_ppm.
	- Microbiome metric (numeric): choose one of rel_pct_abund, count, total_count_run.
	- Genus (filter):
	- Pick a single genus or choose All genera to see everything.
	- Year range: slide to restrict the time window.
	- Point size / opacity: tune map markers.
	- Heatmaps: enable pollutant and/or microbiome intensity heatmaps; adjust radius.
	- Color mode (map points):
	- Pollutant categories (discrete palette by pollutant)
	- Pollutant value (numeric ramp by concentration_ppm)
	- Microbiome value (numeric ramp by chosen microbiome metric)
	- Correlation controls:
	- Method: pearson | spearman | kendall
	- Log10 toggles for the x (pollutant) and y (microbiome) axes

- Main panel (right)
	- Map: circles + optional heatmaps. View auto-fits to visible points.
	- Correlation:
		- Scatter of pollutant vs microbiome metric for your filters.
		- All genera selected: points colored by genus, per-genus trend lines, plus an overall trend line.
		- Single genus selected: single-color scatter + overall trend line.
		- Stats box: N, r, and p for the current view.
	- Per-year correlations: N and r by year (under current filters).
	- Data: the filtered rows shown in the map/plots.

-----------------------------------------------------------
Tips & common questions

Nothing on the map?
- Check that lat and lon are present and numeric.
- Verify your year slider isn’t excluding all rows.
- If you uploaded a CSV, confirm its column names match the schema.

“All genera” colors the scatter by genus but I want one color:
- Select a specific Genus instead of All genera.

Flat trend line / weird r value:
- Try log10 on x and/or y (especially if values span orders of magnitude), or switch correlation method (Spearman/Kendall handle monotonic but non-linear patterns better).

Focus on a single city or pollutant:
- Use the Data table’s built-in search to subset (e.g., type a city name).
- You can also pre-filter your CSV upstream for more speed.

Performance with big files:
- Start with a narrower year range.
- Turn off one or both heatmaps.
- Use Pollutant categories color mode to skip numeric color scaling.

Wrong capitalization (Genus vs genus):
- The app auto-renames Genus → genus internally.

Switching metrics quickly:
- The correlation and map update live. If you change Microbiome metric, both the marker labels and heatmap intensity (when enabled) follow that choice.

-----------------------------------------------------------
File list (example)

- map_app.R — the Shiny app described above  
- combined.csv — your analysis-ready file the app will auto-load if present  
- README.md — this file

