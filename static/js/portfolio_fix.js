
document.addEventListener('DOMContentLoaded', function() {
    const genreChartEl = document.getElementById('genreChart');
    const ageChartEl = document.getElementById('ageChart');
    const genreChartBtn = document.getElementById('genreChartBtn');
    const ageChartBtn = document.getElementById('ageChartBtn');

    // Initialize charts if the elements exist
    if (genreChartEl && genreChartBtn && ageChartBtn) {
        const genreCtx = genreChartEl.getContext('2d');
        const ageCtx = ageChartEl.getContext('2d');

        // Initialize genre chart
        const genreChart = new Chart(genreCtx, {
            type: 'bar',
            data: chartData, // This variable should be passed from Flask
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
                }
            }
        });

        // Initialize age chart
        const ageChart = new Chart(ageCtx, {
            type: 'line',
            data: ageChartData, // This variable should be passed from Flask
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        title: {
                            display: true,
                            text: 'Age (Years)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    }
                }
            }
        });

        // Chart toggle functionality
        genreChartBtn.addEventListener('click', () => {
            genreChartEl.style.display = 'block';
            ageChartEl.style.display = 'none';
            genreChartBtn.classList.add('active');
            ageChartBtn.classList.remove('active');
        });

        ageChartBtn.addEventListener('click', () => {
            genreChartEl.style.display = 'none';
            ageChartEl.style.display = 'block';
            ageChartBtn.classList.add('active');
            genreChartBtn.classList.remove('active');
        });

        // Show genre chart by default
        genreChartBtn.click();
    }
});
