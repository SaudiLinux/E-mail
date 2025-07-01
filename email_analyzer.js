/**
 * Email Metadata Extractor and Analyzer - JavaScript Component
 * 
 * This script provides a web interface for the Python email metadata extractor,
 * allowing users to upload emails, view metadata, search databases, and manage
 * alternate email addresses.
 */

// Global variables
let currentMetadata = null;
let alternateEmails = [];

/**
 * Initialize the application when the DOM is fully loaded
 */
document.addEventListener('DOMContentLoaded', () => {
    // Set up event listeners
    setupEventListeners();
    
    // Check if Python backend is available
    checkBackendStatus();
});

/**
 * Set up all event listeners for the application
 */
function setupEventListeners() {
    // Email file upload
    const emailUploadForm = document.getElementById('email-upload-form');
    if (emailUploadForm) {
        emailUploadForm.addEventListener('submit', handleEmailUpload);
    }
    
    // Search databases button
    const searchDbButton = document.getElementById('search-databases-btn');
    if (searchDbButton) {
        searchDbButton.addEventListener('click', searchRelatedDatabases);
    }
    
    // Discover alternate emails button
    const discoverEmailsButton = document.getElementById('discover-emails-btn');
    if (discoverEmailsButton) {
        discoverEmailsButton.addEventListener('click', discoverAlternateEmails);
    }
    
    // Modify email form
    const modifyEmailForm = document.getElementById('modify-email-form');
    if (modifyEmailForm) {
        modifyEmailForm.addEventListener('submit', handleModifyEmail);
    }
}

/**
 * Check if the Python backend is available
 */
async function checkBackendStatus() {
    try {
        const response = await fetch('/api/status');
        if (response.ok) {
            showStatusMessage('Backend service is running', 'success');
        } else {
            showStatusMessage('Backend service is not responding properly', 'error');
        }
    } catch (error) {
        showStatusMessage('Cannot connect to backend service. Make sure the Python server is running.', 'error');
        console.error('Backend connection error:', error);
    }
}

/**
 * Handle email file upload
 * @param {Event} event - The form submit event
 */
