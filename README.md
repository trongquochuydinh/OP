# Automatic plotting of selected data

## Tech stack

  - Python
  - Flask
  - Plotly
  - pywebview (desktop shell)

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
