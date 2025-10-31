// Microsynth Auto Aligner - Frontend JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // Tabs
    const tabs = document.querySelectorAll('.tab');
    const panels = {
        aligner: document.getElementById('tab-aligner'),
        next: document.getElementById('tab-next'),
        helper: document.getElementById('tab-helper')
    };

    let helperInterval;

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.getAttribute('data-tab');
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            Object.keys(panels).forEach(key => {
                if (key === target) {
                    panels[key].classList.remove('hidden');
                } else {
                    panels[key].classList.add('hidden');
                }
            });
            // Manage helper logs polling
            if (helperInterval) {
                clearInterval(helperInterval);
                helperInterval = null;
            }
            if (target === 'helper') {
                fetchHelperLogs();
                helperInterval = setInterval(fetchHelperLogs, 3000);
            }
        });
    });

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

    // Track last displayed results to avoid unnecessary updates
    let lastResultsHash = null;
    let resultsDisplayed = false;

    // Function to update results
    function updateResults() {
        fetch('/api/results')
            .then(response => response.json())
            .then(data => {
                console.log('DEBUG: Results data:', data);  // Console log
                
                // Create a hash of current results to detect changes
                const currentHash = data.results ? JSON.stringify(data.results) : '';
                
                // Only update if results changed or if we have results to show
                if (data.results && data.results.length > 0) {
                    // Only rebuild if results actually changed
                    if (currentHash !== lastResultsHash) {
                        resultsCard.style.display = 'block';
                        resultsContainer.innerHTML = '';
                        
                        data.results.forEach(result => {
                            console.log('DEBUG: Processing result:', result);  // Console log
                            const resultEntry = document.createElement('div');
                            resultEntry.className = 'result-entry';
                            
                            if (result.success) {
                                // Link to DNA sequence in Benchling (not alignment)
                                const benchlingUrl = result.sequence_url || '#';
                                const linkText = benchlingUrl !== '#' ? 'View Sequence in Benchling' : 'Sequence URL unavailable';
                                resultEntry.innerHTML = `
                                    <div class="result-success">
                                        <strong>${result.tube_name}</strong> - 
                                        ${benchlingUrl !== '#' ? `<a href="${benchlingUrl}" target="_blank" class="benchling-link">${linkText}</a>` : `<span class="error-text">${linkText}</span>`}
                                        ${result.alignment_id ? `<span class="result-id">Alignment ID: ${result.alignment_id}</span>` : ''}
                                    </div>
                                `;
                            } else {
                                // On error, still try to show sequence link if available
                                const benchlingUrl = result.sequence_url || null;
                                resultEntry.innerHTML = `
                                    <div class="result-error">
                                        <strong>${result.tube_name}</strong> - 
                                        <span class="error-text">Failed to create alignment</span>
                                        ${result.error ? `<span class="error-details">(${result.error})</span>` : ''}
                                        ${benchlingUrl ? `<a href="${benchlingUrl}" target="_blank" class="benchling-link">View Sequence in Benchling</a>` : ''}
                                    </div>
                                `;
                            }
                            
                            resultsContainer.appendChild(resultEntry);
                        });
                        
                        lastResultsHash = currentHash;
                        resultsDisplayed = true;
                    }
                } else {
                    // Only hide results card if we haven't displayed results yet
                    // Once results are shown, keep them visible even if polling returns empty
                    if (!resultsDisplayed) {
                        resultsCard.style.display = 'none';
                    }
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
        
        // Reset results tracking for new alignment
        lastResultsHash = null;
        resultsDisplayed = false;
        resultsCard.style.display = 'none';
        resultsContainer.innerHTML = '';

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
        if (helperInterval) {
            clearInterval(helperInterval);
        }
    });

    // Primer Registration logic
    const userSelect = document.getElementById('primer-user');
    const fileInputPrimer = document.getElementById('primer-file');
    const previewBtn = document.getElementById('primer-preview-btn');
    const registerBtn = document.getElementById('primer-register-btn');
    const previewTable = document.getElementById('primer-preview-table');
    const resultsTable = document.getElementById('primer-results-table');
    const directionSelect = document.getElementById('primer-direction');
    const downloadIdtBtn = document.getElementById('primer-download-idt');
    const downloadEurofinsBtn = document.getElementById('primer-download-eurofins');

    let previewRows = [];
    let resultRows = [];

    async function fetchUsers() {
        try {
            const resp = await fetch('/api/users');
            const data = await resp.json();
            (data.users || []).forEach(u => {
                const opt = document.createElement('option');
                opt.value = u.value;
                opt.textContent = u.label;
                userSelect?.appendChild(opt);
            });
        } catch (e) {
            console.error('Failed to load users', e);
        }
    }
    fetchUsers();

    async function fetchDirectionOptions() {
        try {
            const resp = await fetch('/api/dropdown/options');
            const data = await resp.json();
            (data.options || []).forEach(o => {
                const opt = document.createElement('option');
                opt.value = o.value;
                opt.textContent = o.label;
                directionSelect?.appendChild(opt);
            });
            // Add empty option
            const empty = document.createElement('option');
            empty.value = '';
            empty.textContent = 'No Direction';
            if (directionSelect) directionSelect.insertBefore(empty, directionSelect.firstChild);
        } catch (e) {
            console.error('Failed to load direction options', e);
        }
    }
    fetchDirectionOptions();

    function renderTable(container, rows) {
        if (!container) return;
        if (!rows || rows.length === 0) {
            container.innerHTML = '<p class="help-text">No data.</p>';
            return;
        }
        const cols = Object.keys(rows[0]);
        const table = document.createElement('table');
        const thead = document.createElement('thead');
        const trh = document.createElement('tr');
        cols.forEach(c => {
            const th = document.createElement('th');
            th.textContent = c;
            trh.appendChild(th);
        });
        thead.appendChild(trh);
        table.appendChild(thead);
        const tbody = document.createElement('tbody');
        rows.forEach(r => {
            const tr = document.createElement('tr');
            cols.forEach(c => {
                const td = document.createElement('td');
                td.textContent = r[c] ?? '';
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        container.innerHTML = '';
        container.appendChild(table);
    }

    previewBtn?.addEventListener('click', async () => {
        if (!fileInputPrimer?.files || fileInputPrimer.files.length === 0) {
            alert('Choose a CSV or XLSX file.');
            return;
        }
        const fd = new FormData();
        fd.append('file', fileInputPrimer.files[0]);
        try {
            const resp = await fetch('/api/primer/preview', { method: 'POST', body: fd });
            const data = await resp.json();
            if (!resp.ok) {
                alert(data.error || 'Preview failed');
                return;
            }
            previewRows = data.rows || [];
            renderTable(previewTable, previewRows);
            if (registerBtn) registerBtn.disabled = previewRows.length === 0;
        } catch (e) {
            alert('Preview failed');
        }
    });

    registerBtn?.addEventListener('click', async () => {
        const userId = userSelect?.value;
        if (!userId) {
            alert('Select user first.');
            return;
        }
        try {
            const resp = await fetch('/api/primer/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId, rows: previewRows, directionOptionId: directionSelect?.value || undefined })
            });
            const data = await resp.json();
            if (!resp.ok) {
                alert(data.error || 'Registration failed');
                return;
            }
            resultRows = data.results || [];
            renderTable(resultsTable, resultRows);
            const disabled = resultRows.length === 0;
            if (downloadIdtBtn) downloadIdtBtn.disabled = disabled;
            if (downloadEurofinsBtn) downloadEurofinsBtn.disabled = disabled;
        } catch (e) {
            alert('Registration failed');
        }
    });

    function downloadCSV(filename, rows) {
        if (!rows || rows.length === 0) return;
        const cols = Object.keys(rows[0]);
        const csv = [cols.join(',')].concat(rows.map(r => cols.map(c => {
            const val = (r[c] ?? '').toString().replaceAll('"', '""');
            return '"' + val + '"';
        }).join(','))).join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    downloadIdtBtn?.addEventListener('click', () => {
        // IDT format: Name, Sequence, Scale, Purification
        const rows = (resultRows || []).map(r => ({
            Name: r['Oligo Name'],
            Sequence: r['Sequence'],
            Scale: '25nm',
            Purification: 'STD'
        }));
        const date = new Date().toISOString().slice(0,10);
        downloadCSV(`bacta_idt_registered_primers_${date}.csv`, rows);
    });

    // Helper logs
    const helperLogContainer = document.getElementById('helper-log-container');
    const helperTailInput = document.getElementById('helper-tail');
    const helperRefreshBtn = document.getElementById('helper-refresh');

    async function fetchHelperLogs() {
        if (!helperLogContainer) return;
        const tail = parseInt(helperTailInput?.value || '200', 10) || 200;
        try {
            const resp = await fetch(`/api/benchling-helper/logs?tail=${tail}`);
            const data = await resp.json();
            if (!resp.ok) {
                helperLogContainer.innerHTML = `<div class="log-entry">${data.error || 'Unable to fetch logs'}</div>`;
                return;
            }
            const lines = data.lines || [];
            helperLogContainer.innerHTML = '';
            lines.forEach(line => {
                const div = document.createElement('div');
                div.className = 'log-entry';
                div.textContent = line;
                helperLogContainer.appendChild(div);
            });
            helperLogContainer.scrollTop = helperLogContainer.scrollHeight;
        } catch (e) {
            helperLogContainer.innerHTML = `<div class="log-entry">Failed to load logs</div>`;
        }
    }

    helperRefreshBtn?.addEventListener('click', fetchHelperLogs);

    downloadEurofinsBtn?.addEventListener('click', async () => {
        try {
            const resp = await fetch('/api/primer/eurofins', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rows: resultRows })
            });
            if (!resp.ok) {
                const data = await resp.json().catch(() => ({}));
                alert(data.error || 'Eurofins export failed');
                return;
            }
            // Stream file
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'bacta_eurofins_registered_primers.xlsx';
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            alert('Eurofins export failed');
        }
    });
});