async function handleEmailUpload(event) {
    event.preventDefault();
    
    const fileInput = document.getElementById('email-file');
    const file = fileInput.files[0];
    
    if (!file) {
        showStatusMessage('Please select an email file to upload', 'error');
        return;
    }
    
    // Show loading indicator
    showStatusMessage('Uploading and processing email...', 'info');
    
    const formData = new FormData();
    formData.append('email_file', file);
    
    try {
        const response = await fetch('/api/extract-metadata', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        
        const data = await response.json();
        currentMetadata = data.metadata;
        
        // Display the metadata
        displayMetadata(currentMetadata);
        showStatusMessage('Email metadata extracted successfully', 'success');
        
        // Enable database search and alternate email discovery buttons
        document.getElementById('search-databases-btn').disabled = false;
        document.getElementById('discover-emails-btn').disabled = false;
        
    } catch (error) {
        showStatusMessage(`Error processing email: ${error.message}`, 'error');
        console.error('Email upload error:', error);
    }
}

/**
 * Display email metadata in the UI
 * @param {Object} metadata - The email metadata object
 */
function displayMetadata(metadata) {
    const metadataContainer = document.getElementById('metadata-container');
    
    // Clear previous content
    metadataContainer.innerHTML = '';
    
    // Create a table for the metadata
    const table = document.createElement('table');
    table.className = 'metadata-table';
    
    // Add table header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    ['Property', 'Value'].forEach(text => {
        const th = document.createElement('th');
        th.textContent = text;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // Add table body
    const tbody = document.createElement('tbody');
    
    // Add basic metadata rows
    const basicProperties = [
        { key: 'from', label: 'From' },
        { key: 'to', label: 'To' },
        { key: 'cc', label: 'CC' },
        { key: 'bcc', label: 'BCC' },
        { key: 'subject', label: 'Subject' },
        { key: 'date', label: 'Date' },
        { key: 'message_id', label: 'Message ID' },
        { key: 'return_path', label: 'Return Path' },
    ];
    
    basicProperties.forEach(prop => {
        if (metadata[prop.key]) {
            const row = document.createElement('tr');
            
            const labelCell = document.createElement('td');
            labelCell.className = 'property-label';
            labelCell.textContent = prop.label;
            
            const valueCell = document.createElement('td');
            valueCell.className = 'property-value';
            valueCell.textContent = metadata[prop.key];
            
            row.appendChild(labelCell);
            row.appendChild(valueCell);
            tbody.appendChild(row);
        }
    });
    
    // Add IP addresses
    if (metadata.ip_addresses && metadata.ip_addresses.length > 0) {
        const row = document.createElement('tr');
        
        const labelCell = document.createElement('td');
        labelCell.className = 'property-label';
        labelCell.textContent = 'IP Addresses';
        
        const valueCell = document.createElement('td');
        valueCell.className = 'property-value';
        valueCell.textContent = metadata.ip_addresses.join(', ');
        
        row.appendChild(labelCell);
        row.appendChild(valueCell);
        tbody.appendChild(row);
    }
    
    // Add domains
    if (metadata.domains && metadata.domains.length > 0) {
        const row = document.createElement('tr');
        
        const labelCell = document.createElement('td');
        labelCell.className = 'property-label';
        labelCell.textContent = 'Domains';
        
        const valueCell = document.createElement('td');
        valueCell.className = 'property-value';
        valueCell.textContent = metadata.domains.join(', ');
        
        row.appendChild(labelCell);
        row.appendChild(valueCell);
        tbody.appendChild(row);
    }
    
    // Add X-Headers (collapsible)
    if (metadata.x_headers && Object.keys(metadata.x_headers).length > 0) {
        const row = document.createElement('tr');
        
        const labelCell = document.createElement('td');
        labelCell.className = 'property-label';
        labelCell.textContent = 'X-Headers';
        
        const valueCell = document.createElement('td');
        valueCell.className = 'property-value';
        
        const toggleButton = document.createElement('button');
        toggleButton.textContent = 'Show X-Headers';
        toggleButton.className = 'toggle-btn';
        
        const xHeadersContent = document.createElement('div');
        xHeadersContent.className = 'collapsible-content hidden';
        
        const xHeadersList = document.createElement('ul');
        Object.entries(metadata.x_headers).forEach(([key, value]) => {
            const listItem = document.createElement('li');
            listItem.textContent = `${key}: ${value}`;
            xHeadersList.appendChild(listItem);
        });
        
        xHeadersContent.appendChild(xHeadersList);
        
        toggleButton.addEventListener('click', () => {
            xHeadersContent.classList.toggle('hidden');
            toggleButton.textContent = xHeadersContent.classList.contains('hidden') ? 
                'Show X-Headers' : 'Hide X-Headers';
        });
        
        valueCell.appendChild(toggleButton);
        valueCell.appendChild(xHeadersContent);
        
        row.appendChild(labelCell);
        row.appendChild(valueCell);
        tbody.appendChild(row);
    }
    
    table.appendChild(tbody);
    metadataContainer.appendChild(table);
}

/**
 * Search related databases for information about the email domains
 */
async function searchRelatedDatabases() {
    if (!currentMetadata) {
        showStatusMessage('No email metadata available. Please upload an email first.', 'error');
        return;
    }
    
    showStatusMessage('Searching related databases...', 'info');
    
    try {
        const response = await fetch('/api/search-databases', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ metadata: currentMetadata })
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        
        const data = await response.json();
        displayDatabaseResults(data.results);
        showStatusMessage('Database search completed', 'success');
        
    } catch (error) {
        showStatusMessage(`Error searching databases: ${error.message}`, 'error');
        console.error('Database search error:', error);
    }
}

/**
 * Display database search results in the UI
 * @param {Object} results - The database search results
 */
function displayDatabaseResults(results) {
    const resultsContainer = document.getElementById('database-results-container');
    
    // Clear previous content
    resultsContainer.innerHTML = '';
    
    // Create header
    const header = document.createElement('h3');
    header.textContent = 'Database Search Results';
    resultsContainer.appendChild(header);
    
    // Check if we have results
    if (!results || Object.keys(results).length === 0) {
        const noResults = document.createElement('p');
        noResults.textContent = 'No database results found.';
        resultsContainer.appendChild(noResults);
        return;
    }
    
    // Create results for each domain
    Object.entries(results).forEach(([domain, domainResults]) => {
        const domainSection = document.createElement('div');
        domainSection.className = 'domain-results';
        
        const domainHeader = document.createElement('h4');
        domainHeader.textContent = domain;
        domainSection.appendChild(domainHeader);
        
        // Domain info
        if (domainResults.domain_info) {
            const infoTable = document.createElement('table');
            infoTable.className = 'results-table';
            
            Object.entries(domainResults.domain_info).forEach(([key, value]) => {
                const row = document.createElement('tr');
                
                const keyCell = document.createElement('td');
                keyCell.textContent = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                
                const valueCell = document.createElement('td');
                valueCell.textContent = value;
                
                row.appendChild(keyCell);
                row.appendChild(valueCell);
                infoTable.appendChild(row);
            });
            
            domainSection.appendChild(infoTable);
        }
        
        // Related emails
        if (domainResults.related_emails && domainResults.related_emails.length > 0) {
            const emailsHeader = document.createElement('h5');
            emailsHeader.textContent = 'Related Email Addresses:';
            domainSection.appendChild(emailsHeader);
            
            const emailsList = document.createElement('ul');
            domainResults.related_emails.forEach(email => {
                const listItem = document.createElement('li');
                listItem.textContent = email;
                emailsList.appendChild(listItem);
                
                // Add these to our alternate emails list if not already there
                if (!alternateEmails.includes(email)) {
                    alternateEmails.push(email);
                }
            });
            
            domainSection.appendChild(emailsList);
        }
        
        resultsContainer.appendChild(domainSection);
    });
    
    // Update the alternate emails list if we found any
    if (alternateEmails.length > 0) {
        updateAlternateEmailsList();
    }
}

