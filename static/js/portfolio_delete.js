// Delete writing sample with confirmation
window.deleteWritingSample = function(id, filename) {
    if (confirm('Are you sure you want to delete "' + filename + '"? This action cannot be undone.')) {
        fetch('/writing/' + id + '/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(function(response) {
            if (response.ok) {
                // Reload the page to reflect the changes
                window.location.reload();
            } else {
                alert('Failed to delete writing sample');
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
            alert('An error occurred while deleting the writing sample');
        });
    }
};
