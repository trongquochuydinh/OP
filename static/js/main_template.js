let sourceState = { active_source_id: null, sources: [] };
let chartState = { active_chart_id: null, charts: [] };
let columnContext = { source_id: null, range: null, columns: [], pie_style: null };
/** Display labels from loaded presets or preview header edits (parallel to columnContext.columns). */
let pendingColumnLabels = [];
let lastLoadedSourcePath = '';
let isSyncingSourcePathInput = false;
let isAutoLoadingSheet = false;

function setSourceStatus(message) {
    const statusEl = $('#sourceStatus');
    if (statusEl.length > 0) {
        statusEl.text(message || '');
        return;
    }
    if (message) {
        $('#rangeInfo').text(message);
    }
}

function updateCountsModeAvailability() {
    const cols = columnContext.columns || [];
    const ok = cols.length >= 2;
    $('#countsModeCheckbox').prop('disabled', !ok);
    if (!ok && $('#countsModeCheckbox').is(':checked')) {
        $('#countsModeCheckbox').prop('checked', false);
    }
}

function updateChartActionAvailability() {
    const source = getSelectedSource();
    const hasSource = !!source;
    const requiresRange = hasSource && source.file_type === 'xlsx';
    const hasRange = !requiresRange || !!$('#excelRangeInput').val().trim();
    const canUseChartActions = hasSource && hasRange;

    $('.generate-plot').prop('disabled', !canUseChartActions);
    $('#addChartBtn').prop('disabled', !canUseChartActions);
    $('#updateChartBtn').prop('disabled', !canUseChartActions || !$('#chartPresetList').val());
    updateCountsModeAvailability();
}

function isDesktopBridgeAvailable() {
    return !!(window.pywebview && window.pywebview.api);
}

function updateDesktopControlsVisibility() {
    const visible = isDesktopBridgeAvailable();
    $('.desktop-only').toggle(visible);
}

window.addEventListener('pywebviewready', function () {
    updateDesktopControlsVisibility();
});

$(document).ready(function () {
    $('#sourcePathInput').on('change', function () {
        loadSourceFromPathInput();
    });
    $('#sourcePathInput').on('keydown', function (event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            loadSourceFromPathInput();
        }
    });

    $('#desktopSelectFilesBtn').on('click', function () {
        pickDesktopSourceFiles();
    });

    $('#sourceSelect').on('change', function () {
        sourceState.active_source_id = $(this).val() || null;
        syncSourceUI();
    });

    $('#sheetSelect').on('change', function () {
        if (!isAutoLoadingSheet) {
            loadSelectedSheetForSource();
        }
    });

    $('#chartPresetList').on('change', function () {
        loadSelectedChartPresetIntoForm();
    });

    $('#chartTypeInput').on('change', function () {
        syncPlotStyleFieldVisibility();
        const captured = captureSeriesStyleFromDom();
        refreshSeriesStyleRows({
            initialSeries: fitSeriesInitial(captured, getSeriesStyleSlotCount(), DEFAULT_SERIES_COLORS)
        });
    });

    $('#countsModeCheckbox').on('change', function () {
        const captured = captureSeriesStyleFromDom();
        refreshSeriesStyleRows({
            initialSeries: fitSeriesInitial(captured, getSeriesStyleSlotCount(), DEFAULT_SERIES_COLORS)
        });
    });

    $(document).on('input', '#rangePreview .preview-col-header', function () {
        const cols = columnContext.columns || [];
        if (!cols.length) return;
        const idx = Number($(this).attr('data-col-index'));
        if (Number.isNaN(idx) || idx < 0 || idx >= cols.length) return;
        if (pendingColumnLabels.length !== cols.length) {
            pendingColumnLabels = cols.map((c, i) => {
                const inp = $(`#rangePreview .preview-col-header[data-col-index="${i}"]`);
                return inp.length ? inp.val().trim() || String(c) : String(c);
            });
        }
        pendingColumnLabels[idx] = $(this).val().trim() || String(cols[idx]);
        const captured = captureSeriesStyleFromDom();
        refreshSeriesStyleRows({
            initialSeries: fitSeriesInitial(captured, getSeriesStyleSlotCount(), DEFAULT_SERIES_COLORS)
        });
    });

    $('#excelRangeInput').on('input', function () {
        updateChartActionAvailability();
    });

    $('.generate-plot').on('click', function () {
        generatePlotRequest();
    });

    $('#previewRangeBtn').on('click', function () {
        previewExcelRange();
    });

    $('#applyRangeBtn').on('click', function () {
        applyExcelRange();
    });

    $('#saveTemplateBtn').on('click', function () {
        saveTemplate();
    });

    $('#loadTemplateBtn').on('click', function () {
        loadTemplate();
    });
    $('#resetWorkspaceBtn').on('click', function () {
        resetWorkspace();
    });

    $('#addChartBtn').on('click', function () {
        addChartPreset();
    });

    $('#updateChartBtn').on('click', function () {
        updateSelectedChartPreset();
    });

    $('#renderChartsBtn').on('click', function () {
        renderSavedCharts();
    });

    $('#removeChartBtn').on('click', function () {
        removeSelectedChartPreset();
    });

    $('#moveChartUpBtn').on('click', function () {
        moveSelectedChartPreset(-1);
    });

    $('#moveChartDownBtn').on('click', function () {
        moveSelectedChartPreset(1);
    });

    $('#generateDocxBtn').on('click', function () {
        generateDocxReport();
    });

    $('#desktopBrowseDocxBtn').on('click', function () {
        browseDesktopDocxTemplate();
    });

    updateDesktopControlsVisibility();
    refreshTemplateList();
    refreshSources();
    refreshChartPresetList();
    syncPlotStyleFieldVisibility();
    refreshSeriesStyleRows();
    updateChartActionAvailability();
});

function getSelectedSource() {
    const sourceId = sourceState.active_source_id || $('#sourceSelect').val();
    if (!sourceId) return null;
    return sourceState.sources.find((source) => source.source_id === sourceId) || null;
}

