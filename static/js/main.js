document.addEventListener('DOMContentLoaded', function() {
    // Basic initialization - no redirects
    console.log("Main.js loaded - using standard camera functionality");
    
    // Initialize UI elements - supporting both index.html and add_writing.html
    const form = document.getElementById('upload-form') || document.getElementById('writingForm');
    if (!form) {
        console.warn('Image upload form not found on this page');
        return; // Exit early if the form isn't found on this page
    }

    const addImageBtn = document.getElementById('add-image-btn');
    const imageUpload = document.getElementById('image-upload');
    const previewContainer = document.getElementById('preview-container');
    const imagePreview = document.getElementById('preview-image') || document.getElementById('image-preview');
    const imageCounter = document.querySelector('.images-indicator');
    const prevImageBtn = document.getElementById('prev-image');
    const nextImageBtn = document.getElementById('next-image');
    const submitBtn = form.querySelector('button[type="submit"]');
    const addMoreBtn = document.getElementById('add-more-btn');

    let imageFiles = [];
    let currentImageIndex = 0;

    function showNotification(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success alert-dismissible fade show';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        form.insertBefore(alertDiv, form.firstChild);
        setTimeout(() => alertDiv.remove(), 3000);
    }

    function updateImageCounter() {
        if (imageCounter) {
            imageCounter.textContent = `Image ${currentImageIndex + 1} of ${imageFiles.length}`;
        }
        if (prevImageBtn) {
            prevImageBtn.disabled = currentImageIndex === 0;
        }
        if (nextImageBtn) {
            nextImageBtn.disabled = currentImageIndex === imageFiles.length - 1;
        }
    }

    function updateUIAfterImageCapture() {
        if (imageFiles.length > 0) {
            if (previewContainer) {
                previewContainer.classList.remove('d-none');
            }
            if (submitBtn) {
                submitBtn.disabled = false;
            }
            updateImageCounter();
        } else {
            if (previewContainer) {
                previewContainer.classList.add('d-none');
            }
            if (submitBtn) {
                submitBtn.disabled = true;
            }
        }
    }

    // AUTO-RETRY CAMERA SYSTEM
    let cameraRetryAttempts = 0;
    const MAX_RETRY_ATTEMPTS = 3;
    let cameraOpenedTimestamp = 0;
    
    function triggerCamera() {
        // Reset the file input to ensure change event fires
        if (imageUpload) {
            console.log("Preparing camera...");
            imageUpload.value = '';
        }
        
        // Use timeout to ensure proper event handling
        setTimeout(() => {
            if (imageUpload) {
                console.log("Opening camera, attempt #" + (cameraRetryAttempts + 1));
                cameraOpenedTimestamp = Date.now();
                
                // Create and dispatch click event
                const clickEvent = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                });
                
                imageUpload.dispatchEvent(clickEvent);
                console.log("Camera dialog triggered");
                
                // Set up auto-retry if no image is captured within 3 seconds
                setTimeout(() => {
                    if (Date.now() - cameraOpenedTimestamp > 2000 && 
                        !imageFiles.length && 
                        cameraRetryAttempts < MAX_RETRY_ATTEMPTS) {
                        
                        cameraRetryAttempts++;
                        console.log("No image captured, auto-retrying (" + cameraRetryAttempts + "/" + MAX_RETRY_ATTEMPTS + ")");
                        triggerCamera();
                    }
                }, 3000);
            }
        }, 50);
    }
    
    // Event Listeners
    if (addImageBtn) {
        addImageBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log("Add image button clicked");
            cameraRetryAttempts = 0;
            triggerCamera();
        });
    }

    if (addMoreBtn) {
        addMoreBtn.addEventListener('click', (e) => {
            e.preventDefault();
            console.log("Add more button clicked");
            
            // Use same auto-retry function
            cameraRetryAttempts = 0;
            triggerCamera();
        });
    }

    if (imageUpload) {
        imageUpload.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                // Clear any error messages
                const errorMessages = document.querySelectorAll('.alert-danger');
                errorMessages.forEach(msg => msg.classList.add('d-none'));

                // Add new images to array and handle them immediately
                const newFiles = Array.from(e.target.files);
                console.log("Camera capture - files count:", newFiles.length);
                
                try {
                    // Process files directly for simplicity
                    newFiles.forEach(file => {
                        console.log("Processing file:", file.name);
                        try {
                            const imageUrl = URL.createObjectURL(file);
                            console.log("URL created successfully:", imageUrl.slice(0, 30) + "...");
                            
                            imageFiles.push({
                                file: file,
                                url: imageUrl
                            });
                        } catch (err) {
                            console.error("Error creating URL for file:", err);
                        }
                    });
                    
                    // Update current index to show latest image
                    currentImageIndex = imageFiles.length - 1;
                    console.log("Current image index set to:", currentImageIndex);

                    // Update preview immediately to avoid delays
                    if (imagePreview && imageFiles[currentImageIndex]) {
                        console.log("Setting image preview src");
                        imagePreview.src = imageFiles[currentImageIndex].url;
                        previewContainer.classList.remove('d-none');
                    } else {
                        console.warn("Could not update preview - missing elements or files");
                        console.log("imagePreview exists:", !!imagePreview);
                        console.log("imageFiles length:", imageFiles.length);
                    }

                    // Show/hide navigation buttons
                    if (prevImageBtn && nextImageBtn) {
                        prevImageBtn.style.display = imageFiles.length > 1 ? 'block' : 'none';
                        nextImageBtn.style.display = imageFiles.length > 1 ? 'block' : 'none';
                    }

                    // Enable submit button
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        console.log("Submit button enabled");
                    }

                    // Show notification and update UI
                    showNotification(`${newFiles.length} image(s) added successfully!`);
                    console.log("Notification shown");
                    
                    updateImageCounter();
                } catch (error) {
                    console.error("Error in file processing:", error);
                }

                // Reset file input immediately
                imageUpload.value = '';
            }
        });
    }

    // Update navigation handlers - using prevImageBtn and nextImageBtn only

    if (prevImageBtn) {
        prevImageBtn.addEventListener('click', () => {
            currentImageIndex = Math.max(0, currentImageIndex - 1);
            if (imageFiles[currentImageIndex] && imageFiles[currentImageIndex].url) {
                imagePreview.src = imageFiles[currentImageIndex].url;
            }
            updateImageCounter();
        });
    }

    if (nextImageBtn) {
        nextImageBtn.addEventListener('click', () => {
            currentImageIndex = Math.min(imageFiles.length - 1, currentImageIndex + 1);
            if (imageFiles[currentImageIndex] && imageFiles[currentImageIndex].url) {
                imagePreview.src = imageFiles[currentImageIndex].url;
            }
            updateImageCounter();
        });
    }

    // Form submission
    // Add delete functionality
    const deleteImageBtn = document.getElementById('delete-image');
    if (deleteImageBtn) {
        deleteImageBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (imageFiles.length > 0) {
                // Revoke the URL to free up memory
                URL.revokeObjectURL(imageFiles[currentImageIndex].url);
                
                // Remove the current image
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

    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            if (imageFiles.length === 0) {
                showNotification('Please take at least one photo or upload an image.');
                return;
            }

            const formData = new FormData();
            imageFiles.forEach((imageData, index) => {
                formData.append('image', imageData.file);
            });

            const studentSelect = document.getElementById('student-select');
            const assignmentSelect = document.getElementById('assignment-select');

            if (studentSelect && !studentSelect.value) {
                showNotification('Please select a student.');
                return;
            }

            if (studentSelect) {
                formData.append('student_id', studentSelect.value);
            }

            if (assignmentSelect && assignmentSelect.value) {
                formData.append('assignment_id', assignmentSelect.value);
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Processing...';

            try {
                const response = await fetch('/process_image', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok) {
                    showNotification('Images processed successfully!');
                    imageFiles = [];
                    currentImageIndex = 0;
                    updateUIAfterImageCapture();
                    window.location.href = `/writing/${result.writing_id}`;
                } else {
                    showNotification(result.error || 'Failed to process images.');
                }
            } catch (error) {
                showNotification('An error occurred while processing the images.');
                console.error('Upload error:', error);
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fa fa-check me-2"></i>Process Images';
            }
        });
    }
});