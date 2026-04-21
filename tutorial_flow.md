# Data Plotter User Flow Tutorial

## 1) Select the Data Source

In **Step 1: Select Data Source and Range**, load your data using one of these options:

- Use **Select File(s)** to upload `.xlsx` or `.yml` files.
- Use **Source path** + **Load Path Source** to load a local file path directly.
- In desktop mode, use **Desktop: Select Files** or **Browse**.

After loading:

- Choose the correct item in **Active source**.
- If the source is Excel, choose a sheet in **Sheet** and click **Load selected sheet**.

## 2) Define the Range (Excel Sources)

For `.xlsx` sources, enter an Excel range in **Excel Range**:

- `A2:C20` for a rectangular subset
- `A:C` for full column span
- `B,D` for non-adjacent columns

Then:

- Click **Preview Range** to inspect the selected data.
- Click **Apply Range** once correct.

Note: Non-Excel sources do not require range selection.

## 3) Configure Chart Settings

In **Step 2: Configure and Build Charts**:

- Select a chart type.
- Enter a chart title.
- Enter a **Chart key** (used for DOCX placeholder replacement), for example: `revenue_by_region`.
- Optional: enable **Use custom column labels** and edit labels.

## 4) Generate and Save Chart Presets

- Click **Generate plot** to preview the chart.
- Click **Save chart to template** to add it to template state.
- Use **Update selected preset** to overwrite an existing preset.
- Use **Render saved charts** to render all saved presets.
- Reorder presets with **Move up** / **Move down**.
- Remove a preset with **Remove preset**.

## 5) Save and Reload a Template

In **Step 3: Save Template and Generate Report**:

- Enter a value in **Template name**.
- Click **Save Template**.

To continue later:

- Select the template from the list.
- Click **Load Template** to restore sources and chart presets.

## 6) Insert Charts into a DOCX Report

Still in **Step 3**:

- Provide the Word template via:
  - file upload (`.docx`), or
  - template path input, or
  - **Browse DOCX** in desktop mode.
- Optionally set an output filename.
- Click **Generate DOCX report**.

The application replaces placeholders based on chart keys and writes an output `.docx`.

## Placeholder Rules

- Ensure DOCX placeholders match chart keys exactly (same spelling and case).
- If a key does not match, the chart is not inserted.

## Recommended Best Practices

- Prefer desktop absolute paths for reliable template restore.
- Set chart keys early and keep them stable.
- Preview/apply Excel ranges before saving chart presets.
- Save templates after major updates.
- If restore warnings appear, verify source files still exist at the saved paths.