function sourceLabel(source) {
    const name = source.file_name || source.path_value || source.source_path_relative || source.source_path || source.source_id;
    const sheetSuffix = source.sheet_name ? ` :: ${source.sheet_name}` : '';
    const pathSuffix = source.path_mode && source.path_value ? ` | ${source.path_mode}:${source.path_value}` : '';
    return `${name}${sheetSuffix} [${source.file_type}]${pathSuffix}`;
}

function syncSourceUI() {
    const source = getSelectedSource();
    if (!source) {
        $('#excelRangeDiv').hide();
        $('#sheetControls').hide();
        setColumnContext(null, null, [], null);
        setSourceStatus('Load a source to start charting.');
        updateChartActionAvailability();
        return;
    }

    const pathValue = source.source_path || source.source_path_relative || '';
    isSyncingSourcePathInput = true;
    $('#sourcePathInput').val(pathValue);
    isSyncingSourcePathInput = false;

    if (source.file_type === 'xlsx') {
        $('#sheetControls').show();
        const sheetSelect = $('#sheetSelect');
        sheetSelect.empty();
        const sheets = Array.isArray(source.available_sheets) ? source.available_sheets : [];
        sheets.forEach((sheetName) => {
            sheetSelect.append($('<option>').val(sheetName).text(sheetName));
        });
        if (source.sheet_name) {
            isAutoLoadingSheet = true;
            sheetSelect.val(source.sheet_name);
            isAutoLoadingSheet = false;
        }

        $('#excelRangeDiv').show();
        if (source.total_rows && source.total_cols) {
            $('#rangeInfo').text(`File dimensions: ${source.total_rows} rows x ${source.total_cols} columns`);
        }
        setColumnContext(source.source_id, null, [], null);
        setSourceStatus('Excel source loaded. Select range before generating or saving charts.');
    } else {
        $('#sheetControls').hide();
        $('#excelRangeDiv').hide();
        setColumnContext(source.source_id, null, source.columns || [], null);
        setSourceStatus('Source loaded. Configure chart settings and generate.');
    }
    updateChartActionAvailability();
}

function columnsAligned(prevCols, newCols) {
    const a = Array.isArray(prevCols) ? prevCols : [];
    const b = Array.isArray(newCols) ? newCols : [];
    if (a.length !== b.length) return false;
    return a.every((v, i) => String(v) === String(b[i]));
}

function setColumnContext(sourceId, rangeValue, columns, pieStyle) {
    const cols = Array.isArray(columns) ? columns : [];
    const prevCols = columnContext.columns || [];
    const colsUnchanged = columnsAligned(prevCols, cols);
    const pie = pieStyle != null && typeof pieStyle === 'object' ? pieStyle : null;
    const prevPie = columnContext.pie_style || null;
    const pieUnchanged = JSON.stringify(prevPie || {}) === JSON.stringify(pie || {});

    if (!colsUnchanged) {
        pendingColumnLabels = [];
    }
    columnContext = {
        source_id: sourceId,
        range: rangeValue,
        columns: cols,
        pie_style: pie
    };
    if (!colsUnchanged || !pieUnchanged) {
        refreshSeriesStyleRows();
    }
    /* When columns are unchanged (e.g. Generate re-resolves the same range), skip rebuilding
       series rows — refreshSeriesStyleRows() would reset color pickers to defaults. */
}

/** Restore labels from a loaded preset when they match the current column list. */
function applyLoadedColumnLabels(labels) {
    const normalized = Array.isArray(labels) ? labels.map((x) => String(x)) : [];
    const cols = columnContext.columns || [];
    pendingColumnLabels = normalized.length === cols.length ? normalized : [];
}

function normalizeChartKey(rawValue) {
    return String(rawValue || '')
        .trim()
        .replace(/[^a-zA-Z0-9_-]/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_+|_+$/g, '');
}

function deriveChartKeyFallback() {
    const title = $('#plotTitleInput').val().trim();
    const chartType = $('#chartTypeInput').val();
    const base = normalizeChartKey(title) || normalizeChartKey(chartType) || 'chart';
    return base;
}

function getActiveChartPreset() {
    const chartId = $('#chartPresetList').val();
    if (!chartId) return null;
    return (chartState.charts || []).find((item) => item.id === chartId) || null;
}

const DEFAULT_SERIES_COLORS = [
    '#636EFA',
    '#EF553B',
    '#00CC96',
    '#AB63FA',
    '#FFA15A',
    '#19D3F3',
    '#FF6692',
    '#B6E880',
    '#FF97FF',
    '#FECB52'
];

const MAX_PIE_STYLE_SLICES = 100;

function getPieStyleSliceCount() {
    const ps = columnContext.pie_style;
    if (!ps || typeof ps.slice_count !== 'number' || ps.slice_count <= 0) return 0;
    return Math.min(ps.slice_count, MAX_PIE_STYLE_SLICES);
}

