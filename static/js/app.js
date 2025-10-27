// Microsynth Auto Aligner - Frontend JavaScript

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('alignment-form');
    const logContainer = document.getElementById('log-container');
    const statusMessage = document.getElementById('status-message');
    const runBtn = document.getElementById('run-btn');
    const clearLogsBtn = document.getElementById('clear-logs-btn');

    // Fetch logs periodically
    let logInterval;

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

    // Start polling for logs when page loads
    logInterval = setInterval(updateLogs, 500);

    // Cleanup interval on page unload
    window.addEventListener('beforeunload', () => {
        if (logInterval) {
            clearInterval(logInterval);
        }
    });
});

