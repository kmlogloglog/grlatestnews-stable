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

        // Show loader sentences immediately after 1s, and keep rotating until result
        showLoader();

        // Send request to process news right away (no artificial delay)
        fetch('/process_news', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            setLoading(false);
            hideLoader();
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
            hideLoader();
            showAlert('danger', 'An unexpected error occurred. Please try again.');
        });
    });
    
    function setLoading(isLoading) {
        if (isLoading) {
            btnText.textContent = '';
            btnSpinner.classList.remove('d-none');
            submitBtn.disabled = true;
            submitBtn.style.display = 'none'; // Hide the button while loading
        } else {
            btnText.textContent = 'Get Greek News Summary';
            btnSpinner.classList.add('d-none');
            submitBtn.disabled = false;
            submitBtn.style.display = 'block'; // Show the button again
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
    
    // Loader messages and animation (with emoji)
    const loaderSentences = [
        "🇬🇷 Gathering today's freshest Greek headlines...",
        "📰 Translating news from Greek to English...",
        "🔍 Fact-checking with a magnifying glass...",
        "🦉 Consulting the wise owl of Athens...",
        "🎡 Spinning the news wheel for you...",
        "📻 Tuning into the latest scoops...",
        "📦 Packing the news into a neat summary...",
        "🍋 Squeezing lemons for zesty news...",
        "🎭 Translating drama into plain English...",
        "💡 Illuminating today's top stories...",
        "🚀 Launching your news rocket..."
    ];
    let loaderInterval = null;
    let loaderIndex = 0;
    function showLoader() {
        const loaderDiv = document.createElement('div');
        loaderDiv.id = 'customNewsLoader';
        loaderDiv.className = 'custom-loader-container';
        loaderDiv.innerHTML = `
            <div class="spinner-border text-primary" role="status"></div>
            <div id="loaderSentence" class="mt-2 fw-bold"></div>
        `;
        summaryContent.innerHTML = '';
        summaryContent.appendChild(loaderDiv);
        resultsContainer.classList.remove('d-none');
        // Animate sentences after 1 second
        loaderIndex = 0;
        setTimeout(() => {
            document.getElementById('loaderSentence').textContent = loaderSentences[loaderIndex];
            loaderInterval = setInterval(() => {
                loaderIndex = (loaderIndex + 1) % loaderSentences.length;
                const loaderSentenceElem = document.getElementById('loaderSentence');
                if (loaderSentenceElem) {
                    loaderSentenceElem.textContent = loaderSentences[loaderIndex];
                }
            }, 2000);
        }, 1000);
    }
    function hideLoader() {
        clearInterval(loaderInterval);
        const loaderDiv = document.getElementById('customNewsLoader');
        if (loaderDiv) loaderDiv.remove();
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
