#!/bin/bash

# Create a backup of the original file
cp templates/student_portfolio_new_temp.html templates/student_portfolio_new_temp.html.bak

# First, fix the genre chart
cat templates/student_portfolio_new_temp.html | sed '/const genreCtx = document.getElementById/,/borderWidth: 1/{/borderWidth: 1/d;}' | sed '/const genreCtx = document.getElementById/,/}]/{/}]/d;}' > templates/student_portfolio_new_temp.html.tmp

# Second, let's fix the age chart
cat templates/student_portfolio_new_temp.html.tmp | sed '/const ageCtx = document.getElementById/,/line/{/line/s/$/,/;}' | sed '/const ageCtx = document.getElementById/i\    // Generate the age comparison chart\n    const ageCtx = document.getElementById("ageChart").getContext("2d");\n    const ageChartData = {{ age_chart_data|safe }};\n    new Chart(ageCtx, {\n        type: "line",\n        data: ageChartData,\n    });' | sed '/const ageCtx = document.getElementById/,/type: "line"/d' > templates/student_portfolio_new_temp.html.fixed

# Replace the original file with the fixed version
mv templates/student_portfolio_new_temp.html.fixed templates/student_portfolio_new_temp.html
rm templates/student_portfolio_new_temp.html.tmp