/**
 * Discover potential alternate email addresses
 */
async function discoverAlternateEmails() {
    if (!currentMetadata) {
        showStatusMessage('No email metadata available. Please upload an email first.', 'error');
        return;
    }
    
    showStatusMessage('Discovering alternate email addresses...', 'info');
    
    try {
        const response = await fetch('/api/discover-alternates', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ metadata: currentMetadata })
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        
        const data = await response.json();
        alternateEmails = data.alternates || [];
        
        updateAlternateEmailsList();
        showStatusMessage('Alternate email discovery completed', 'success');
        
    } catch (error) {
        showStatusMessage(`Error discovering alternate emails: ${error.message}`, 'error');
        console.error('Alternate email discovery error:', error);
    }
}

/**
 * Update the alternate emails list in the UI
 */
function updateAlternateEmailsList() {
    const alternatesContainer = document.getElementById('alternate-emails-container');
    const selectOriginal = document.getElementById('original-email');
    
    // Clear previous content
    alternatesContainer.innerHTML = '';
    
    // Clear and repopulate the select dropdown
    selectOriginal.innerHTML = '';
    
    // Create header
    const header = document.createElement('h3');
    header.textContent = 'Potential Alternate Email Addresses';
    alternatesContainer.appendChild(header);
    
    if (alternateEmails.length === 0) {
        const noEmails = document.createElement('p');
        noEmails.textContent = 'No alternate email addresses found.';
        alternatesContainer.appendChild(noEmails);
        return;
    }
    
    // Create list of alternate emails
    const emailsList = document.createElement('ul');
    emailsList.className = 'alternate-emails-list';
    
    alternateEmails.forEach(email => {
        // Add to the list
        const listItem = document.createElement('li');
        listItem.textContent = email;
        emailsList.appendChild(listItem);
        
        // Add to the select dropdown
        const option = document.createElement('option');
        option.value = email;
        option.textContent = email;
        selectOriginal.appendChild(option);
    });
    
    alternatesContainer.appendChild(emailsList);
    
    // Show the modify email form
    document.getElementById('modify-email-section').classList.remove('hidden');
}

/**
 * Handle the modify email form submission
 * @param {Event} event - The form submit event
 */
async function handleModifyEmail(event) {
    event.preventDefault();
    
    const originalEmail = document.getElementById('original-email').value;
    const newEmail = document.getElementById('new-email').value;
    
    if (!originalEmail || !newEmail) {
        showStatusMessage('Please select an original email and provide a new email address', 'error');
        return;
    }
    
    showStatusMessage('Modifying email address...', 'info');
    
    try {
        const response = await fetch('/api/modify-email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                original_email: originalEmail,
                new_email: newEmail
            })
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            showStatusMessage(`Successfully modified email: ${originalEmail} -> ${newEmail}`, 'success');
            
            // Update our list of alternate emails
            const index = alternateEmails.indexOf(originalEmail);
            if (index !== -1) {
                alternateEmails[index] = newEmail;
                updateAlternateEmailsList();
            }
        } else {
            showStatusMessage(`Failed to modify email: ${data.message}`, 'error');
        }
        
    } catch (error) {
        showStatusMessage(`Error modifying email: ${error.message}`, 'error');
        console.error('Email modification error:', error);
    }
}

/**
 * Show a status message to the user
 * @param {string} message - The message to display
 * @param {string} type - The message type (success, error, info)
 */
function showStatusMessage(message, type = 'info') {
    const statusContainer = document.getElementById('status-container');
    
    const statusMessage = document.createElement('div');
    statusMessage.className = `status-message ${type}`;
    statusMessage.textContent = message;
    
    // Clear previous messages
    statusContainer.innerHTML = '';
    statusContainer.appendChild(statusMessage);
    
    // Auto-remove success and info messages after 5 seconds
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            statusMessage.remove();
        }, 5000);
    }
}