
// Wait for both DOM and Google Charts to load
google.charts.load('current', {'packages':['corechart']});
google.charts.setOnLoadCallback(initializeChart);

function initializeChart() {
    document.addEventListener('DOMContentLoaded', drawChart);
}

function drawChart() {
    try {
        console.log("Starting chart initialization");
        
        // Get table data
        const rows = Array.from(document.querySelectorAll('table tbody tr:not(.details-row)'));
        if (!rows.length) {
            console.error("No data rows found");
            return;
        }

        // Create data table
        const data = new google.visualization.DataTable();
        data.addColumn('string', 'Date');
        data.addColumn('number', 'Score');

        // Process each row
        const chartData = rows.map(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 6) {
                const date = cells[1].textContent.trim();
                const scoreText = cells[5].textContent.trim();
                // Extract number from percentage string (e.g., "85%" -> 85)
                const score = parseFloat(scoreText.replace(/[^0-9.]/g, ''));
                
                if (!isNaN(score)) {
                    console.log(`Adding data point: ${date} - ${score}`);
                    return [date, score];
                }
            }
            return null;
        }).filter(item => item !== null);

        if (chartData.length === 0) {
            console.error("No valid data points found");
            return;
        }

        // Add data to chart
        data.addRows(chartData);

        // Configure chart
        const options = {
            title: 'Writing Progress',
            height: 400,
            curveType: 'function',
            legend: { position: 'none' },
            vAxis: {
                title: 'Score (%)',
                minValue: 0,
                maxValue: 100,
                format: '#"%"'
            },
            hAxis: {
                title: 'Date',
                slantedText: true,
                slantedTextAngle: 45
            }
        };

        // Draw chart
        const chartDiv = document.getElementById('performanceChart');
        if (chartDiv) {
            const chart = new google.visualization.LineChart(chartDiv);
            chart.draw(data, options);
            console.log("Chart drawn successfully with", chartData.length, "points");
        } else {
            console.error("Chart container not found");
        }
    } catch (error) {
        console.error("Error creating chart:", error);
    }
}

// Add window resize handler
window.addEventListener('resize', drawChart);
