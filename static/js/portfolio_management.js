// Individual sample deletion
function deleteWritingSample(sampleId, filename) {
    if (confirm(`Are you sure you want to delete "${filename}"?`)) {
        fetch(`/writing/${sampleId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            if (response.ok) {
                window.location.reload();
            } else {
                alert('Failed to delete writing sample');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while deleting the writing sample');
        });
    }
}

// Initialize bulk delete functionality
document.addEventListener('DOMContentLoaded', function() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const writingCheckboxes = document.querySelectorAll('.writing-checkbox');
    const deleteSelectedBtn = document.querySelector('.delete-selected');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            writingCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateDeleteButton();
        });
    }

    writingCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateDeleteButton);
    });

    function updateDeleteButton() {
        const checkedBoxes = document.querySelectorAll('.writing-checkbox:checked');
        if (deleteSelectedBtn) {
            deleteSelectedBtn.disabled = checkedBoxes.length === 0;
        }
        if (bulkDeleteBtn) {
            bulkDeleteBtn.disabled = checkedBoxes.length === 0;
        }
    }

    // Initialize button state
    updateDeleteButton();
});