function normalizeHexColorInput(hex) {
    if (!hex || typeof hex !== 'string') return DEFAULT_SERIES_COLORS[0];
    let h = hex.trim();
    if (!h.startsWith('#')) h = `#${h}`;
    if (/^#[0-9A-Fa-f]{6}$/.test(h)) return h;
    if (/^#[0-9A-Fa-f]{3}$/.test(h)) {
        const r = h[1];
        const g = h[2];
        const b = h[3];
        return `#${r}${r}${g}${g}${b}${b}`;
    }
    return DEFAULT_SERIES_COLORS[0];
}

function resolveColumnDisplayLabel(columns, idx) {
    const cols = Array.isArray(columns) ? columns : [];
    const colName = cols[idx];
    if (colName === undefined) return '';
    const previewInp = $(`#rangePreview .preview-col-header[data-col-index="${idx}"]`);
    if (previewInp.length) {
        const v = previewInp.val().trim();
        return v || String(colName);
    }
    if (pendingColumnLabels.length === cols.length && pendingColumnLabels[idx] !== undefined) {
        const v = String(pendingColumnLabels[idx]).trim();
        return v || String(colName);
    }
    return String(colName);
}

function getSeriesStyleSlotCount() {
    const ct = $('#chartTypeInput').val();
    if (ct === 'dumbbellchart') return 2;
    if (ct === 'piechart') {
        const n = getPieStyleSliceCount();
        return n > 0 ? n : 1;
    }
    const cols = columnContext.columns || [];
    /* Two columns + counts = joint combo chart → single trace "count". Three or more + counts = one trace per column after the first. */
    if ($('#countsModeCheckbox').is(':checked') && cols.length === 2) {
        return 1;
    }
    if (cols.length <= 1) return 1;
    if (cols.length === 2) return 1;
    return cols.length - 1;
}

function getSeriesStyleLabels() {
    const ct = $('#chartTypeInput').val();
    if (ct === 'dumbbellchart') return ['Low endpoints', 'High endpoints'];
    if (ct === 'piechart') {
        const n = getSeriesStyleSlotCount();
        const ps = columnContext.pie_style;
        const labels = ps && Array.isArray(ps.slice_labels) ? ps.slice_labels : [];
        const out = [];
        for (let i = 0; i < n; i++) {
            if (labels[i] !== undefined && String(labels[i]).trim() !== '') {
                out.push(String(labels[i]));
            } else {
                out.push(`Slice ${i + 1}`);
            }
        }
        return out;
    }
    const cols = columnContext.columns || [];
    if ($('#countsModeCheckbox').is(':checked') && cols.length === 2) {
        return ['Counts'];
    }
    if (cols.length <= 1) return ['Series'];
    if (cols.length === 2) return [`Series (${resolveColumnDisplayLabel(cols, 1)})`];
    return cols.slice(1).map((_, j) => resolveColumnDisplayLabel(cols, j + 1));
}

function seriesUsesLineWidthDashUi() {
    const ct = $('#chartTypeInput').val();
    return ct === 'linechart' || ct === 'dumbbellchart';
}

function fitSeriesInitial(prevArr, n, palette) {
    const prev = Array.isArray(prevArr) ? prevArr : [];
    const pal = palette || DEFAULT_SERIES_COLORS;
    const out = [];
    for (let i = 0; i < n; i++) {
        const p = prev[i];
        if (p && typeof p === 'object') {
            const dash = p.line_dash != null ? String(p.line_dash) : 'solid';
            out.push({
                color: p.color || pal[i % pal.length],
                line_width: p.line_width,
                line_dash: dash
            });
        } else {
            out.push({ color: pal[i % pal.length], line_dash: 'solid' });
        }
    }
    return out;
}

function inputValTrimmed($ctx, selector) {
    const v = $ctx.find(selector).val();
    return String(v == null ? '' : v).trim();
}

function captureSeriesStyleFromDom() {
    const arr = [];
    const lineUi = seriesUsesLineWidthDashUi();
    $('#seriesStyleRows .series-style-row').each(function () {
        const $row = $(this);
        const row = { color: $row.find('.series-color').val() };
        if (lineUi) {
            const widthRaw = inputValTrimmed($row, '.series-line-width');
            if (widthRaw !== '') {
                const num = Number(widthRaw);
                if (!Number.isNaN(num) && num > 0) row.line_width = num;
            }
            row.line_dash = $row.find('.series-line-dash').val() || 'solid';
        }
        arr.push(row);
    });
    return arr;
}

function buildSeriesFromStyle(styleObj) {
    const n = getSeriesStyleSlotCount();
    const series = Array.isArray(styleObj.series) ? styleObj.series : [];
    const legacy = Array.isArray(styleObj.colors) ? styleObj.colors : [];
    const merged = [];
    for (let i = 0; i < n; i++) {
        const base = { ...(series[i] || {}) };
        if (!base.color && legacy[i]) base.color = legacy[i];
        merged.push(base);
    }
    return fitSeriesInitial(merged, n, DEFAULT_SERIES_COLORS);
}

function refreshSeriesStyleRows(opts = {}) {
    const container = $('#seriesStyleRows');
    if (!container.length) return;

    let initial = opts.initialSeries;
    const n = getSeriesStyleSlotCount();
    const labels = getSeriesStyleLabels();
    const palette = DEFAULT_SERIES_COLORS;

    if (!initial || !Array.isArray(initial)) {
        initial = fitSeriesInitial([], n, palette);
    } else {
        initial = fitSeriesInitial(initial, n, palette);
    }

    container.empty();

    if (n <= 0) {
        container.append(
            $('<div>').addClass('section-note').text('Select chart type and columns to style each series.')
        );
        return;
    }

    const lineUi = seriesUsesLineWidthDashUi();
    const chartType = $('#chartTypeInput').val() || '';
    let hint = '';
    if (chartType === 'piechart') {
        hint = 'Each row sets the color for one pie slice (same order as categories in your data).';
    } else if ((columnContext.columns || []).length >= 3) {
        hint = 'Each row matches one Y-series (columns after the first are separate lines/bars).';
    } else {
        hint = 'Single-series chart; one row applies to the plotted trace.';
    }
    if (!lineUi) {
        hint += ' Line width and dash apply only to line charts (and dumbbell).';
    }
    container.append($('<div>').addClass('section-note').css({ marginBottom: '8px' }).text(hint));

    for (let i = 0; i < n; i++) {
        const cfg = initial[i] || { color: palette[i % palette.length], line_dash: 'solid' };
        const row = $('<div>').addClass('series-style-row');
        row.append($('<span class="series-style-label">').text(labels[i] || `Series ${i + 1}`));
        row.append(
            $('<label class="series-style-field">')
                .append($('<span>').text('Color'))
                .append(
                    $('<input type="color">')
                        .addClass('series-color')
                        .val(normalizeHexColorInput(cfg.color))
                )
        );

        if (lineUi) {
            row.append(
                $('<label class="series-style-field">')
                    .append($('<span>').text('Line width'))
                    .append(
                        $('<input type="number">')
                            .addClass('series-line-width')
                            .attr({ min: '1', max: '12', step: '0.5', placeholder: 'default' })
                            .css({ width: '5rem' })
                            .val(cfg.line_width != null && cfg.line_width !== '' ? String(cfg.line_width) : '')
                    )
            );
            const dashSelect = $('<select>').addClass('series-line-dash');
            dashSelect.append(
                $('<option value="solid">').text('Solid'),
                $('<option value="dash">').text('Dashed'),
                $('<option value="dot">').text('Dotted'),
                $('<option value="dashdot">').text('Dash-dot')
            );
            dashSelect.val(cfg.line_dash || 'solid');
            row.append($('<label class="series-style-field">').append($('<span>').text('Line')).append(dashSelect));
        }

        container.append(row);
    }
}

function collectPlotStyle() {
    const style = {};
    if (!$('#plotTitleVisible').is(':checked')) {
        style.title_visible = false;
    }
    const legendVisible = $('#plotLegendVisible').is(':checked');
    const legendPosition = $('#plotLegendPosition').val() || 'default';
    style.legend = {
        visible: legendVisible,
        position: legendVisible ? legendPosition : 'default'
    };
    if ($('#plotMarkersRow').is(':visible') && $('#plotMarkersVisible').is(':checked')) {
        style.markers_visible = true;
    }

    const lineUi = seriesUsesLineWidthDashUi();
    const series = [];
    $('#seriesStyleRows .series-style-row').each(function () {
        const $row = $(this);
        const entry = {
            color: $row.find('.series-color').val()
        };
        if (lineUi) {
            const widthRaw = inputValTrimmed($row, '.series-line-width');
            if (widthRaw !== '') {
                const w = Number(widthRaw);
                if (!Number.isNaN(w) && w > 0) entry.line_width = w;
            }
            const dash = $row.find('.series-line-dash').val() || 'solid';
            if (dash !== 'solid') entry.line_dash = dash;
        }
        series.push(entry);
    });
    if (series.length) style.series = series;

    return style;
}

function syncPlotStyleForm(style) {
    const s = style && typeof style === 'object' ? style : {};
    $('#plotTitleVisible').prop('checked', s.title_visible !== false);
    const leg = s.legend || {};
    $('#plotLegendVisible').prop('checked', leg.visible !== false);
    $('#plotLegendPosition').val(leg.position || 'default');
    $('#plotMarkersVisible').prop('checked', s.markers_visible === true);
    syncPlotStyleFieldVisibility();
    refreshSeriesStyleRows({ initialSeries: buildSeriesFromStyle(s) });
}

function syncPlotStyleFieldVisibility() {
    const chartType = $('#chartTypeInput').val() || '';
    const markerFriendly = chartType === 'linechart' || chartType === 'dumbbellchart';
    $('#plotMarkersRow').toggle(markerFriendly);
}

function collectColumnLabelsForChart(columns) {
    const cols = Array.isArray(columns) ? columns : [];
    const defaults = cols.map((c) => String(c));
    const merged = cols.map((_, idx) => resolveColumnDisplayLabel(cols, idx));
    const sameAsDefault = merged.every((lbl, i) => lbl === defaults[i]);
    return sameAsDefault ? [] : merged;
}

async function resolveColumnsForChart(source, rangeValue, updatePreview) {
    if (source.file_type !== 'xlsx') {
        const cols = Array.isArray(source.columns) ? source.columns : [];
        setColumnContext(source.source_id, null, cols, null);
        updateChartActionAvailability();
        return cols;
    }

    if (!rangeValue) {
        throw new Error('Range is required for Excel charts');
    }

    const response = await fetch('/preview-range', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            source_id: source.source_id,
            range: rangeValue,
            max_rows: 500,
            max_cols: 50
        })
    });
    const result = await response.json();
    if (!response.ok || !result.success) {
        throw new Error(result.error || 'Range preview failed');
    }

    const cols = Array.isArray(result.excel_columns) ? result.excel_columns : [];
    setColumnContext(source.source_id, rangeValue, cols, result.pie_style || null);

    if (updatePreview) {
        const info = result.range_info || {};
        let msg = `Range ${info.display || rangeValue} → ${info.total_rows} rows × ${info.total_cols} columns`;
        const tr = result.truncation;
        if (tr && (tr.rows_truncated || tr.cols_truncated)) {
            msg += `. Preview grid ${tr.preview_rows}×${tr.preview_cols}`;
            if (tr.rows_truncated) msg += '; rows truncated';
            if (tr.cols_truncated) msg += '; columns truncated';
        }
        $('#rangeInfo').text(msg);
        renderRangePreview(result.preview, cols, tr);
    }

    updateChartActionAvailability();
    return cols;
}

