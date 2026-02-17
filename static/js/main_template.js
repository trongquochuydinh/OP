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

        dataset = data; // store full dataset
        if (data.schema != null)
            populateSelect(data.schema);

        Plotly.purge('plot'); // clear previous plot

    } catch (error) {
        console.error("Upload error:", error);
        alert("File upload failed.");
    }
}


/* ===============================
   POPULATE COLUMN SELECT
================================= */

function populateSelect(schema) {

    const select = $('#columnSelect');
    select.empty();

    if (!schema.measures || schema.measures.length === 0) {
        return;
    }

    // Add options
    schema.measures.forEach(col => {
        select.append(new Option(col, col));
    });

    // 🔥 Auto-select first column
    const firstColumn = schema.measures[0];
    select.val([firstColumn]).trigger('change');
}


/* ===============================
   GENERATE PLOT
================================= */

async function generatePlotRequest() {

    if (!dataset) {
        alert("Upload a file first.");
        return;
    }

    const selectedColumn = $('#columnSelect').val();
    const title = $('#plotTitleInput').val();

    const chartType = $('#chartTypeInput').val();

    const formData = new FormData();
    formData.append("records", JSON.stringify(dataset.records));
    formData.append("chart_type", chartType);
    formData.append("title", title);

    if (dataset.type === "xlsx") {
        const selectedColumn = $('#columnSelect').val();

        if (!selectedColumn) {
            alert("Please select a column.");
            return;
        }

        formData.append("column", selectedColumn);
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
