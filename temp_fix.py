with open('templates/student_portfolio_new_temp.html', 'r') as file:
    content = file.read()

fixed_content = content.replace('''                                            <div class="d-flex align-items-center">
                                                <div class="h3 mb-0">{{ total_mark }}%</div>
                                            </div>
                                    </td>''', '''                                            <div class="d-flex align-items-center">
                                                <div class="h3 mb-0">{{ total_mark }}%</div>
                                            </div>
                                        {% else %}
                                            <div class="text-muted">No marks</div>
                                        {% endif %}
                                    </td>''')

with open('templates/student_portfolio_new_temp.html', 'w') as file:
    file.write(fixed_content)

print("File updated successfully!")
