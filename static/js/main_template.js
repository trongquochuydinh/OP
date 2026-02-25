let dataset = null;

$(document).ready(function () {

    $('#columnSelect').select2({
        placeholder: "Select column",
        allowClear: true,
        width: '100%'
    });

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

});


/* ===============================
   FILE UPLOAD
================================= */

async function uploadFile(file) {

    const formData = new FormData();
    formData.append("file", file);

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

        cleanup_column_select();
        if (dataset.type === "yaml") {
            $('#columnSelect').prop('disabled', true);
        } else {
            populateSelect(data.columns);
            $('#columnSelect').prop('disabled', false);
        }

        renderPreviewTable(data.preview, data.columns);

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

function renderPreviewTable(preview, columns) {

    const container = document.getElementById("previewTable");
    container.innerHTML = "";

    if (!preview || preview.length === 0) {
        container.innerHTML = "<p>No preview available</p>";
        return;
    }

    const table = document.createElement("table");
    table.border = "1";
    table.style.borderCollapse = "collapse";

    const header = document.createElement("tr");

    columns.forEach(col => {
        const th = document.createElement("th");
        th.innerText = col;
        th.style.padding = "4px";
        header.appendChild(th);
    });

    table.appendChild(header);

    preview.forEach(row => {
        const tr = document.createElement("tr");

        columns.forEach(col => {
            const td = document.createElement("td");
            const value = row[col];
            td.innerText = truncateText(value, 80);
            td.title = value;
            td.style.padding = "4px";
            tr.appendChild(td);
        });

        table.appendChild(tr);
    });


    container.appendChild(table);
}



/* ===============================
   POPULATE COLUMN SELECT
================================= */

function cleanup_column_select() {
    $('#columnSelect').empty().trigger('change');
}

function populateSelect(columns) {

    const select = $('#columnSelect');

    select.empty();

    columns.forEach(col => {
        select.append(new Option(col, col));
    });

    // Refresh Select2
    select.trigger('change');

    // Auto-select first column
    if (columns.length > 0) {
        select.val(columns[0]).trigger('change');
    }
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

    if (dataset.type === "xlsx") {
        const selectedColumns = $('#columnSelect').val();

        if (!selectedColumns) {
            alert("Please select a column.");
            return;
        }

        formData.append("columns", JSON.stringify(selectedColumns));
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
