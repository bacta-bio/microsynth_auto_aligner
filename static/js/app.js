// Microsynth Auto Aligner - Frontend JavaScript

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('alignment-form');
    const logContainer = document.getElementById('log-container');
    const statusMessage = document.getElementById('status-message');
    const runBtn = document.getElementById('run-btn');
    const clearLogsBtn = document.getElementById('clear-logs-btn');
    const resultsCard = document.getElementById('results-card');
    const resultsContainer = document.getElementById('results-container');

    // Fetch logs and results periodically
    let logInterval;
    let resultsInterval;

    // Function to update logs
    function updateLogs() {
        fetch('/api/logs')
            .then(response => response.json())
            .then(data => {
                if (data.logs && data.logs.length > 0) {
                    logContainer.innerHTML = '';
                    data.logs.forEach(log => {
                        const logEntry = document.createElement('div');
                        logEntry.textContent = log;
                        logEntry.className = 'log-entry';
                        logContainer.appendChild(logEntry);
                    });
                    // Auto-scroll to bottom
                    logContainer.scrollTop = logContainer.scrollHeight;
                }
            })
            .catch(error => {
                console.error('Error fetching logs:', error);
            });
    }

    // Function to update results
    function updateResults() {
        fetch('/api/results')
            .then(response => response.json())
            .then(data => {
                console.log('DEBUG: Results data:', data);  // Console log
                if (data.results && data.results.length > 0) {
                    resultsCard.style.display = 'block';
                    resultsContainer.innerHTML = '';
                    
                    data.results.forEach(result => {
                        console.log('DEBUG: Processing result:', result);  // Console log
                        const resultEntry = document.createElement('div');
                        resultEntry.className = 'result-entry';
                        
                        if (result.success && result.alignment_id) {
                            // Create Benchling link - handle both alignment IDs and task IDs
                            const benchlingUrl = `https://app.benchling.com/nucleotide-alignments/${result.alignment_id}`;
                            resultEntry.innerHTML = `
                                <div class="result-success">
                                    <strong>${result.tube_name}</strong> - 
                                    <a href="${benchlingUrl}" target="_blank" class="benchling-link">
                                        View in Benchling
                                    </a>
                                    <span class="result-id">ID: ${result.alignment_id}</span>
                                    ${result.response_data ? `<span class="debug-info">Response: ${JSON.stringify(result.response_data)}</span>` : ''}
                                </div>
                            `;
                        } else {
                            resultEntry.innerHTML = `
                                <div class="result-error">
                                    <strong>${result.tube_name}</strong> - 
                                    <span class="error-text">Failed to create alignment</span>
                                    ${result.error ? `<span class="error-details">(${result.error})</span>` : ''}
                                    ${result.response_data ? `<span class="debug-info">Response: ${JSON.stringify(result.response_data)}</span>` : ''}
                                </div>
                            `;
                        }
                        
                        resultsContainer.appendChild(resultEntry);
                    });
                } else {
                    resultsCard.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Error fetching results:', error);
            });
    }

    // Function to show status message
    function showStatus(message, type) {
        statusMessage.textContent = message;
        statusMessage.className = `status-message ${type}`;
        statusMessage.style.display = 'block';
        
        // Auto-hide after 5 seconds for success messages
        if (type === 'success') {
            setTimeout(() => {
                statusMessage.style.display = 'none';
            }, 5000);
        }
    }

    // Function to clear status
    function clearStatus() {
        statusMessage.style.display = 'none';
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const fileInput = document.getElementById('file-upload');
        const files = fileInput.files;
        
        if (!files || files.length === 0) {
            showStatus('Please select at least one file to upload.', 'error');
            return;
        }

        // Disable button and show loading state
        runBtn.disabled = true;
        const btnText = runBtn.querySelector('.btn-text');
        const btnLoader = runBtn.querySelector('.btn-loader');
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';
        
        clearStatus();
        logContainer.innerHTML = '<div class="log-placeholder">Uploading files...</div>';

        try {
            // Step 1: Upload files
            const formData = new FormData();
            for (let file of files) {
                formData.append('files', file);
            }

            const uploadResponse = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const uploadData = await uploadResponse.json();
            
            if (!uploadData.success) {
                showStatus('✗ ' + uploadData.error, 'error');
                return;
            }

            logContainer.innerHTML = '<div class="log-placeholder">Files uploaded. Starting alignment...</div>';

            // Step 2: Run alignment
            const runResponse = await fetch('/api/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ upload_dir: uploadData.upload_dir })
            });

            const data = await runResponse.json();

            if (data.success) {
                showStatus('✓ Alignment completed successfully! Results uploaded to Benchling.', 'success');
                // Update results display
                updateResults();
            } else {
                showStatus('⚠ Alignment completed but no files were processed. Check the log for details.', 'error');
            }
        } catch (error) {
            console.error('Error running alignment:', error);
            showStatus('✗ Error running alignment: ' + error.message, 'error');
        } finally {
            // Re-enable button
            runBtn.disabled = false;
            btnText.style.display = 'inline';
            btnLoader.style.display = 'none';
            // Clear file input
            fileInput.value = '';
        }
    });

    // Clear logs button
    clearLogsBtn.addEventListener('click', () => {
        logContainer.innerHTML = '<p class="log-placeholder">Logs cleared...</p>';
    });

    // Start polling for logs and results when page loads
    logInterval = setInterval(updateLogs, 500);
    resultsInterval = setInterval(updateResults, 1000);

    // Cleanup intervals on page unload
    window.addEventListener('beforeunload', () => {
        if (logInterval) {
            clearInterval(logInterval);
        }
        if (resultsInterval) {
            clearInterval(resultsInterval);
        }
    });
});

