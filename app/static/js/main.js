document.addEventListener('DOMContentLoaded', function() {
    console.log('Schedule Importer main.js loaded.');

    const importForm = document.getElementById('importForm');
    const submitButton = document.getElementById('submitImportBtn');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressMessage = document.getElementById('progress-message');
    let intervalId = null;

    if (importForm) {
        importForm.addEventListener('submit', function(e) {
            // First, reset any existing progress data
            fetch('/reset_progress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(() => {
                console.log('Progress data reset successfully');
                // Show progress bar and disable button on form submission
                if (progressContainer) progressContainer.style.display = 'block';
                if (submitButton) submitButton.disabled = true;
                if (progressMessage) progressMessage.textContent = 'Initializing import...';
                if (progressBar) {
                    progressBar.style.width = '0%';
                    progressBar.textContent = '0%';
                    progressBar.classList.add('progress-bar-striped', 'progress-bar-animated');
                    progressBar.classList.remove('bg-success', 'bg-danger', 'bg-warning'); // Reset colors
                }
                // Start polling for progress
                startPollingProgress();
            })
            .catch(error => {
                console.error('Error resetting progress data:', error);
                // Continue with form submission anyway
            });
            // Don't prevent default - allow the form to submit normally
        });
    }

    function startPollingProgress() {
        if (intervalId) {
            clearInterval(intervalId); // Clear any existing interval
        }
        intervalId = setInterval(fetchProgress, 1500); // Poll every 1.5 seconds
    }

    function fetchProgress() {
        fetch('/get_import_progress')
            .then(response => response.json())
            .then(data => {
                if (progressContainer && progressBar && progressMessage) {
                    // If status is 'not_started', don't update the progress bar
                    if (data.status === 'not_started') {
                        return;
                    }
                    
                    progressMessage.textContent = data.message || 'Processing...';
                    progressBar.style.width = (data.percentage || 0) + '%';
                    progressBar.textContent = (data.percentage || 0) + '%';

                    // Update progress bar color based on status
                    progressBar.classList.remove('bg-success', 'bg-danger', 'bg-warning', 'progress-bar-striped', 'progress-bar-animated');
                    if (data.status === 'complete') {
                        progressBar.classList.add('bg-success');
                        stopPollingProgress();
                        if (submitButton) submitButton.disabled = false;
                    } else if (data.status === 'complete_with_info' || data.status === 'complete_with_warnings') {
                        progressBar.classList.add('bg-warning');
                        stopPollingProgress();
                        if (submitButton) submitButton.disabled = false;
                    } else if (data.status === 'error') {
                        progressBar.classList.add('bg-danger');
                        stopPollingProgress();
                        if (submitButton) submitButton.disabled = false;
                    } else { // Still running
                        progressBar.classList.add('progress-bar-striped', 'progress-bar-animated');
                    }
                }
            })
            .catch(error => {
                console.error('Error fetching progress:', error);
                if (progressMessage) progressMessage.textContent = 'Error fetching progress updates.';
                if (progressBar) progressBar.classList.add('bg-danger');
                stopPollingProgress(); // Stop polling on error
                if (submitButton) submitButton.disabled = false;
            });
    }

    function stopPollingProgress() {
        if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
        }
        // Keep animated class if still in progress, remove if complete/error
        if (progressBar && (progressBar.classList.contains('bg-success') || progressBar.classList.contains('bg-danger') || progressBar.classList.contains('bg-warning'))) {
            progressBar.classList.remove('progress-bar-animated');
        }
    }

    // Check if there's a flash message indicating a just-completed import
    const flashMessages = document.querySelectorAll('.alert');
    let hasCompletionMessage = false;
    
    flashMessages.forEach(message => {
        const messageText = message.textContent.toLowerCase();
        if (messageText.includes('successfully created') || 
            messageText.includes('no schedule data found') ||
            messageText.includes('error occurred during')) {
            hasCompletionMessage = true;
        }
    });

    // Only show the final state if there's a completion message
    if (hasCompletionMessage) {
        // Make a single request to get the final state
        fetch('/get_import_progress')
            .then(response => response.json())
            .then(data => {
                if (data && (data.percentage === 100 || data.status === 'complete' || 
                          data.status === 'complete_with_info' || data.status === 'complete_with_warnings' || 
                          data.status === 'error')) {
                    // If it's complete or error, just show final state
                    if (progressContainer) progressContainer.style.display = 'block';
                    if (progressMessage) progressMessage.textContent = data.message || 'Complete';
                    if (progressBar) {
                        progressBar.style.width = (data.percentage || 100) + '%';
                        progressBar.textContent = (data.percentage || 100) + '%';
                        
                        if (data.status === 'complete' || data.status === 'complete_with_info') {
                            progressBar.classList.add('bg-success');
                        } else if (data.status === 'complete_with_warnings') {
                            progressBar.classList.add('bg-warning');
                        } else if (data.status === 'error') {
                            progressBar.classList.add('bg-danger');
                        }
                    }
                }
            })
            .catch(error => {
                console.log("Could not retrieve final progress state", error);
            });
    }
});