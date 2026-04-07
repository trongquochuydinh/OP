let sourceState = { active_source_id: null, sources: [] };
let chartState = { active_chart_id: null, charts: [] };
let columnContext = { source_id: null, range: null, columns: [] };

$(document).ready(function () {
    $('#fileInput').on('change', function () {
        const files = Array.from(this.files || []);
        if (files.length === 0) return;
        uploadFileSources(files);
        $(this).val('');
    });

    $('#loadSourcePathBtn').on('click', function () {
        loadSourceFromPathInput();
    });

    $('#sourceSelect').on('change', function () {
        sourceState.active_source_id = $(this).val() || null;
        syncSourceUI();
    });

    $('#loadSheetBtn').on('click', function () {
        loadSelectedSheetForSource();
    });

    $('#chartPresetList').on('change', function () {
        loadSelectedChartPresetIntoForm();
    });

    $('#useCustomColumnLabels').on('change', function () {
        refreshColumnLabelEditor();
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

    refreshTemplateList();
    refreshSources();
    refreshChartPresetList();
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
        setColumnContext(null, null, []);
        return;
    }

    const pathValue = source.source_path || source.source_path_relative || '';
    $('#sourcePathInput').val(pathValue);

    if (source.file_type === 'xlsx') {
        $('#sheetControls').show();
        const sheetSelect = $('#sheetSelect');
        sheetSelect.empty();
        const sheets = Array.isArray(source.available_sheets) ? source.available_sheets : [];
        sheets.forEach((sheetName) => {
            sheetSelect.append($('<option>').val(sheetName).text(sheetName));
        });
        if (source.sheet_name) {
            sheetSelect.val(source.sheet_name);
        }

        $('#excelRangeDiv').show();
        if (source.total_rows && source.total_cols) {
            $('#rangeInfo').text(`File dimensions: ${source.total_rows} rows x ${source.total_cols} columns`);
        }
        setColumnContext(source.source_id, null, []);
    } else {
        $('#sheetControls').hide();
        $('#excelRangeDiv').hide();
        setColumnContext(source.source_id, null, source.columns || []);
    }
}

function setColumnContext(sourceId, rangeValue, columns) {
    columnContext = {
        source_id: sourceId,
        range: rangeValue,
        columns: Array.isArray(columns) ? columns : []
    };
    refreshColumnLabelEditor();
}

function refreshColumnLabelEditor() {
    const useCustom = $('#useCustomColumnLabels').is(':checked');
    const editor = $('#columnLabelEditor');
    if (!useCustom) {
        editor.hide();
        return;
    }

    editor.show();
    const existingValues = [];
    editor.find('.column-label-input').each(function () {
        existingValues.push($(this).val());
    });
    editor.empty();

    if (!columnContext.columns || columnContext.columns.length === 0) {
        editor.append($('<div>').css({ color: '#666' }).text('No columns available yet. Preview/select a range or source first.'));
        return;
    }

    columnContext.columns.forEach((columnName, index) => {
        const row = $('<div>').css({ display: 'flex', gap: '8px', marginBottom: '4px', alignItems: 'center' });
        row.append($('<div>').css({ minWidth: '220px', fontSize: '0.9em' }).text(`Column ${index + 1}: ${columnName}`));
        row.append(
            $('<input>')
                .attr('type', 'text')
                .attr('data-col-index', String(index))
                .addClass('column-label-input')
                .val(existingValues[index] || columnName)
                .css({ flex: '1', minWidth: '220px' })
        );
        editor.append(row);
    });
}

function setCustomColumnLabels(labels) {
    const normalized = Array.isArray(labels) ? labels : [];
    const useCustom = normalized.length > 0;
    $('#useCustomColumnLabels').prop('checked', useCustom);
    refreshColumnLabelEditor();

    if (!useCustom) {
        return;
    }

    $('#columnLabelEditor .column-label-input').each(function () {
        const idx = Number($(this).attr('data-col-index'));
        if (idx >= 0 && idx < normalized.length) {
            $(this).val(normalized[idx]);
        }
    });
}

function collectCustomColumnLabels(columns) {
    if (!$('#useCustomColumnLabels').is(':checked')) {
        return [];
    }

    const labels = [];
    $('#columnLabelEditor .column-label-input').each(function () {
        labels.push($(this).val().trim());
    });

    if (labels.length !== columns.length) {
        return columns.map((value) => String(value));
    }

    return labels.map((label, idx) => label || String(columns[idx]));
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

async function resolveColumnsForChart(source, rangeValue, updatePreview) {
    if (source.file_type !== 'xlsx') {
        const cols = Array.isArray(source.columns) ? source.columns : [];
        setColumnContext(source.source_id, null, cols);
        return cols;
    }

    if (!rangeValue) {
        throw new Error('Range is required for Excel charts');
    }

    const response = await fetch('/preview-range', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id: source.source_id, range: rangeValue })
    });
    const result = await response.json();
    if (!response.ok || !result.success) {
        throw new Error(result.error || 'Range preview failed');
    }

    const cols = Array.isArray(result.excel_columns) ? result.excel_columns : [];
    setColumnContext(source.source_id, rangeValue, cols);

    if (updatePreview) {
        const info = result.range_info;
        $('#rangeInfo').text(`Range ${info.display} -> ${info.total_rows} rows x ${info.total_cols} columns`);
        renderRangePreview(result.preview, cols);
    }

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
    } catch (error) {
        console.error('Sources refresh error:', error);
    }
}

