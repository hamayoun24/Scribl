/**
 * Displays educational teaching tips during processing
 * Requires the teaching_tips.js file to be loaded first
 * Expects HTML elements with IDs: tip-content, tip-reference, teaching-tip
 */
// Function to display random teaching tips during processing
function displayRandomTeachingTip() {
    const tipContent = document.getElementById('tip-content');
    const tipReference = document.getElementById('tip-reference');
    const teachingTipContainer = document.getElementById('teaching-tip');
    
    if (tipContent && teachingTipContainer) {
        // Select a random tip from the array
        const randomIndex = Math.floor(Math.random() * teachingTips.length);
        const selectedTip = teachingTips[randomIndex];
        
        tipContent.textContent = selectedTip.text;
        
        // Set the reference if the element exists
        if (tipReference) {
            tipReference.textContent = selectedTip.reference;
        }
        
        // Show the teaching tip
        teachingTipContainer.classList.remove('d-none');
    }
}
