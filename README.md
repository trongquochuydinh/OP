# Automatic plotting of selected data

## Tech stack

  - Python
  - Flask
  - Plotly
  - pywebview (desktop shell)

## Features

- Load data from Excel (`.xlsx`) files
- Configure and preview Plotly charts (line, bar, stacked bar, pie, horizontal clustered bar, dumbbell)
- Per-preset appearance controls: font size, title visibility, legend position, point markers, per-series color/line style
- Count row occurrences mode for categorical combination charts
- Save named chart presets with a unique key; reorder and manage them in session
- Save and reload full report configurations (sources + chart presets) as JSON
- Generate Word (`.docx`) reports by replacing `{{CHART:key}}` placeholders with exported chart images
- Control the output location via the output name/path field (plain name saves next to template; full path saves at that location)

## Run (web) - deprecated

```bash
pip install -r requirements.txt
python main.py
```

## Run (desktop wrapper)

```bash
pip install -r requirements.txt
python desktop_app.py
```

The desktop app starts the same Flask backend locally and opens it in a native window.
All existing web functionality is preserved, plus native file pickers in desktop mode.