async function refreshSources(selectedSourceId = null) {
    try {
        const response = await fetch('/sources');
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || 'Could not load sources');
        }

        sourceState = {
            active_source_id: result.active_source_id,
            sources: result.sources || []
        };

        const select = $('#sourceSelect');
        select.empty();
        if (sourceState.sources.length === 0) {
            select.append($('<option>').val('').text('No source loaded'));
            sourceState.active_source_id = null;
            syncSourceUI();
            return;
        }

        sourceState.sources.forEach((source) => {
            select.append($('<option>').val(source.source_id).text(sourceLabel(source)));
        });

        const target = selectedSourceId || sourceState.active_source_id || sourceState.sources[0].source_id;
        sourceState.active_source_id = target;
        select.val(target);
        syncSourceUI();
        setSourceStatus(`Loaded ${sourceState.sources.length} source(s).`);
    } catch (error) {
        console.error('Sources refresh error:', error);
        setSourceStatus(`Could not refresh sources: ${error.message}`);
    }
}

async function loadSourcePaths(paths) {
    const normalizedPaths = Array.isArray(paths) ? paths.filter(Boolean) : [];
    if (normalizedPaths.length === 0) {
        return;
    }

    const failures = [];
    let lastSourceId = null;

    for (const sourcePath of normalizedPaths) {
        try {
            const formData = new FormData();
            formData.append('source_path', sourcePath);
            const response = await fetch('/sources/load-path', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Could not load source path');
            }
            lastSourceId = result.source_id;
        } catch (error) {
            failures.push(`${sourcePath}: ${error.message}`);
        }
    }

    await refreshSources(lastSourceId);
    Plotly.purge('plot');
    if (lastSourceId && normalizedPaths.length > 0) {
        lastLoadedSourcePath = String(normalizedPaths[normalizedPaths.length - 1]).trim();
        setSourceStatus(`Loaded ${normalizedPaths.length} source path(s).`);
    }

    if (failures.length > 0) {
        alert(`Some sources failed to load:\n- ${failures.join('\n- ')}`);
    }
}

