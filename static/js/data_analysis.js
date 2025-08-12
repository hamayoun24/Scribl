/**
 * Data Analysis Dashboard
 * This script handles the interactive data visualization for student performance
 */
document.addEventListener('DOMContentLoaded', function() {
    // Chart colors - will be used to assign colors to different students
    const chartColors = [
        'rgba(75, 192, 192, 1)', // Teal
        'rgba(255, 99, 132, 1)',  // Pink
        'rgba(54, 162, 235, 1)',  // Blue
        'rgba(255, 159, 64, 1)',  // Orange
        'rgba(153, 102, 255, 1)', // Purple
        'rgba(255, 205, 86, 1)',  // Yellow
        'rgba(201, 203, 207, 1)', // Grey
        'rgba(0, 204, 150, 1)',   // Seafoam
        'rgba(255, 0, 110, 1)',   // Magenta
        'rgba(0, 138, 255, 1)'    // Light Blue
    ];

    // Store the chart instance for updating later
    let currentChart = null;

    // DOM elements
    const chartTypeSelector = document.getElementById('chartTypeSelector');
    const classSelector = document.getElementById('classSelector');
    const timePeriodSelector = document.getElementById('timePeriodSelector');
    const showClassAverageToggle = document.getElementById('showClassAverageToggle');
    const averageTypeSelector = document.getElementById('averageTypeSelector');

    // Enable/disable average type selector based on toggle
    showClassAverageToggle.addEventListener('change', function() {
        averageTypeSelector.disabled = !this.checked;
    });

    // Update chart when average type changes
    averageTypeSelector.addEventListener('change', updateChart);
    const studentSelector = document.getElementById('studentSelector');
    const selectAllStudentsBtn = document.getElementById('selectAllStudents');
    const deselectAllStudentsBtn = document.getElementById('deselectAllStudents');
    const dataChart = document.getElementById('dataChart');
    const noDataMessage = document.getElementById('noDataMessage');
    const dataInsights = document.getElementById('dataInsights');
    const noStudentsMessage = document.getElementById('noStudentsMessage');

    // Initialize the chart
    initializeChart();

    // Load students when class selection changes
    classSelector.addEventListener('change', function() {
        loadStudentsForClass(this.value);
    });

    // Event listeners for filter changes
    chartTypeSelector.addEventListener('change', updateChart);
    timePeriodSelector.addEventListener('change', updateChart);
    showClassAverageToggle.addEventListener('change', updateChart);

    // Select/deselect all buttons
    selectAllStudentsBtn.addEventListener('click', function() {
        const checkboxes = studentSelector.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = true;
        });
        updateChart();
    });

    deselectAllStudentsBtn.addEventListener('click', function() {
        const checkboxes = studentSelector.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        updateChart();
    });

    // Load students for the initial class selection
    loadStudentsForClass(classSelector.value);

    /**
     * Initialize the chart with empty data
     */
    function initializeChart() {
        const ctx = dataChart.getContext('2d');

        currentChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Score (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Assignment Title'
                        },
                        ticks: {
                            callback: function(value, index) {
                                // Get the actual assignment title
                                return this.chart.data.labels[index] || 'Unknown';
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        enabled: true
                    }
                }
            }
        });
    }

    /**
     * Load students for a selected class
     * @param {string} classId - The ID of the selected class or 'all'
     */
    function loadStudentsForClass(classId) {
        // Clear current student selector
        studentSelector.innerHTML = '';

        // Fetch students for the selected class
        fetch(`/api/students?class_id=${classId}&_cache=${new Date().getTime()}`)
            .then(response => response.json())
            .then(data => {
                if (data.students.length === 0) {
                    noStudentsMessage.style.display = 'block';
                    return;
                }

                noStudentsMessage.style.display = 'none';

                // Generate student checkboxes
                data.students.forEach((student, index) => {
                    const colorIndex = index % chartColors.length;
                    const div = document.createElement('div');
                    div.className = 'student-item';

                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.id = `student-${student.id}`;
                    checkbox.className = 'student-checkbox';
                    checkbox.value = student.id;
                    checkbox.dataset.name = student.name;
                    checkbox.dataset.color = chartColors[colorIndex];
                    checkbox.addEventListener('change', updateChart);

                    const colorIndicator = document.createElement('span');
                    colorIndicator.className = 'color-indicator';
                    colorIndicator.style.backgroundColor = chartColors[colorIndex];

                    const label = document.createElement('label');
                    label.setAttribute('for', `student-${student.id}`);
                    label.appendChild(colorIndicator);
                    label.appendChild(document.createTextNode(student.name));

                    div.appendChild(checkbox);
                    div.appendChild(label);
                    studentSelector.appendChild(div);
                });

                // Select the first few students by default
                const checkboxes = studentSelector.querySelectorAll('input[type="checkbox"]');
                const maxInitialSelected = Math.min(3, checkboxes.length);

                for (let i = 0; i < maxInitialSelected; i++) {
                    checkboxes[i].checked = true;
                }

                // Update the chart with the new selection
                updateChart();
            })
            .catch(error => {
                console.error('Error loading students:', error);
                noStudentsMessage.style.display = 'block';
                studentSelector.innerHTML = '<div class="alert alert-danger">Error loading students. Please try again.</div>';
            });
    }

    /**
     * Update the chart based on current selections
     */
    function updateChart() {
        const chartType = chartTypeSelector.value;
        const classId = classSelector.value;
        const timePeriod = timePeriodSelector.value;
        const showClassAverage = showClassAverageToggle.checked;

        // Get selected students
        const selectedStudents = Array.from(studentSelector.querySelectorAll('input[type="checkbox"]:checked'))
            .map(checkbox => ({
                id: checkbox.value,
                name: checkbox.dataset.name,
                color: checkbox.dataset.color
            }));

        if (selectedStudents.length === 0) {
            // No students selected, show empty chart
            updateChartWithData([], chartType);
            noDataMessage.style.display = 'block';
            dataInsights.innerHTML = '<p>No students selected. Please select at least one student to view data.</p>';
            return;
        }

        // Fetch data for selected students
        const studentIds = selectedStudents.map(s => s.id).join(',');
        const averageType = showClassAverage ? averageTypeSelector.value : 'none';
        fetch(`/api/student_data?ids=${studentIds}&class_id=${classId}&time_period=${timePeriod}&chart_type=${chartType}&include_average=${showClassAverage}&average_type=${averageType}&_cache=${new Date().getTime()}`)
            .then(response => response.json())
            .then(data => {
                if (!data.datasets || data.datasets.length === 0) {
                    updateChartWithData([], chartType);
                    noDataMessage.style.display = 'block';
                    dataInsights.innerHTML = '<p>No data available for the selected students and filters.</p>';
                    return;
                }

                noDataMessage.style.display = 'none';

                // Map the API data to chart datasets
                const datasets = data.datasets.map((dataset, index) => {
                    const student = selectedStudents.find(s => s.id === dataset.student_id);
                    const color = student ? student.color : chartColors[index % chartColors.length];

                    return {
                        label: dataset.name,
                        data: dataset.data,
                        borderColor: color,
                        backgroundColor: color.replace('1)', '0.2)'),
                        borderWidth: dataset.is_average ? 3 : 2,
                        pointRadius: dataset.is_average ? 0 : 3,
                        tension: 0.1,
                        fill: false
                    };
                });

                // Update averageTypeSelector options dynamically
                // Update average type selector options
                if (showClassAverageToggle.checked) {
                    averageTypeSelector.innerHTML = '<option value="all">Overall Average</option>';
                    const uniqueAssignments = new Set();
                    data.datasets.forEach(dataset => {
                        if (dataset.assignment_titles) {
                            dataset.assignment_titles.forEach(title => uniqueAssignments.add(title));
                        }
                    });
                    uniqueAssignments.forEach(title => {
                        averageTypeSelector.innerHTML += `<option value="${title}">${title}</option>`;
                    });
                }

                // Special handling for average datasets
                datasets.forEach(dataset => {
                    if (dataset.is_average) {
                        const avgValue = dataset.data[0]; // Get the average value
                        dataset.data = new Array(data.labels.length).fill(avgValue); // Fill with same value
                        dataset.borderDash = [5, 5]; // Dashed line for average
                        dataset.pointRadius = 0; // Hide points for average line
                        dataset.borderWidth = 2;
                        dataset.fill = false;
                        dataset.order = -1; // Ensure average appears on top
                    }
                });

                // Group data by assignment name
                const assignmentData = {};
                datasets.forEach(dataset => {
                    dataset.data.forEach((value, index) => {
                        // Use simple sample numbering
                        const label = `Sample ${index + 1}`;
                        if (!assignmentData[label]) {
                            assignmentData[label] = {};
                        }
                        if (!assignmentData[label][dataset.label]) {
                            assignmentData[label][dataset.label] = [];
                        }
                        assignmentData[label][dataset.label].push(value);
                    });
                });

                const assignmentLabels = Object.keys(assignmentData);

                // Create new datasets with assignment-based data
                const newDatasets = datasets.map(originalDataset => {
                    const newData = assignmentLabels.map(label => {
                        const values = assignmentData[label][originalDataset.label] || [];
                        return values.length > 0 ? values.reduce((a, b) => a + b) / values.length : null;
                    });
                    return {
                        ...originalDataset,
                        data: newData
                    };
                });

                updateChartWithData(newDatasets, chartType, assignmentLabels);
                updateInsights(data.insights, chartType);
            })
            .catch(error => {
                console.error('Error fetching data:', error);
                noDataMessage.style.display = 'block';
                dataInsights.innerHTML = '<p>Error fetching data. Please try again.</p>';
            });
    }

    /**
     * Update the chart with new data
     * @param {Array} datasets - The datasets to display
     * @param {string} chartType - The type of chart to display
     * @param {Array} labels - The x-axis labels
     */
    function updateChartWithData(datasets, chartType, labels = []) {
        // Update y-axis title based on chart type
        let yAxisTitle = 'Score (%)';
        if (chartType === 'writing_age') {
            yAxisTitle = 'Writing Age (years)';
        } else if (chartType === 'age_difference') {
            yAxisTitle = 'Age Difference (years)';
        }

        // Update chart configuration
        currentChart.options.scales.y.title.text = yAxisTitle;
        currentChart.data.datasets = datasets;
        currentChart.data.labels = labels;
        currentChart.update();
    }

    /**
     * Update the insights section based on the data
     * @param {Object} insights - The insights to display
     * @param {string} chartType - The type of chart displayed
     */
    function updateInsights(insights, chartType) {
        if (!insights) {
            dataInsights.innerHTML = '<p>No insights available for the selected data.</p>';
            return;
        }

        let html = '<ul class="list-group list-group-flush">';

        if (insights.key_observations) {
            insights.key_observations.forEach(observation => {
                html += `<li class="list-group-item">${observation}</li>`;
            });
        }

        if (insights.recommendations) {
            html += `<li class="list-group-item"><strong>Recommendations:</strong> ${insights.recommendations}</li>`;
        }

        html += '</ul>';
        dataInsights.innerHTML = html;
    }
});