async function uploadFileSources(files) {
    const requestedPath = $('#sourcePathInput').val().trim();
    const failures = [];
    let lastSourceId = null;

    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('source_path', requestedPath);

        try {
            const response = await fetch('/sources/upload', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Upload failed');
            }
            lastSourceId = result.source_id;
        } catch (error) {
            console.error('Upload error:', error);
            failures.push(`${file.name}: ${error.message}`);
        }
    }

    await refreshSources(lastSourceId);
    Plotly.purge('plot');

    if (failures.length > 0) {
        alert(`Some files failed to upload:\n- ${failures.join('\n- ')}`);
    }
}

async function loadSourceFromPathInput() {
    const sourcePath = $('#sourcePathInput').val().trim();
    if (!sourcePath) {
        alert('Enter source path first.');
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
        formData.append('column_labels', JSON.stringify(collectCustomColumnLabels(columns)));

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
        formData.append('column_labels', JSON.stringify(collectCustomColumnLabels(columns)));

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
        formData.append('column_labels', JSON.stringify(collectCustomColumnLabels(columns)));

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
    setColumnContext(chart.source_id || null, chart.range || null, chart.columns || []);
    setCustomColumnLabels(chart.column_labels || []);
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
            throw new Error(result.error || 'Template save failed');
        }

        $('#templateInfo').text(`Saved template '${result.template_name}' at ${result.saved_at}`);
        $('#templateNameInput').val(result.template_name);
        await refreshTemplateList(result.template_name);
    } catch (error) {
        console.error('Template save error:', error);
        $('#templateInfo').text(`Template save failed: ${error.message}`);
    }
}

async function refreshTemplateList(selectedTemplate = null) {
    try {
        const response = await fetch('/templates');
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || 'Unable to list templates');
        }

        const selector = $('#templateList');
        selector.empty();
        if (!result.templates || result.templates.length === 0) {
            selector.append($('<option>').val('').text('No templates'));
            return;
        }

        result.templates.forEach((name) => {
            selector.append($('<option>').val(name).text(name));
        });

        if (selectedTemplate && result.templates.includes(selectedTemplate)) {
            selector.val(selectedTemplate);
        }
    } catch (error) {
        console.error('Template list error:', error);
        $('#templateInfo').text(`Template list error: ${error.message}`);
    }
}

async function loadTemplate() {
    const templateName = $('#templateList').val();
    if (!templateName) {
        $('#templateInfo').text('Select a template first.');
        return;
    }

    try {
        const response = await fetch(`/load_template?template_name=${encodeURIComponent(templateName)}`);
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Template load failed');
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
            const sourcePath = source.path_value || source.source_path || source.source_path_relative;
            if (!sourcePath) {
                warnings.push(`source ${source.file_name || source.source_id} has no path`);
                continue;
            }

            const payload = new FormData();
            payload.append('source_id', source.source_id);
            payload.append('source_path', sourcePath);
            payload.append('sheet_name', source.sheet_name || '');
            payload.append('path_mode', source.path_mode || '');
            payload.append('path_value', source.path_value || '');
            payload.append('source_path_saved', source.source_path || '');
            payload.append('source_path_relative_saved', source.source_path_relative || '');

            const sourceResponse = await fetch('/sources/load-path', {
                method: 'POST',
                body: payload
            });
            const sourceResult = await sourceResponse.json();
            if (!sourceResponse.ok) {
                warnings.push(`${sourcePath}: ${sourceResult.error || 'failed to load'}`);
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
            setColumnContext(activeChart.source_id || null, activeChart.range || null, activeChart.columns || []);
            setCustomColumnLabels(activeChart.column_labels || []);
        }

        const warningText = warnings.length ? ` Warnings: ${warnings.join('; ')}` : '';
        const restoreText = ` Restored sources: ${restoredSourceIds.size}/${sources.length}.`;
        const blockedText = blockedCharts.length ? ` Blocked charts (missing sources): ${blockedCharts.length}.` : '';
        $('#templateInfo').text(`Loaded template '${result.template_name}'.${restoreText}${blockedText}${warningText}`);
    } catch (error) {
        console.error('Template load error:', error);
        $('#templateInfo').text(`Template load failed: ${error.message}`);
    }
}

function renderRangePreview(preview, excelColumns) {
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

    const table = $('<table border="1" style="border-collapse: collapse; font-size: 0.85em;">');
    const header = $('<tr>');
    excelColumns.forEach((col) => {
        header.append($('<th>').text(col).css('padding', '4px'));
    });
    table.append(header);

    preview.forEach((row) => {
        const tr = $('<tr>');
        excelColumns.forEach((col) => {
            const value = row[col] == null ? '' : String(row[col]);
            tr.append($('<td>').text(value).css('padding', '4px').attr('title', value));
        });
        table.append(tr);
    });

    previewContainer.append(table);
}

async function generateDocxReport() {
    const file = $('#docxTemplateInput')[0].files[0];
    const templatePath = $('#docxTemplatePathInput').val().trim();
    const outputName = $('#docxOutputNameInput').val().trim();

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
