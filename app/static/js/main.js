document.addEventListener('DOMContentLoaded', function() {
    console.log('Mosaic Sync main.js loaded.');

    // Form and progress elements
    const importForm = document.getElementById('importForm');
    const submitButton = document.getElementById('submitImportBtn');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressMessage = document.getElementById('progress-message');
    let progressIntervalId = null;

    const calendarSelect = document.getElementById('calendar_id');
    const calendarLoadError = document.getElementById('calendar-load-error');

    // Background grid animation (subtle movement)
    const body = document.querySelector('body');
    if (body) {
        let posX = 0;
        let posY = 0;
        setInterval(() => {
            posX += 0.05;
            posY += 0.05;
            body.style.backgroundPosition = `${posX}px ${posY}px`;
        }, 50);
    }

    // Function to fetch and update progress
    async function fetchProgress() {
        try {
            const response = await fetch("/get_import_progress");
            if (!response.ok) {
                console.error('Failed to fetch progress', response.status);
                if (progressMessage) progressMessage.textContent = 'Error fetching progress.';
                return;
            }
            const data = await response.json();

            if (progressBar) {
                const roundedProgress = Math.floor(data.percentage || 0);
                progressBar.style.width = roundedProgress + '%';
                progressBar.textContent = roundedProgress + '%';
                progressBar.setAttribute('aria-valuenow', roundedProgress);
                // Ensure no error class persists if we are now processing or completed successfully
                if (data.status !== 'error') {
                    progressBar.classList.remove('bg-danger');
                }
            }
            if (progressMessage) {
                progressMessage.textContent = data.message || 'Processing...';
            }

            // Check for terminal states to stop polling
            // Ensure these strings exactly match the statuses sent by task_manager.py
            const terminalSuccessStates = ['complete', 'complete_with_info', 'complete_with_warnings']; // Changed 'completed' to 'complete'
            const terminalErrorStates = ['error'];
            const terminalStates = [...terminalSuccessStates, ...terminalErrorStates];

            if (terminalStates.includes(data.status)) {
                clearInterval(progressIntervalId);
                
                if (terminalSuccessStates.includes(data.status)) {
                    if (progressMessage) progressMessage.textContent = data.message || 'Import complete!';
                    if (progressBar) {
                        progressBar.style.width = '100%';
                        progressBar.textContent = '100%';
                        progressBar.setAttribute('aria-valuenow', '100');
                        progressBar.classList.remove('bg-danger'); // Ensure no error style
                        progressBar.classList.add('bg-success');
                    }
                    if (submitButton) {
                        submitButton.disabled = false;
                        submitButton.innerHTML = '<i class="fas fa-check-circle mr-2"></i> Done!';
                    }
                } else { // Error state
                    if (progressMessage) progressMessage.textContent = data.message || 'An error occurred.';
                    if (progressBar) {
                        progressBar.classList.add('bg-danger');
                        progressBar.classList.remove('bg-success');
                    }
                    if (submitButton) {
                        submitButton.disabled = false;
                        submitButton.innerHTML = '<i class="fas fa-exclamation-triangle mr-2"></i> Import Failed';
                    }
                }

                // Optionally hide progress bar and reset button after a delay
                setTimeout(() => {
                    if (progressContainer) progressContainer.style.display = 'none';
                    if (progressBar) {
                        progressBar.style.width = '0%';
                        progressBar.textContent = '0%';
                        progressBar.setAttribute('aria-valuenow', '0');
                        progressBar.classList.remove('bg-success', 'bg-danger');
                    }
                    if (submitButton) { // Reset button for another import
                        submitButton.innerHTML = '<i class="fas fa-sync mr-2"></i> Import Schedule';
                    }
                }, 5000);

            } else if (data.status === 'not_started' && progressContainer.style.display === 'block') {
                console.log("Progress status: not_started, but UI was active. Continuing to poll.");
            }
        } catch (error) {
            console.error('Error in fetchProgress:', error);
            if (progressMessage) progressMessage.textContent = 'Failed to update progress.';
        }
    }

    // Function to load calendars into the dropdown
    async function loadCalendars() {
        if (!calendarSelect) return; // Should not happen if gcal is authorized, as element is conditional

        // Check if calendars are pre-populated by the template.
        // The template adds a "Loading..." option first, then actual calendars.
        if (calendarSelect.options.length > 1 && 
            calendarSelect.options[0].value === "" && 
            calendarSelect.options[0].disabled) {
            
            console.log('Calendars pre-populated by template. Removing placeholder.');
            calendarSelect.remove(0); // Remove the "Loading calendars..." placeholder

            // Ensure an option is selected if the template didn't explicitly select one
            // (e.g., no "primary" calendar was found by the template).
            if (calendarSelect.options.length > 0 && calendarSelect.selectedIndex === -1) {
                calendarSelect.options[0].selected = true;
            }
            return; // Calendars are already loaded and placeholder removed.
        }

        // If not pre-populated (or only placeholder exists), fetch them.
        console.log('Fetching calendars dynamically...');
        try {
            const response = await fetch('/get_calendars');
            const data = await response.json();

            // Clear existing options (e.g., "Loading..." or error messages)
            calendarSelect.innerHTML = ''; 

            if (response.ok && data.status === 'success') {
                if (data.calendars.length === 0) {
                    const option = new Option('No calendars found in your account.', '');
                    option.disabled = true;
                    option.selected = true;
                    calendarSelect.add(option);
                    if (calendarLoadError) {
                        calendarLoadError.textContent = 'No calendars found. Please ensure you have calendars in your Google account.';
                        calendarLoadError.style.display = 'block';
                    }
                } else {
                    let primarySelected = false;
                    data.calendars.forEach(calendar => {
                        const option = new Option(calendar.summary, calendar.id);
                        calendarSelect.add(option);
                        if (calendar.id === 'primary') {
                            option.selected = true;
                            primarySelected = true;
                        }
                    });
                    if (!primarySelected && data.calendars.length > 0) {
                        calendarSelect.options[0].selected = true; // Select the first one if primary not found
                    }
                    if (calendarLoadError) calendarLoadError.style.display = 'none';
                }
            } else {
                console.error('Failed to load calendars:', data.message);
                const errorOption = new Option('Error loading calendars', '');
                errorOption.disabled = true;
                errorOption.selected = true;
                calendarSelect.add(errorOption);
                if (calendarLoadError) {
                    calendarLoadError.textContent = data.message || 'Could not load calendars. Please try re-authorizing or refresh.';
                    calendarLoadError.style.display = 'block';
                }
            }
        } catch (error) {
            console.error('Error fetching calendars:', error);
            calendarSelect.innerHTML = ''; // Clear again
            const catchErrorOption = new Option('Error fetching calendars', '');
            catchErrorOption.disabled = true;
            catchErrorOption.selected = true;
            calendarSelect.add(catchErrorOption);
            if (calendarLoadError) {
                calendarLoadError.textContent = 'An unexpected error occurred while fetching calendars.';
                calendarLoadError.style.display = 'block';
            }
        }
    }

    // Form submission and progress tracking
    if (importForm) {
        importForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            if (progressContainer) progressContainer.style.display = 'block';
            if (progressBar) {
                progressBar.style.width = '0%';
                progressBar.textContent = '0%';
                progressBar.setAttribute('aria-valuenow', '0');
                progressBar.classList.remove('bg-success', 'bg-danger');
            }
            if (progressMessage) progressMessage.textContent = 'Initializing import...';
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Processing...';
            }

            try {
                const resetResponse = await fetch('/reset_progress', { method: 'POST' });
                if (!resetResponse.ok) {
                    const errorData = await resetResponse.json();
                    throw new Error(errorData.message || 'Failed to reset import session.');
                }
                console.log("Import session reset successfully.");

                const formData = new FormData(importForm);
                const importResponse = await fetch(importForm.action, {
                    method: 'POST',
                    body: formData
                });

                const importResult = await importResponse.json();

                if (importResponse.ok && importResult.status === 'success') {
                    if (progressMessage) progressMessage.textContent = importResult.message || 'Import initiated. Fetching progress...';
                    clearInterval(progressIntervalId);
                    progressIntervalId = setInterval(fetchProgress, 1500);
                    fetchProgress();
                } else {
                    throw new Error(importResult.message || 'Failed to start import process.');
                }
            } catch (error) {
                console.error('Form submission error:', error);
                if (progressMessage) progressMessage.textContent = error.message || 'Error starting import.';
                if (progressBar) progressBar.classList.add('bg-danger');
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = '<i class="fas fa-exclamation-triangle mr-2"></i> Import Failed';
                }
                if (progressContainer) {
                    setTimeout(() => {
                        progressContainer.style.display = 'none';
                        if (progressBar) {
                            progressBar.style.width = '0%';
                            progressBar.textContent = '0%';
                            progressBar.setAttribute('aria-valuenow', '0');
                            progressBar.classList.remove('bg-danger');
                        }
                    }, 5000);
                }
            }
        });
    }

    // Enhance form field interactions
    const formControls = document.querySelectorAll('.form-control');
    formControls.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('input-focus');
        });

        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('input-focus');
        });

        if (input.type === 'password') {
            const toggleBtn = input.parentElement.querySelector('.password-toggle');
            if (toggleBtn) {
                toggleBtn.addEventListener('click', function() {
                    if (input.type === 'password') {
                        input.type = 'text';
                        this.querySelector('i').className = 'fas fa-eye-slash';
                    } else {
                        input.type = 'password';
                        this.querySelector('i').className = 'fas fa-eye';
                    }
                });
            }
        }
    });

    // Date range validation
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');

    if (startDateInput && endDateInput) {
        startDateInput.addEventListener('change', validateDateRange);
        endDateInput.addEventListener('change', validateDateRange);

        function validateDateRange() {
            const startDate = new Date(startDateInput.value);
            const endDate = new Date(endDateInput.value);

            if (startDate > endDate) {
                endDateInput.setCustomValidity('End date must be after start date');

                if (!document.querySelector('.date-error-message')) {
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'text-danger small mt-2 date-error-message';
                    errorMsg.innerHTML = '<i class="fas fa-exclamation-circle mr-1"></i> End date must be after start date';
                    endDateInput.parentElement.appendChild(errorMsg);
                }
            } else {
                endDateInput.setCustomValidity('');
                const errorMsg = document.querySelector('.date-error-message');
                if (errorMsg) errorMsg.remove();
            }
        }
    }

    // Initial actions on page load
    if (calendarSelect) { 
        loadCalendars();
    }
});