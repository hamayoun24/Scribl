import re

with open('templates/student_portfolio_new_temp.html', 'r') as f:
    content = f.read()

# Check if the file already has Chart.js included
if 'cdn.jsdelivr.net/npm/chart.js' not in content:
    # Add Chart.js script to the extra_scripts block
    pattern = r'{% block extra_scripts %}(.*?){% endblock %}'
    replacement = r'{% block extra_scripts %}\1<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>\n{% endblock %}'
    updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Fix the duplicate closing tags in the JavaScript code
    pattern = r'document\.addEventListener\(\'DOMContentLoaded\', function\(\) \{[\s\S]*?\}\);\s*\}\);'
    replacement = '''document.addEventListener('DOMContentLoaded', function() {
    // Chart toggle functionality
    const genreChartBtn = document.getElementById('genreChartBtn');
    const ageChartBtn = document.getElementById('ageChartBtn');
    const genreChart = document.getElementById('genreChart');
    const ageChart = document.getElementById('ageChart');
    
    genreChartBtn.addEventListener('click', function() {
        genreChart.style.display = 'block';
        ageChart.style.display = 'none';
        genreChartBtn.classList.add('active');
        ageChartBtn.classList.remove('active');
    });
    
    ageChartBtn.addEventListener('click', function() {
        genreChart.style.display = 'none';
        ageChart.style.display = 'block';
        ageChartBtn.classList.add('active');
        genreChartBtn.classList.remove('active');
    });
    
    // Generate the genre chart
    const genreCtx = document.getElementById('genreChart').getContext('2d');
    const chartData = {{ chart_data|safe }};
    new Chart(genreCtx, {
        type: 'bar',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Criteria Met (%)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.raw.toFixed(1) + '%';
                        }
                    }
                }
            }
        }
    });
    
    // Generate the age comparison chart
    const ageCtx = document.getElementById('ageChart').getContext('2d');
    const ageChartData = {{ age_chart_data|safe }};
    new Chart(ageCtx, {
        type: 'line',
        data: ageChartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    title: {
                        display: true,
                        text: 'Writing Age'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.raw.toFixed(1);
                        }
                    }
                }
            }
        }
    });
    
    // Ensure the toggle buttons work with existing charts
    genreChartBtn.click();
    
    // This function is now handled by portfolio_collapsible.js
    function populateAnalysisData(sampleId) {
        // Functionality moved to portfolio_collapsible.js
        // This empty function remains to prevent any existing calls to it from breaking
    }
});'''
    
    updated_content = re.sub(pattern, replacement, updated_content, flags=re.DOTALL)
    
    # Write the updated content back to the file
    with open('templates/student_portfolio_new_temp.html', 'w') as f:
        f.write(updated_content)
    
    print("Successfully added Chart.js and fixed the JavaScript code!")
else:
    print("Chart.js is already included in the template.")