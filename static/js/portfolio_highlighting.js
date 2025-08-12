/**
 * Enhanced text highlighting for student portfolio
 * This script improves marking mode in the portfolio view
 */

// Global function for deleting writing samples
window.deleteWritingSample = function(sampleId, filename) {
    if (confirm(`Are you sure you want to delete "${filename}"?`)) {
        fetch(`/writing/${sampleId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            if (response.ok) {
                const row = document.getElementById(`row-${sampleId}`);
                if (row) {
                    row.remove();
                }
                location.reload(); // Refresh the page to update the list
            } else {
                alert('Failed to delete writing sample');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while deleting the writing sample');
        });
    }
};

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', function() {
    const toggleButtons = document.querySelectorAll('.toggle-highlight-mode');

    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const detailsContainer = this.closest('.details-row').querySelector('.p-3');
            const textElement = detailsContainer.querySelector('[id^="text-"]');
            const sampleId = textElement ? textElement.id.replace('text-', '') : null;
            const isActive = this.classList.toggle('active');

            if (isActive) {
                this.innerHTML = '<i class="fas fa-times me-1"></i> Exit Marking Mode';
                this.classList.remove('btn-outline-primary');
                this.classList.add('btn-primary');

                if (this.getAttribute('data-apply-ai-highlights') === 'true') {
                    applyHighlightsToText(textElement, sampleId);
                } else {
                    setupManualHighlighting(textElement);
                }
            } else {
                this.innerHTML = '<i class="fas fa-highlighter me-1"></i> Show Criteria Marking';
                this.classList.remove('btn-primary');
                this.classList.add('btn-outline-primary');

                if (textElement.getAttribute('data-original-content')) {
                    textElement.innerHTML = textElement.getAttribute('data-original-content');
                }
            }
        });
    });
});

/**
 * Apply highlights to text based on criteria
 */
function applyHighlightsToText(textElement, sampleId) {
    if (!textElement.getAttribute('data-original-content')) {
        textElement.setAttribute('data-original-content', textElement.innerHTML);
    }

    const originalContent = textElement.getAttribute('data-original-content');
    textElement.innerHTML = originalContent;

    const feedbackElement = document.getElementById(`feedback-${sampleId}`);
    if (!feedbackElement) return;

    const feedback = feedbackElement.textContent;
    const criteriaPattern = /criterion "([^"]+)".*?examples?:([^"]*?)(?:"|$)/gi;
    let match;

    while ((match = criteriaPattern.exec(feedback)) !== null) {
        const criterionName = match[1].trim();
        const examplesText = match[2].trim();
        const examples = examplesText.match(/"([^"]+)"/g) || [];

        examples.forEach(example => {
            const cleanExample = example.replace(/"/g, '').trim();
            if (cleanExample) {
                highlightTextInElement(textElement, cleanExample, criterionName);
            }
        });
    }
}

/**
 * Highlight specific text in an element
 */
function highlightTextInElement(element, text, criterionName) {
    if (!text || !element) return;

    const colors = {
        'vocabulary': '#c6f6d5',
        'grammar': '#bee3f8',
        'structure': '#fed7d7',
        'punctuation': '#fefcbf',
        'default': '#ffeb3b'
    };

    let color = colors.default;
    const lowerCriterion = criterionName.toLowerCase();

    if (lowerCriterion.includes('vocabulary') || lowerCriterion.includes('word')) {
        color = colors.vocabulary;
    } else if (lowerCriterion.includes('grammar') || lowerCriterion.includes('tense')) {
        color = colors.grammar;
    } else if (lowerCriterion.includes('structure') || lowerCriterion.includes('paragraph')) {
        color = colors.structure;
    } else if (lowerCriterion.includes('punctuation') || lowerCriterion.includes('comma')) {
        color = colors.punctuation;
    }

    const escapedText = text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(escapedText, 'g');
    element.innerHTML = element.innerHTML.replace(regex,
        `<span class="highlight" style="background-color: ${color};" title="${criterionName}">$&</span>`);
}

/**
 * Setup for manual highlighting
 */
function setupManualHighlighting(textElement) {
    textElement.style.userSelect = 'text';

    textElement.addEventListener('mouseup', function(event) {
        const selection = window.getSelection();
        if (selection.rangeCount > 0 && !selection.isCollapsed) {
            const range = selection.getRangeAt(0);

            if (range.toString().trim() !== '') {
                const highlightSpan = document.createElement('span');
                highlightSpan.className = 'highlight';
                highlightSpan.style.backgroundColor = '#ffeb3b';

                try {
                    range.surroundContents(highlightSpan);
                } catch (e) {
                    console.error('Highlighting error:', e);
                }

                selection.removeAllRanges();
            }
        }
    });
}