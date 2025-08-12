import re

# Read the original file
with open('templates/student_portfolio_new_temp.html', 'r') as f:
    content = f.read()

# Fix the genre chart section
genre_pattern = re.compile(r'// Generate the genre chart.*?const genreCtx.*?data: {.*?labels:.*?datasets:.*?}].*?,', re.DOTALL)
genre_replacement = '''// Generate the genre chart
    const genreCtx = document.getElementById('genreChart').getContext('2d');
    const chartData = {{ chart_data|safe }};
    new Chart(genreCtx, {
        type: 'bar',
        data: chartData,'''

content = genre_pattern.sub(genre_replacement, content)

# Fix the age chart section
age_pattern = re.compile(r'// Generate the age comparison chart.*?const ageCtx.*?data: {.*?labels:.*?datasets:.*?}].*?,', re.DOTALL)
age_replacement = '''// Generate the age comparison chart
    const ageCtx = document.getElementById('ageChart').getContext('2d');
    const ageChartData = {{ age_chart_data|safe }};
    new Chart(ageCtx, {
        type: 'line',
        data: ageChartData,'''

content = age_pattern.sub(age_replacement, content)

# Write the corrected content to the file
with open('templates/student_portfolio_new_temp.html', 'w') as f:
    f.write(content)

print("File updated successfully!")