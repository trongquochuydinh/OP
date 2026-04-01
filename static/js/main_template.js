let dataset = null;

$(document).ready(function () {

    // Upload file immediately when selected
    $('#fileInput').on('change', function () {
        const file = this.files[0];
        if (!file) return;

        uploadFile(file);
    });

    // Generate plot only on button click
    $('.generate-plot').on('click', function () {
        generatePlotRequest();
    });

    // Excel range functionality
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

    // Auto-preview range when user types (with debounce)
    let rangeInputTimeout;
    $('#excelRangeInput').on('input', function () {
        clearTimeout(rangeInputTimeout);
        const range = $(this).val().trim();
        
        if (range) {
            rangeInputTimeout = setTimeout(() => {
                previewExcelRange();
            }, 500);
        } else {
            $('#rangeInfo').text('');
        }
    });

    refreshTemplateList();

});


/* ===============================
   FILE UPLOAD
================================= */

async function uploadFile(file) {

    const formData = new FormData();
    formData.append("file", file);
    formData.append("source_path", $('#sourcePathInput').val().trim());

    try {
        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error("Upload failed");
        }

        const data = await response.json();

        dataset = data;

        const sourcePath = data.source_path || data.source_path_relative || '';
        if (sourcePath) {
            $('#sourcePathInput').val(sourcePath);
        }

        if (dataset.type === "yaml") {
            $('#excelRangeDiv').hide();
        } else {
            $('#excelRangeDiv').show();
            
            // Show file dimensions for Excel files
            if (data.total_rows && data.total_cols) {
                $('#rangeInfo').text(`File dimensions: ${data.total_rows} rows × ${data.total_cols} columns`);
            }
        }

        Plotly.purge('plot');


    } catch (error) {
        console.error("Upload error:", error);
        alert("File upload failed.");
    }
}

function truncateText(text, maxLength = 60) {
    if (text === null || text === undefined) return "";
    const str = String(text);
    return str.length > maxLength ? str.slice(0, maxLength) + "…" : str;
}


/* ===============================
   GENERATE PLOT
================================= */

async function generatePlotRequest() {

    if (!dataset) {
        alert("Upload a file first.");
        return;
    }

    const title = $('#plotTitleInput').val();
    const chartType = $('#chartTypeInput').val();

    const formData = new FormData();
    formData.append("chart_type", chartType);
    formData.append("title", title);

    // For Excel files, check if a range has been applied
    if (dataset.type === "xlsx") {
        if (!dataset.range_applied) {
            alert("Please apply an Excel range first by entering a range (e.g., A2:N28) and clicking 'Apply Range'.");
            return;
        }
        // Automatically use all columns from the applied range
        formData.append("columns", JSON.stringify(dataset.columns));
        
        // Show user what will happen based on number of columns
        const numCols = dataset.columns.length;
        console.log(`Plotting with ${numCols} columns:`, dataset.columns);
        
        if (numCols === 1) {
            console.log("Single column detected → Will create frequency/count chart");
        } else if (numCols === 2) {
            console.log(`Two columns detected → X: ${dataset.columns[0]}, Y: ${dataset.columns[1]}`);
        } else {
            console.log(`Multiple columns (${numCols}) detected → Using first two for X/Y axes`);
        }
    } else if (Array.isArray(dataset.columns)) {
        formData.append("columns", JSON.stringify(dataset.columns));
    }

    try {
        const response = await fetch("/generate", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error("Generation failed");
        }

        const plotData = await response.json();

        Plotly.newPlot('plot', plotData.traces, plotData.layout || {});

    } catch (error) {
        console.error("Plot error:", error);
        alert("Plot generation failed.");
    }
}


/* ===============================
   EXCEL RANGE FUNCTIONALITY
================================= */

async function previewExcelRange() {
    if (!dataset || dataset.type !== "xlsx") {
        alert("Please upload an Excel file first.");
        return;
    }

    const range = $('#excelRangeInput').val().trim();
    if (!range) {
        $('#rangeInfo').text('Please enter a range (e.g., A2:N28)');
        return;
    }

    try {
        const formData = new FormData();
        formData.append("range", range);

        const response = await fetch("/preview-range", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            $('#rangeInfo').text(`Error: ${result.error}`);
            return;
        }

        // Update range info display
        const info = result.range_info;
        const rangeLabel = info.display || `${info.start_cell}:${info.end_cell}`;
        $('#rangeInfo').html(`Range ${rangeLabel} → ${info.total_rows} rows × ${info.total_cols} columns`);

        // Show preview table with Excel column headers
        renderRangePreview(result.preview, result.excel_columns);

    } catch (error) {
        console.error("Range preview error:", error);
        $('#rangeInfo').text("Preview failed: " + error.message);
    }
}

/* ===============================
   TEMPLATE SAVE/LOAD
================================= */

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

