document.addEventListener('DOMContentLoaded', function() {
    const newsForm = document.getElementById('newsForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const btnSpinner = document.getElementById('btnSpinner');
    const alertContainer = document.getElementById('alertContainer');
    const resultsContainer = document.getElementById('resultsContainer');
    const summaryContent = document.getElementById('summaryContent');

    newsForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        // Show loading state
        setLoading(true);
        
        // Clear previous alerts and results
        alertContainer.innerHTML = '';
        alertContainer.classList.add('d-none');
        resultsContainer.classList.add('d-none');
        summaryContent.innerHTML = '';
        
        // Send request to process news
        fetch('/process_news', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            setLoading(false);
            
            if (data.status === 'success') {
                // Show success message
                showAlert('success', 'News summarized successfully!');
                
                // Display content
                if (data.html_content) {
                    showSummaryContent(data.html_content);
                }
            } else {
                // Show error message
                showAlert('danger', data.message || 'An error occurred. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            setLoading(false);
            showAlert('danger', 'An unexpected error occurred. Please try again.');
        });
    });
    
    function setLoading(isLoading) {
        if (isLoading) {
            btnText.textContent = 'Summarizing...';
            btnSpinner.classList.remove('d-none');
            submitBtn.disabled = true;
        } else {
            btnText.textContent = 'Get Greek News Summary';
            btnSpinner.classList.add('d-none');
            submitBtn.disabled = false;
        }
    }
    
    function showAlert(type, message) {
        alertContainer.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        alertContainer.classList.remove('d-none');
    }
    
    function showSummaryContent(html) {
        // Sanitize and process the HTML content
        try {
            // Clean up any unwanted text before the HTML
            let cleanHtml = html;
            const h1Index = html.indexOf('<h1>');
            
            if (h1Index > 0) {
                // Found an h1 tag, extract everything from there
                cleanHtml = html.substring(h1Index);
                console.log("Extracted clean HTML starting from h1 tag");
            }
            
            // Set the content
            summaryContent.innerHTML = cleanHtml;
            
            // Check if content was properly set
            if (summaryContent.innerHTML.includes('<h1>')) {
                console.log("Successfully injected HTML with h1 tag");
            } else {
                console.log("HTML injection may have failed, content doesn't contain h1 tag");
                
                // Fallback to a simple display
                summaryContent.innerHTML = `
                    <h1>Greek Domestic News Summary</h1>
                    <p>There was an issue formatting the news. The raw content is below:</p>
                    <pre>${html}</pre>
                `;
            }
        } catch (error) {
            console.error("Error handling HTML content:", error);
            summaryContent.innerHTML = "<h1>Error Processing News</h1><p>There was an error processing the news content. Please try again.</p>";
        }
        
        resultsContainer.classList.remove('d-none');
        
        // Scroll to results container
        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
});
