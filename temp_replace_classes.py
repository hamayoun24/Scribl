import re

with open('templates/student_portfolio_new_temp.html', 'r') as f:
    content = f.read()

# Instead of selective replacement, let's rewrite the entire chart initialization code
# Find the chart initialization section
chart_section_pattern = re.compile(r'document\.addEventListener\(\'DOMContentLoaded\', function\(\) \{.*?// Chart toggle functionality.*?// Generate the genre chart.*?// Generate the age comparison chart.*?}\);', re.DOTALL)

# Create the replacement code block with proper formatting
chart_section_replacement = '''document.addEventListener('DOMContentLoaded', function() {
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
});'''

# Replace the chart section with our new code
updated_content = chart_section_pattern.sub(chart_section_replacement, content)

# Write the updated content back to the file
with open('templates/student_portfolio_new_temp.html', 'w') as f:
    f.write(updated_content)

print("Successfully updated the chart initialization code!")