async function saveTemplate() {
    try {
        const templateName = $('#templateNameInput').val().trim();
        const sourcePathInput = $('#sourcePathInput').val().trim();
        const formData = new FormData();
        formData.append('template_name', templateName);
        formData.append('source_path', sourcePathInput);

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

        const state = result.state || {};
        const dataState = state.data || {};
        const chartState = state.chart || {};
        const source = dataState.source || {};
        const sourcePath = source.source_path || source.source_path_relative || '';
        let sourceLoadWarning = '';

        if (sourcePath) {
            $('#sourcePathInput').val(sourcePath);
            try {
                await uploadFromSavedPath(sourcePath);
            } catch (pathError) {
                sourceLoadWarning = ` (could not open source path: ${pathError.message})`;
            }
        }

        if (chartState.chart_type) {
            $('#chartTypeInput').val(chartState.chart_type);
        }
        $('#plotTitleInput').val(chartState.title || '');

        if (source.file_type === 'xlsx') {
            $('#excelRangeDiv').show();
            if (source.range_applied) {
                $('#excelRangeInput').val(source.range_applied);
                await applyExcelRange();
            }
        } else {
            $('#excelRangeDiv').hide();
        }

        if (Array.isArray(dataState.columns)) {
            const datasetType = dataset && dataset.type ? dataset.type : source.file_type;
            dataset = {
                type: datasetType,
                columns: dataState.columns,
                row_count: dataState.row_count,
                preview: dataState.preview || [],
                range_applied: source.range_applied || null
            };
        }

        if (chartState.chart_type && Array.isArray(chartState.columns) && chartState.columns.length > 0) {
            await generatePlotRequest();
        }

        const sourceLabel = source.source_path || source.source_path_relative || source.file_name || 'unknown source';
        $('#templateInfo').text(`Loaded template '${result.template_name}' from ${sourceLabel}.${sourceLoadWarning}`);
    } catch (error) {
        console.error('Template load error:', error);
        $('#templateInfo').text(`Template load failed: ${error.message}`);
    }
}

async function uploadFromSavedPath(sourcePath) {
    const formData = new FormData();
    formData.append('source_path', sourcePath);

    const response = await fetch('/upload-from-path', {
        method: 'POST',
        body: formData
    });

    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || 'Unable to load source path');
    }

    dataset = data;

    if (dataset.type === 'yaml') {
        $('#excelRangeDiv').hide();
    } else {
        $('#excelRangeDiv').show();
        if (data.total_rows && data.total_cols) {
            $('#rangeInfo').text(`File dimensions: ${data.total_rows} rows × ${data.total_cols} columns`);
        }
    }

    Plotly.purge('plot');
}

async function applyExcelRange() {
    if (!dataset || dataset.type !== "xlsx") {
        alert("Please upload an Excel file first.");
        return;
    }

    const range = $('#excelRangeInput').val().trim();
    if (!range) {
        alert("Please enter a range (e.g., A2:N28)");
        return;
    }

    try {
        const formData = new FormData();
        formData.append("range", range);

        const response = await fetch("/apply-range", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            alert(`Error: ${result.error}`);
            return;
        }

        // Update the dataset
        dataset.columns = result.columns;
        dataset.preview = result.preview;
        dataset.row_count = result.row_count;
        dataset.range_applied = true; // Mark that a range has been applied

        // Update range info with plot strategy
        const info = result.range_info;
        const numCols = result.columns.length;
        let plotStrategy = "";
        
        if (numCols === 1) {
            plotStrategy = " → Will create frequency/count chart";
        } else if (numCols === 2) {
            plotStrategy = ` → X-axis: ${result.columns[0]}, Y-axis: ${result.columns[1]}`;
        } else {
            plotStrategy = ` → Will use first 2 columns: ${result.columns[0]} vs ${result.columns[1]}`;
        }
        
        $('#rangeInfo').html(
            `✓ Applied ${info.display || range} → ` +
            `${info.total_rows} rows × ${info.total_cols} columns${plotStrategy}`
        );

        // Clear any previous plots
        Plotly.purge('plot');

        console.log("Range applied successfully:", result);

    } catch (error) {
        console.error("Range application error:", error);
        alert("Range application failed: " + error.message);
    }
}

function renderRangePreview(preview, excelColumns) {
    // Create a separate preview area for range preview
    let previewContainer = $('#rangePreview');
    if (previewContainer.length === 0) {
        // Create the preview container if it doesn't exist
        previewContainer = $('<div id="rangePreview" class="range-preview-table"></div>');
        $('#rangeInfo').after(previewContainer);
    }

    previewContainer.empty();

    if (!preview || preview.length === 0) {
        previewContainer.html("<p>No data in selected range</p>");
        return;
    }

    const table = $('<table border="1" style="border-collapse: collapse; font-size: 0.85em;">');
    
    // Create header with Excel column names
    const header = $('<tr>');
    excelColumns.forEach(col => {
        const th = $('<th>').text(col).css('padding', '4px');
        header.append(th);
    });
    table.append(header);

    // Add data rows
    preview.forEach(row => {
        const tr = $('<tr>');
        excelColumns.forEach(col => {
            const td = $('<td>').text(truncateText(row[col], 30)).css('padding', '4px');
            td.attr('title', row[col]);
            tr.append(td);
        });
        table.append(tr);
    });

    previewContainer.append(table);
}
