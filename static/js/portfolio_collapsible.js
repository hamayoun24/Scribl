
document.addEventListener('DOMContentLoaded', function() {
    // Initialize collapsible functionality for writing samples
    setupCollapsibleSamples();
    
    function setupCollapsibleSamples() {
        const toggleButtons = document.querySelectorAll('[data-bs-toggle="collapse"]');
        
        toggleButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const targetId = this.getAttribute('data-bs-target');
                const detailsSection = document.querySelector(targetId);
                const icon = this.querySelector('i');
                
                if (detailsSection) {
                    if (detailsSection.classList.contains('show')) {
                        detailsSection.classList.remove('show');
                        if (icon) {
                            icon.classList.remove('fa-chevron-up');
                            icon.classList.add('fa-chevron-down');
                        }
                    } else {
                        detailsSection.classList.add('show');
                        if (icon) {
                            icon.classList.remove('fa-chevron-down');
                            icon.classList.add('fa-chevron-up');
                        }
                        
                        // Get the sample ID from the button's parent
                        const sampleId = this.closest('.btn-group').getAttribute('data-sample-id');
                        if (sampleId) {
                            populateAnalysisData(sampleId);
                        }
                    }
                }
            });
        });
    }
    
    function populateAnalysisData(sampleId) {
        if (!sampleId) return;
        
        const strengthsList = document.getElementById(`strengths-list-${sampleId}`);
        const developmentList = document.getElementById(`development-list-${sampleId}`);
        
        // Check if lists exist and are empty
        if (strengthsList && strengthsList.children.length === 0 && 
            developmentList && developmentList.children.length === 0) {
            
            // Get the feedback from the hidden field
            const feedbackElement = document.getElementById(`feedback-${sampleId}`);
            if (feedbackElement && feedbackElement.textContent) {
                const feedback = feedbackElement.textContent;
                
                // Extract strengths section
                const strengthsMatch = feedback.match(/Strengths:([\s\S]*?)(?:Areas for Development:|$)/i);
                if (strengthsMatch && strengthsList) {
                    const strengthsText = strengthsMatch[1].trim();
                    const strengthsPoints = strengthsText.split('\n')
                        .map(point => point.trim().replace(/^-\s*/, ''))
                        .filter(point => point.length > 0);
                    
                    // Add each strength point as a list item
                    strengthsPoints.forEach(point => {
                        const li = document.createElement('li');
                        li.className = 'list-group-item';
                        li.textContent = point;
                        strengthsList.appendChild(li);
                    });
                    
                    // If no strengths were found, add a message
                    if (strengthsList.children.length === 0) {
                        const li = document.createElement('li');
                        li.className = 'list-group-item';
                        li.textContent = 'No specific strengths identified.';
                        strengthsList.appendChild(li);
                    }
                }
                
                // Extract development section
                const developmentMatch = feedback.match(/Areas for Development:([\s\S]*?)(?:Writing Age:|$)/i);
                if (developmentMatch && developmentList) {
                    const developmentText = developmentMatch[1].trim();
                    const developmentPoints = developmentText.split('\n')
                        .map(point => point.trim().replace(/^-\s*/, ''))
                        .filter(point => point.length > 0);
                    
                    // Add each development point as a list item
                    developmentPoints.forEach(point => {
                        const li = document.createElement('li');
                        li.className = 'list-group-item';
                        li.textContent = point;
                        developmentList.appendChild(li);
                    });
                    
                    // If no development areas were found, add a message
                    if (developmentList.children.length === 0) {
                        const li = document.createElement('li');
                        li.className = 'list-group-item';
                        li.textContent = 'No specific areas for development identified.';
                        developmentList.appendChild(li);
                    }
                }
            }
        }
    }
    
    // Make the function globally available
    window.populateAnalysisData = populateAnalysisData;
});