async function pickDesktopSourceFiles() {
    if (!isDesktopBridgeAvailable()) {
        alert('Desktop file picker is not available in browser mode.');
        return;
    }

    try {
        const pickedPaths = await window.pywebview.api.pick_source_files();
        await loadSourcePaths(pickedPaths || []);
        if (Array.isArray(pickedPaths) && pickedPaths.length > 0) {
            $('#sourcePathInput').val(pickedPaths[0]);
            setSourceStatus(`Desktop selected ${pickedPaths.length} file(s) and loaded them.`);
        }
    } catch (error) {
        console.error('Desktop source file picker error:', error);
        alert(`Desktop file picker failed: ${error.message}`);
    }
}

async function browseDesktopDocxTemplate() {
    if (!isDesktopBridgeAvailable()) {
        alert('Desktop DOCX picker is not available in browser mode.');
        return;
    }

    try {
        const docxPath = await window.pywebview.api.pick_docx_file();
        if (docxPath) {
            $('#docxTemplatePathInput').val(docxPath);
        }
    } catch (error) {
        console.error('Desktop DOCX picker error:', error);
        alert(`Desktop DOCX picker failed: ${error.message}`);
    }
}

async function loadSourceFromPathInput() {
    const sourcePath = $('#sourcePathInput').val().trim();
    if (isSyncingSourcePathInput) {
        return;
    }
    if (!sourcePath) {
        lastLoadedSourcePath = '';
        return;
    }
    if (sourcePath === lastLoadedSourcePath) {
        return;
    }

    try {
        const formData = new FormData();
        formData.append('source_path', sourcePath);
        const response = await fetch('/sources/load-path', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || 'Could not load path source');
        }
        await refreshSources(result.source_id);
        Plotly.purge('plot');
        lastLoadedSourcePath = sourcePath;
        setSourceStatus('Source path loaded successfully.');
    } catch (error) {
        console.error('Load path source error:', error);
        alert(`Load source failed: ${error.message}`);
    }
}

async function loadSelectedSheetForSource() {
    const source = getSelectedSource();
    if (!source || source.file_type !== 'xlsx') {
        alert('Select an Excel source first.');
        return;
    }

    const sheetName = $('#sheetSelect').val();
    if (!sheetName) {
        alert('Select a sheet first.');
        return;
    }

    try {
        const response = await fetch('/sources/select-sheet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_id: source.source_id, sheet_name: sheetName })
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || 'Could not load selected sheet');
        }

        await refreshSources(source.source_id);
        $('#rangeInfo').text(`Loaded sheet '${sheetName}'`);
        setSourceStatus(`Loaded sheet '${sheetName}'.`);
        Plotly.purge('plot');
    } catch (error) {
        console.error('Sheet load error:', error);
        alert(`Failed to load sheet: ${error.message}`);
    }
}

async function previewExcelRange() {
    const source = getSelectedSource();
    if (!source || source.file_type !== 'xlsx') {
        alert('Select an Excel source first.');
        return;
    }

    const range = $('#excelRangeInput').val().trim();
    if (!range) {
        $('#rangeInfo').text('Please enter a range (e.g., A2:N28)');
        return;
    }

    try {
        await resolveColumnsForChart(source, range, true);
    } catch (error) {
        console.error('Range preview error:', error);
        $('#rangeInfo').text(`Preview failed: ${error.message}`);
    }
}

async function applyExcelRange() {
    await previewExcelRange();
}

async function generatePlotRequest() {
    const source = getSelectedSource();
    if (!source) {
        alert('Load or select a data source first.');
        return;
    }

    const formData = new FormData();
    formData.append('source_id', source.source_id);
    formData.append('chart_type', $('#chartTypeInput').val());
    formData.append('title', $('#plotTitleInput').val());
    formData.append('chart_key', normalizeChartKey($('#chartKeyInput').val()) || deriveChartKeyFallback());

    let rangeValue = null;
    if (source.file_type === 'xlsx') {
        rangeValue = $('#excelRangeInput').val().trim();
        if (!rangeValue) {
            alert('Enter an Excel range for this chart.');
            return;
        }
        formData.append('range', rangeValue);
    }

    try {
        const columns = await resolveColumnsForChart(source, rangeValue, false);
        formData.append('columns', JSON.stringify(columns));
        formData.append('column_labels', JSON.stringify(collectColumnLabelsForChart(columns)));
        formData.append('plot_style', JSON.stringify(collectPlotStyle()));
        formData.append('counts_mode', $('#countsModeCheckbox').is(':checked') ? '1' : '0');

        const response = await fetch('/generate', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || 'Plot generation failed');
        }
        Plotly.newPlot('plot', result.traces, result.layout || {});
    } catch (error) {
        console.error('Generate plot error:', error);
        alert(`Plot generation failed: ${error.message}`);
    }
}

async function addChartPreset() {
    const source = getSelectedSource();
    if (!source) {
        alert('Load or select a data source first.');
        return;
    }

    const formData = new FormData();
    const normalizedKey = normalizeChartKey($('#chartKeyInput').val()) || deriveChartKeyFallback();
    formData.append('source_id', source.source_id);
    formData.append('chart_type', $('#chartTypeInput').val());
    formData.append('title', $('#plotTitleInput').val());
    formData.append('chart_key', normalizedKey);

    let rangeValue = null;
    if (source.file_type === 'xlsx') {
        rangeValue = $('#excelRangeInput').val().trim();
        if (!rangeValue) {
            alert('Enter a range before saving this chart preset.');
            return;
        }
        formData.append('range', rangeValue);
    }

    try {
        const columns = await resolveColumnsForChart(source, rangeValue, false);
        formData.append('columns', JSON.stringify(columns));
        formData.append('column_labels', JSON.stringify(collectColumnLabelsForChart(columns)));
        formData.append('plot_style', JSON.stringify(collectPlotStyle()));
        formData.append('counts_mode', $('#countsModeCheckbox').is(':checked') ? '1' : '0');

        const response = await fetch('/new_chart', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Could not save chart preset');
        }
        chartState = result.chart_state || chartState;
        await refreshChartPresetList(result.chart.id);
        await renderSavedCharts();
    } catch (error) {
        console.error('Add chart preset error:', error);
        alert(`Failed to save chart preset: ${error.message}`);
    }
}

