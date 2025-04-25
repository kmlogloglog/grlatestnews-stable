document.addEventListener('DOMContentLoaded', function() {
    const newsForm = document.getElementById('newsForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const btnSpinner = document.getElementById('btnSpinner');
    const alertContainer = document.getElementById('alertContainer');

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
        
        // Clear previous alerts
        alertContainer.innerHTML = '';
        alertContainer.classList.add('d-none');
        
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
});
