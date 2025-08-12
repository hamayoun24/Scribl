/**
 * Completely rebuilt camera functionality for Scribl
 * This file replaces the camera functions in main.js
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("Camera.js loaded - STANDALONE implementation");

    // Cache DOM elements
    const form = document.getElementById('writingForm');
    const addImageBtn = document.getElementById('add-image-btn');
    const addMoreBtn = document.getElementById('add-more-btn');
    const imageUpload = document.getElementById('image-upload');
    const previewContainer = document.getElementById('preview-container');
    const imagePreview = document.getElementById('image-preview');
    const submitBtn = document.querySelector('button[type="submit"]');
    
    // State variables
    let imageFiles = [];
    let currentImageIndex = 0;
    
    // Navigation elements
    const prevImageBtn = document.createElement('button');
    prevImageBtn.className = 'btn btn-sm btn-secondary position-absolute start-0 top-50 translate-middle-y';
    prevImageBtn.innerHTML = '<i class="fa fa-chevron-left"></i>';
    prevImageBtn.style.display = 'none';
    
    const nextImageBtn = document.createElement('button');
    nextImageBtn.className = 'btn btn-sm btn-secondary position-absolute end-0 top-50 translate-middle-y';
    nextImageBtn.innerHTML = '<i class="fa fa-chevron-right"></i>';
    nextImageBtn.style.display = 'none';
    
    // Add navigation buttons to preview container
    if (previewContainer) {
        previewContainer.style.position = 'relative';
        previewContainer.appendChild(prevImageBtn);
        previewContainer.appendChild(nextImageBtn);
        
        // Add delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.id = 'delete-image';
        deleteBtn.className = 'btn btn-sm btn-danger position-absolute top-0 end-0 m-2';
        deleteBtn.innerHTML = '<i class="fa fa-trash"></i>';
        previewContainer.appendChild(deleteBtn);
    }
    
    // Helper functions
    function showNotification(message, type = 'success') {
        const notificationContainer = document.getElementById('notification-container') || 
                                      (() => {
                                          const container = document.createElement('div');
                                          container.id = 'notification-container';
                                          container.style.position = 'fixed';
                                          container.style.top = '20px';
                                          container.style.right = '20px';
                                          container.style.zIndex = '9999';
                                          document.body.appendChild(container);
                                          return container;
                                      })();
        
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        notificationContainer.appendChild(notification);
        
        // Auto dismiss after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    function updateImageCounter() {
        // Create counter if it doesn't exist
        let counter = document.getElementById('image-counter');
        if (!counter && previewContainer) {
            counter = document.createElement('div');
            counter.id = 'image-counter';
            counter.className = 'badge bg-primary position-absolute bottom-0 start-50 translate-middle-x mb-2';
            previewContainer.appendChild(counter);
        }
        
        if (counter) {
            counter.textContent = `${currentImageIndex + 1} / ${imageFiles.length}`;
            counter.style.display = imageFiles.length > 1 ? 'block' : 'none';
        }
    }
    
    function updateUIAfterImageCapture() {
        // Reset form and preview
        if (form) form.reset();
        if (previewContainer) previewContainer.classList.add('d-none');
        
        // Update buttons visibility
        if (prevImageBtn) prevImageBtn.style.display = 'none';
        if (nextImageBtn) nextImageBtn.style.display = 'none';
        
        // Disable submit button
        if (submitBtn) submitBtn.disabled = true;
    }
    
    // Flag to prevent auto-reopening
    let cameraCaptureInProgress = false;
    
    // TOTAL REPLACEMENT CAMERA FUNCTIONALITY
    // Completely new implementation to forcibly prevent reopening
    function triggerCamera() {
        console.log("Activating camera with EXTREME PREJUDICE approach");
        
        // Don't reopen camera if we're already processing an image
        if (cameraCaptureInProgress) {
            console.log("Camera capture already in progress - ignoring request");
            return;
        }
        
        // Set flag to prevent reopening
        cameraCaptureInProgress = true;
        
        // CRITICAL: Create input directly in document body, completely detached
        // from the form to prevent any form-related reopening
        
        // Remove only camera-related file inputs but keep the standard form input
        const oldCameraInput = document.getElementById('one-time-camera-input');
        if (oldCameraInput) {
            oldCameraInput.remove();
        }
        
        // Create a brand new input with no history
        const cameraInput = document.createElement('input');
        cameraInput.type = 'file';
        cameraInput.id = 'one-time-camera-input'; // Unique ID to avoid conflicts
        cameraInput.style.display = 'none';
        cameraInput.accept = 'image/*';
        cameraInput.setAttribute('capture', 'environment');
        
        // EXTREMELY CRITICAL: Only capture one image at a time
        cameraInput.removeAttribute('multiple');
        
        // Add to document body instead of the form
        document.body.appendChild(cameraInput);
        
        // Add one-time event listener
        cameraInput.addEventListener('change', function singleUseHandler(e) {
            if (e.target.files && e.target.files.length > 0) {
                console.log("Camera capture successful with standalone camera");
                
                // IMMEDIATE destruction of the input to prevent any possibility of reopening
                setTimeout(() => {
                    try {
                        // Process files first
                        handleCameraCapture(e);
                        
                        // Then destroy the input element completely
                        cameraInput.value = ''; // Clear value first
                        cameraInput.removeEventListener('change', singleUseHandler);
                        cameraInput.remove(); // Remove from DOM
                        
                        console.log("Camera element completely destroyed");
                    } catch (error) {
                        console.error("Error in camera handler:", error);
                    }
                    
                    // Reset flag to allow future captures
                    cameraCaptureInProgress = false;
                }, 200);
            } else {
                // No image captured, reset state
                cameraInput.remove();
                cameraCaptureInProgress = false;
            }
        });
        
        // Trigger camera after a very short delay
        setTimeout(() => {
            try {
                cameraInput.click();
                console.log("One-time camera opened");
            } catch (error) {
                console.error("Error opening camera:", error);
                cameraInput.remove();
                cameraCaptureInProgress = false;
            }
        }, 100);
    }
    
    // Handler for camera capture events
    function handleCameraCapture(e) {
        if (e.target.files && e.target.files.length > 0) {
            console.log("Camera capture successful, files count:", e.target.files.length);
            
            // Process captured images
            const newFiles = Array.from(e.target.files);
            
            try {
                newFiles.forEach(file => {
                    console.log("Processing file:", file.name);
                    const imageUrl = URL.createObjectURL(file);
                    
                    imageFiles.push({
                        file: file,
                        url: imageUrl
                    });
                });
                
                // Update current index to show latest image
                currentImageIndex = imageFiles.length - 1;
                
                // Update UI
                if (imagePreview && imageFiles[currentImageIndex]) {
                    imagePreview.src = imageFiles[currentImageIndex].url;
                    previewContainer.classList.remove('d-none');
                }
                
                // Show/hide navigation buttons
                if (prevImageBtn && nextImageBtn) {
                    prevImageBtn.style.display = imageFiles.length > 1 ? 'block' : 'none';
                    nextImageBtn.style.display = imageFiles.length > 1 ? 'block' : 'none';
                }
                
                // Enable submit button
                if (submitBtn) {
                    submitBtn.disabled = false;
                }
                
                // Update counter
                updateImageCounter();
                
                // Show success notification - explicitly prevent page refresh with return false
                showNotification(`${newFiles.length} image(s) added successfully!`);
                
                // CRITICAL: Prevent any form submission or page reload
                if (e && e.preventDefault) {
                    e.preventDefault();
                    e.stopPropagation(); 
                }
                
                // Stop any auto form submission or page refresh
                return false;
                
            } catch (error) {
                console.error("Error processing camera capture:", error);
                showNotification("Error processing images. Please try again.", "danger");
            }
        }
    }
    
    // Event Listeners
    if (addImageBtn) {
        addImageBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log("Add image button clicked");
            triggerCamera();
        });
    }
    
    if (addMoreBtn) {
        addMoreBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log("Add more button clicked");
            triggerCamera();
        });
    }
    
    // Navigation buttons
    if (prevImageBtn) {
        prevImageBtn.addEventListener('click', () => {
            if (currentImageIndex > 0) {
                currentImageIndex--;
                imagePreview.src = imageFiles[currentImageIndex].url;
                updateImageCounter();
            }
        });
    }
    
    if (nextImageBtn) {
        nextImageBtn.addEventListener('click', () => {
            if (currentImageIndex < imageFiles.length - 1) {
                currentImageIndex++;
                imagePreview.src = imageFiles[currentImageIndex].url;
                updateImageCounter();
            }
        });
    }
    
    // Delete functionality
    const deleteImageBtn = document.getElementById('delete-image');
    if (deleteImageBtn) {
        deleteImageBtn.addEventListener('click', (e) => {
            e.preventDefault();
            
            if (imageFiles.length > 0) {
                // Revoke URL to free memory
                URL.revokeObjectURL(imageFiles[currentImageIndex].url);
                
                // Remove current image
                imageFiles.splice(currentImageIndex, 1);
                
                if (imageFiles.length === 0) {
                    // No images left
                    previewContainer.classList.add('d-none');
                    currentImageIndex = 0;
                    if (submitBtn) submitBtn.disabled = true;
                } else {
                    // Adjust current index if needed
                    currentImageIndex = Math.min(currentImageIndex, imageFiles.length - 1);
                    imagePreview.src = imageFiles[currentImageIndex].url;
                }
                
                // Update navigation
                if (prevImageBtn && nextImageBtn) {
                    prevImageBtn.style.display = imageFiles.length > 1 ? 'block' : 'none';
                    nextImageBtn.style.display = imageFiles.length > 1 ? 'block' : 'none';
                }
                
                updateImageCounter();
            }
        });
    }
    
    // Form submission
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (imageFiles.length === 0) {
                showNotification('Please take at least one photo or upload an image.', 'warning');
                return;
            }
            
            // Get form data
            const formData = new FormData();
            
            // Add all captured images
            imageFiles.forEach((imageData) => {
                formData.append('image', imageData.file);
            });
            
            // Add student and assignment IDs
            const studentSelect = document.getElementById('student-select') || document.getElementById('student_id');
            const assignmentSelect = document.getElementById('assignment-select') || document.getElementById('assignment_id');
            
            if (studentSelect && !studentSelect.value) {
                showNotification('Please select a student.', 'warning');
                return;
            }
            
            if (studentSelect) {
                formData.append('student_id', studentSelect.value);
            }
            
            if (assignmentSelect && assignmentSelect.value) {
                formData.append('assignment_id', assignmentSelect.value);
            }
            
            // Disable submit button and show loading state
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Processing...';
            
            try {
                // Submit to server
                const response = await fetch('/process_image', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showNotification('Images processed successfully!');
                    // Redirect to results page
                    window.location.href = `/writing/${result.writing_id}`;
                } else {
                    showNotification(result.error || 'Failed to process images.', 'danger');
                    // Reset button state
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fa fa-check me-2"></i>Process Images';
                }
            } catch (error) {
                console.error('Error submitting form:', error);
                showNotification('An error occurred while processing the images.', 'danger');
                // Reset button state
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fa fa-check me-2"></i>Process Images';
            }
        });
    }
    
    // Class/Student selection handlers
    const classSelect = document.getElementById('class_id');
    
    if (classSelect) {
        classSelect.addEventListener('change', async function() {
            const classId = this.value;
            const studentSelect = document.getElementById('student_id');
            const assignmentSelect = document.getElementById('assignment_id');
            
            if (!classId) {
                // Reset and disable dependent dropdowns
                if (studentSelect) {
                    studentSelect.innerHTML = '<option value="">Choose a student...</option>';
                    studentSelect.disabled = true;
                }
                
                if (assignmentSelect) {
                    assignmentSelect.innerHTML = '<option value="">No assignment - free writing</option>';
                    assignmentSelect.disabled = true;
                }
                
                return;
            }
            
            try {
                // Fetch students for selected class
                const studentsResponse = await fetch(`/get_students/${classId}`);
                const students = await studentsResponse.json();
                
                if (studentSelect) {
                    // Enable and populate student dropdown
                    studentSelect.disabled = false;
                    studentSelect.innerHTML = '<option value="">Choose a student...</option>';
                    
                    students.forEach(student => {
                        const option = document.createElement('option');
                        option.value = student.id;
                        option.textContent = student.name;
                        option.style.backgroundColor = 'white';
                        option.style.color = 'black';
                        studentSelect.appendChild(option);
                    });
                }
                
                // Fetch assignments for selected class
                const assignmentsResponse = await fetch(`/get_assignments/${classId}`);
                const assignments = await assignmentsResponse.json();
                
                if (assignmentSelect) {
                    // Enable and populate assignment dropdown
                    assignmentSelect.disabled = false;
                    assignmentSelect.innerHTML = '<option value="">No assignment - free writing</option>';
                    
                    assignments.forEach(assignment => {
                        const option = document.createElement('option');
                        option.value = assignment.id;
                        option.textContent = `${assignment.title} (${assignment.genre})`;
                        option.style.backgroundColor = 'white';
                        option.style.color = 'black';
                        assignmentSelect.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('Error fetching class data:', error);
                showNotification('Error loading class data. Please try again.', 'danger');
            }
        });
    }
    
    // Auto-trigger class selection if value exists
    if (classSelect && classSelect.value) {
        const event = new Event('change');
        classSelect.dispatchEvent(event);
    }
});