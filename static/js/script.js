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
        
        // Form validation
        if (!newsForm.checkValidity()) {
            event.stopPropagation();
            newsForm.classList.add('was-validated');
            return;
        }
        
        // Get the email value
        const email = document.getElementById('email').value;
        
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
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `email=${encodeURIComponent(email)}`
        })
        .then(response => response.json())
        .then(data => {
            setLoading(false);
            
            // Show success or error message
            showAlert(data.status === 'success' ? 'success' : 'danger', data.message);
            
            // If there's fallback content, display it
            if (data.html_content) {
                showSummaryContent(data.html_content);
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
            btnText.textContent = 'Processing...';
            btnSpinner.classList.remove('d-none');
            submitBtn.disabled = true;
        } else {
            btnText.textContent = 'Get News Summary';
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
        summaryContent.innerHTML = html;
        resultsContainer.classList.remove('d-none');
        
        // Scroll to results container
        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
});