async function updateSelectedChartPreset() {
    const chartId = $('#chartPresetList').val();
    if (!chartId) {
        alert('Select a preset to update first.');
        return;
    }

    const source = getSelectedSource();
    if (!source) {
        alert('Load or select a data source first.');
        return;
    }

    const formData = new FormData();
    const normalizedKey = normalizeChartKey($('#chartKeyInput').val()) || deriveChartKeyFallback();
    formData.append('chart_id', chartId);
    formData.append('source_id', source.source_id);
    formData.append('chart_type', $('#chartTypeInput').val());
    formData.append('title', $('#plotTitleInput').val());
    formData.append('chart_key', normalizedKey);

    let rangeValue = null;

    if (source.file_type === 'xlsx') {
        rangeValue = $('#excelRangeInput').val().trim();
        if (!rangeValue) {
            alert('Enter a range before updating this chart preset.');
            return;
        }
        formData.append('range', rangeValue);
    }

    try {
        const columns = await resolveColumnsForChart(source, rangeValue, false);
        formData.append('columns', JSON.stringify(columns));
        formData.append('column_labels', JSON.stringify(collectColumnLabelsForChart(columns)));
        formData.append('plot_style', JSON.stringify(collectPlotStyle()));
        formData.append('counts_mode', $('#countsModeCheckbox').is(':checked') ? '1' : '0');

        const response = await fetch('/new_chart', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Could not update chart preset');
        }

        chartState = result.chart_state || chartState;
        await refreshChartPresetList(chartId);
        await renderSavedCharts();
        updateChartActionAvailability();
        $('#templateInfo').text('Updated selected chart preset.');
    } catch (error) {
        console.error('Update chart preset error:', error);
        alert(`Failed to update chart preset: ${error.message}`);
    }
}

async function refreshChartPresetList(selectedChartId = null) {
    try {
        const response = await fetch('/charts');
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || 'Unable to fetch chart presets');
        }

        chartState = result.chart_state || { active_chart_id: null, charts: [] };
        const selector = $('#chartPresetList');
        selector.empty();

        const charts = chartState.charts || [];
        if (charts.length === 0) {
            selector.append($('<option>').val('').text('No chart presets'));
            updateChartActionAvailability();
            return;
        }

        charts.forEach((chart, index) => {
            const source = sourceState.sources.find((item) => item.source_id === chart.source_id);
            const base = chart.title && chart.title.trim() ? chart.title : `${chart.chart_type} #${index + 1}`;
            const suffix = source ? ` :: ${source.file_name || source.source_id}` : ` :: ${chart.source_id}`;
            const keyLabel = chart.chart_key ? ` [${chart.chart_key}]` : '';
            selector.append($('<option>').val(chart.id).text(`${base}${keyLabel}${suffix}`));
        });

        const target = selectedChartId || chartState.active_chart_id || charts[0].id;
        selector.val(target);
        updateChartActionAvailability();
    } catch (error) {
        console.error('Chart preset list error:', error);
    }
}

async function removeSelectedChartPreset() {
    const chartId = $('#chartPresetList').val();
    if (!chartId) return;

    try {
        const response = await fetch(`/charts/${encodeURIComponent(chartId)}`, { method: 'DELETE' });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Could not remove chart preset');
        }
        chartState = result.chart_state || { active_chart_id: null, charts: [] };
        await refreshChartPresetList();
        await renderSavedCharts();
        updateChartActionAvailability();
    } catch (error) {
        console.error('Remove chart preset error:', error);
        alert(`Failed to remove chart preset: ${error.message}`);
    }
}

async function moveSelectedChartPreset(step) {
    const chartId = $('#chartPresetList').val();
    const charts = (chartState && Array.isArray(chartState.charts)) ? chartState.charts : [];
    if (!chartId || charts.length < 2) return;

    const currentIndex = charts.findIndex((chart) => chart.id === chartId);
    if (currentIndex < 0) return;

    const targetIndex = Math.max(0, Math.min(currentIndex + step, charts.length - 1));
    if (targetIndex === currentIndex) return;

    try {
        const response = await fetch('/charts/reorder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chart_id: chartId, target_index: targetIndex })
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Could not reorder chart preset');
        }
        chartState = result.chart_state || { active_chart_id: null, charts: [] };
        await refreshChartPresetList(chartId);
        await renderSavedCharts();
        updateChartActionAvailability();
    } catch (error) {
        console.error('Reorder chart preset error:', error);
        alert(`Failed to reorder chart preset: ${error.message}`);
    }
}

async function renderSavedCharts() {
    try {
        const response = await fetch('/render_charts', { method: 'POST' });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || 'Could not render charts');
        }
        renderSavedChartsPanel(result.charts || []);
    } catch (error) {
        console.error('Render charts error:', error);
        $('#savedChartsContainer').html(`<div>Could not render charts: ${error.message}</div>`);
    }
}

function renderSavedChartsPanel(charts) {
    const container = $('#savedChartsContainer');
    container.empty();
    if (!charts || charts.length === 0) return;

    charts.forEach((chart, index) => {
        const source = sourceState.sources.find((item) => item.source_id === chart.source_id);
        const sourceText = source ? sourceLabel(source) : chart.source_id;

        const wrapper = $('<div>').css({ marginBottom: '20px', border: '1px solid #ddd', padding: '10px' });
        const title = chart.title && chart.title.trim() ? chart.title : `${chart.chart_type} #${index + 1}`;
        wrapper.append($('<div>').css({ fontWeight: 'bold', marginBottom: '4px' }).text(title));
        const keyText = chart.chart_key ? ` | Key: ${chart.chart_key}` : '';
        wrapper.append($('<div>').css({ color: '#666', marginBottom: '8px', fontSize: '0.9em' }).text(`Source: ${sourceText}${chart.range ? ` | Range: ${chart.range}` : ''}${keyText}`));

        if (chart.error) {
            wrapper.append($('<div>').css({ color: '#b33' }).text(`Error: ${chart.error}`));
            container.append(wrapper);
            return;
        }

        const chartDivId = `saved-chart-${chart.id}`;
        wrapper.append($('<div>').attr('id', chartDivId).css({ height: '420px' }));
        container.append(wrapper);
        Plotly.newPlot(chartDivId, chart.traces || [], chart.layout || {});
    });
}

