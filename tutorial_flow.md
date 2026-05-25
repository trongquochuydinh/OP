# Data Plotter User Flow Tutorial

## 1) Select the Data Source

In **Step 1: Select Data Source and Range**, load your data using one of these options:

- Type the file path in **Source path** and press Enter (or tab away) to auto-load it.
- In desktop mode, use **Desktop: Select Files** to open a native file picker.

After loading:

- Choose the correct item in **Active source**.
- If the source is Excel, select a sheet in the **Sheet** dropdown — it loads automatically on selection.

## 2) Define the Range (Excel Sources)

For `.xlsx` sources, enter an Excel range in **Excel Range**:

- `A2:C20` for a rectangular subset
- `A:C` for full column span
- `B,D` for non-adjacent columns

Then:

- Click **Preview Range** to inspect the selected data.
- Click **Apply Range** once correct.

## 3) Configure Chart Settings

In **Step 2: Configure and Build Charts**:

- Select a chart type.
- Optional: enable **Count row occurrences** to count distinct value combinations instead of plotting raw values (requires 2+ columns; enabled automatically when columns are resolved).
- Enter a chart title.
- Enter a **Chart key** — this is both the unique preset identifier and the DOCX placeholder key, for example: `revenue_by_region`. Each key must be unique across all presets.

Under **Chart appearance**:

- **Font size** — controls the size of all chart labels and axis text (default: 12).
- **Show chart title** — toggle the chart title on/off.
- **Show legend** + **Legend position** — toggle the legend and set its placement.
- **Show point markers** — add dot markers on line and dumbbell charts.
- **Series styling** — per-series color, line width, and dash style (appears after columns are resolved; applies to line charts and dumbbell endpoints).

To rename columns: after clicking **Preview Range**, edit the column name directly in the preview table header row.

## 4) Generate and Save Chart Presets

The preset dropdown (with **Move up**, **Move down**, **Remove preset**) appears above the action buttons. Select a preset from the dropdown to load it into the form before generating or updating.

- Click **Generate plot** to preview the chart.
- Click **Save chart preset** to add the current configuration as a new preset.
- Use **Update selected preset** to overwrite the currently selected preset.
- Use **Render saved charts** to render all saved presets below the form.
- Reorder presets with **Move up** / **Move down**.
- Remove a preset with **Remove preset**.

## 5) Save and Reload a Configuration

In **Step 3: Save Report Configuration and Generate Report**:

- Enter a value in **Configuration name**.
- Click **Save configuration**.

To continue later:

- Select the configuration from the list.
- Click **Load configuration** to restore sources and chart presets.

To update existing configurations:

- Ensure that the configuration name matches the configuration that is to be updated
- Click **Save configuration**.

## 6) Insert Charts into a DOCX Report

Still in **Step 3**:

- Provide the Word template via:
  - file upload (`.docx`), or
  - template path input, or
  - **Browse DOCX** in desktop mode.
- Optionally set an output path or name:
  - Plain name (e.g. `final_report`) — saved next to the template DOCX with that filename.
  - Full path (e.g. `/Users/foo/reports/final_report.docx`) — saved at exactly that location.
  - Leave blank — auto-generated name saved next to the template DOCX.
- Click **Generate DOCX report**.

The application replaces placeholders based on chart keys and writes an output `.docx`.

## Placeholder Rules

- The placeholder format is `{{CHART:key}}` — for example, `{{CHART:revenue_by_region}}`.
- Ensure DOCX placeholders match chart keys exactly (same spelling and case).
- If a key does not match, the chart is not inserted.

## Recommended Best Practices

- Prefer desktop absolute paths for reliable template restore.
- Set chart keys early and keep them stable.
- Preview/apply Excel ranges before saving chart presets.
- Save templates after major updates.
- If restore warnings appear, verify source files still exist at the saved paths.