function loadSelectedChartPresetIntoForm() {
    const chartId = $('#chartPresetList').val();
    if (!chartId) return;

    const chart = (chartState.charts || []).find((item) => item.id === chartId);
    if (!chart) return;

    if (chart.chart_type) $('#chartTypeInput').val(chart.chart_type);
    $('#plotTitleInput').val(chart.title || '');
    $('#chartKeyInput').val(chart.chart_key || '');
    if (chart.source_id) {
        sourceState.active_source_id = chart.source_id;
        $('#sourceSelect').val(chart.source_id);
        syncSourceUI();
    }
    if (chart.range) {
        $('#excelRangeInput').val(chart.range);
    }
    setColumnContext(chart.source_id || null, chart.range || null, chart.columns || [], null);
    applyLoadedColumnLabels(chart.column_labels || []);
    $('#countsModeCheckbox').prop('checked', !!chart.counts_mode);
    syncPlotStyleForm(chart.plot_style || {});
    updateChartActionAvailability();
}

async function saveTemplate() {
    try {
        const templateName = $('#templateNameInput').val().trim();
        const formData = new FormData();
        formData.append('template_name', templateName);

        const response = await fetch('/create_template', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Configuration save failed');
        }

        $('#templateInfo').text(`Saved configuration '${result.template_name}' at ${result.saved_at}`);
        $('#templateNameInput').val(result.template_name);
        await refreshTemplateList(result.template_name);
    } catch (error) {
        console.error('Configuration save error:', error);
        $('#templateInfo').text(`Configuration save failed: ${error.message}`);
    }
}

async function refreshTemplateList(selectedTemplate = null) {
    try {
        const response = await fetch('/templates');
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || 'Unable to list saved configurations');
        }

        const selector = $('#templateList');
        selector.empty();
        if (!result.templates || result.templates.length === 0) {
            selector.append($('<option>').val('').text('No saved configurations'));
            return;
        }

        result.templates.forEach((name) => {
            selector.append($('<option>').val(name).text(name));
        });

        if (selectedTemplate && result.templates.includes(selectedTemplate)) {
            selector.val(selectedTemplate);
        }
    } catch (error) {
        console.error('Configuration list error:', error);
        $('#templateInfo').text(`Configuration list error: ${error.message}`);
    }
}

async function loadTemplate() {
    const templateName = $('#templateList').val();
    if (!templateName) {
        $('#templateInfo').text('Select a saved configuration first.');
        return;
    }

    try {
        const response = await fetch(`/load_template?template_name=${encodeURIComponent(templateName)}`);
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Configuration load failed');
        }

        $('#templateNameInput').val(result.template_name || templateName);

        const state = result.state || {};
        const dataState = state.data || {};
        const templateChartState = state.chart || {};
        const sources = Array.isArray(dataState.sources) ? dataState.sources : [];
        const warnings = [];
        const restoredSourceIds = new Set();

        await fetch('/sources/reset', { method: 'POST' });
        await fetch('/charts/reset', { method: 'POST' });

        for (const source of sources) {
            const sourcePath = source.source_path_canonical || source.source_path || source.path_value || source.source_path_relative;
            if (!sourcePath) {
                warnings.push(`Source '${source.file_name || source.source_id}' has no persisted path.`);
                continue;
            }

            const payload = new FormData();
            payload.append('source_id', source.source_id);
            payload.append('source_path', sourcePath);
            payload.append('sheet_name', source.sheet_name || '');
            if (source.source_path_relative) {
                payload.append('source_path_relative_saved', source.source_path_relative);
            }

            const sourceResponse = await fetch('/sources/load-path', {
                method: 'POST',
                body: payload
            });
            const sourceResult = await sourceResponse.json();
            if (!sourceResponse.ok) {
                warnings.push(`Could not load '${sourcePath}': ${sourceResult.error || 'failed to load'}`);
            } else {
                restoredSourceIds.add(source.source_id);
            }
        }

        const hydrateResponse = await fetch('/hydrate_charts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chart_state: templateChartState })
        });
        const hydrateResult = await hydrateResponse.json();
        if (!hydrateResponse.ok || !hydrateResult.success) {
            throw new Error(hydrateResult.error || 'Could not restore chart presets');
        }

        await refreshSources(dataState.active_source_id || null);
        chartState = hydrateResult.chart_state || { active_chart_id: null, charts: [] };
        await refreshChartPresetList();
        await renderSavedCharts();

        const blockedCharts = (chartState.charts || []).filter((chart) => !restoredSourceIds.has(chart.source_id));

        const activeChart = chartState.charts.find((item) => item.id === chartState.active_chart_id) || chartState.charts[0];
        if (activeChart) {
            $('#chartTypeInput').val(activeChart.chart_type);
            $('#plotTitleInput').val(activeChart.title || '');
            $('#chartKeyInput').val(activeChart.chart_key || '');
            if (activeChart.source_id) {
                sourceState.active_source_id = activeChart.source_id;
                $('#sourceSelect').val(activeChart.source_id);
                syncSourceUI();
            }
            if (activeChart.range) {
                $('#excelRangeInput').val(activeChart.range);
            }
            setColumnContext(activeChart.source_id || null, activeChart.range || null, activeChart.columns || [], null);
            applyLoadedColumnLabels(activeChart.column_labels || []);
            $('#countsModeCheckbox').prop('checked', !!activeChart.counts_mode);
            syncPlotStyleForm(activeChart.plot_style || {});
        }

        const warningText = warnings.length ? ` Warnings: ${warnings.join('; ')}` : '';
        const restoreText = ` Restored sources: ${restoredSourceIds.size}/${sources.length}.`;
        const blockedText = blockedCharts.length ? ` Blocked charts (missing sources): ${blockedCharts.length}.` : '';
        $('#templateInfo').text(`Loaded configuration '${result.template_name}'.${restoreText}${blockedText}${warningText}`);
        updateChartActionAvailability();
    } catch (error) {
        console.error('Configuration load error:', error);
        $('#templateInfo').text(`Configuration load failed: ${error.message}`);
        updateChartActionAvailability();
    }
}

async function resetWorkspace() {
    try {
        await fetch('/sources/reset', { method: 'POST' });
        await fetch('/charts/reset', { method: 'POST' });

        sourceState = { active_source_id: null, sources: [] };
        chartState = { active_chart_id: null, charts: [] };
        setColumnContext(null, null, [], null);
        lastLoadedSourcePath = '';

        isSyncingSourcePathInput = true;
        $('#sourcePathInput').val('');
        isSyncingSourcePathInput = false;
        $('#excelRangeInput').val('');
        $('#plotTitleInput').val('');
        $('#chartKeyInput').val('');
        pendingColumnLabels = [];
        $('#countsModeCheckbox').prop('checked', false);
        syncPlotStyleForm({});

        $('#templateNameInput').val('');
        $('#docxTemplateInput').val('');
        $('#docxTemplatePathInput').val('');
        $('#docxOutputNameInput').val('');
        $('#docxReportInfo').text('');

        $('#rangeInfo').text('');
        $('#rangePreview').remove();
        $('#savedChartsContainer').empty();
        Plotly.purge('plot');

        await refreshSources();
        await refreshChartPresetList();
        await refreshTemplateList();

        setSourceStatus('Workspace reset. Load a source to start charting.');
        $('#templateInfo').text('Workspace reset. Saved report configurations on disk are unchanged.');
        updateChartActionAvailability();
    } catch (error) {
        console.error('Workspace reset error:', error);
        $('#templateInfo').text(`Workspace reset failed: ${error.message}`);
    }
}

function renderRangePreview(preview, excelColumns, truncation) {
    let previewContainer = $('#rangePreview');
    if (previewContainer.length === 0) {
        previewContainer = $('<div id="rangePreview" class="range-preview-table"></div>');
        $('#rangeInfo').after(previewContainer);
    }

    previewContainer.empty();
    if (!preview || preview.length === 0) {
        previewContainer.html('<p>No data in selected range</p>');
        return;
    }

    const fullCols = Array.isArray(excelColumns) ? excelColumns : [];
    let headerKeys;
    if (truncation && fullCols.length && typeof truncation.preview_cols === 'number') {
        headerKeys = fullCols.slice(0, Math.min(truncation.preview_cols, fullCols.length));
    } else if (preview.length) {
        headerKeys = Object.keys(preview[0]);
    } else {
        headerKeys = fullCols;
    }

    const chart = getActiveChartPreset();
    const chartHints = chart && Array.isArray(chart.column_labels) ? chart.column_labels : [];

    const table = $('<table border="1">');
    const headerRow = $('<tr>');
    headerKeys.forEach((colKey, idx) => {
        let displayVal = String(colKey);
        if (pendingColumnLabels.length === fullCols.length && pendingColumnLabels[idx] !== undefined) {
            const p = String(pendingColumnLabels[idx]).trim();
            if (p) displayVal = p;
        } else if (chartHints[idx] !== undefined && String(chartHints[idx]).trim() !== '') {
            displayVal = String(chartHints[idx]);
        }
        const th = $('<th>').css({ padding: '2px', verticalAlign: 'bottom' });
        const input = $('<input type="text">')
            .addClass('preview-col-header')
            .attr('data-col-index', String(idx))
            .attr('aria-label', `Column ${idx + 1} label`)
            .val(displayVal);
        th.append(input);
        headerRow.append(th);
    });
    table.append(headerRow);

    preview.forEach((row) => {
        const tr = $('<tr>');
        headerKeys.forEach((col) => {
            const value = row[col] == null ? '' : String(row[col]);
            tr.append($('<td>').text(value).css('padding', '4px').attr('title', value));
        });
        table.append(tr);
    });

    previewContainer.append(table);
}

async function generateDocxReport() {
    const file = $('#docxTemplateInput')[0].files[0];
    let templatePath = $('#docxTemplatePathInput').val().trim();
    const outputName = $('#docxOutputNameInput').val().trim();

    if (!file && !templatePath && isDesktopBridgeAvailable()) {
        try {
            const pickedPath = await window.pywebview.api.pick_docx_file();
            if (pickedPath) {
                templatePath = pickedPath;
                $('#docxTemplatePathInput').val(pickedPath);
            }
        } catch (error) {
            console.error('Desktop DOCX picker error:', error);
        }
    }

    if (!file && !templatePath) {
        $('#docxReportInfo').text('Select a DOCX file or provide a DOCX template path first.');
        return;
    }

    const formData = new FormData();
    if (file) {
        formData.append('docx_template', file);
    }
    if (templatePath) {
        formData.append('docx_template_path', templatePath);
    }
    if (outputName) {
        formData.append('output_name', outputName);
    }

    $('#docxReportInfo').text('Generating report...');
    try {
        const response = await fetch('/report/generate-docx', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'DOCX generation failed');
        }

        const replacedCount = Array.isArray(result.replaced) ? result.replaced.length : 0;
        const missingImages = (result.missing_images || []).join(', ');
        const missingPlaceholders = (result.missing_placeholders || []).join(', ');
        let msg = `Generated: ${result.output_docx_path}. Replaced ${replacedCount} placeholder(s).`;
        if (missingImages) msg += ` Missing images for keys: ${missingImages}.`;
        if (missingPlaceholders) msg += ` Unused exported keys: ${missingPlaceholders}.`;
        $('#docxReportInfo').text(msg);
    } catch (error) {
        console.error('DOCX report generation error:', error);
        $('#docxReportInfo').text(`DOCX generation failed: ${error.message}`);
    }
}
