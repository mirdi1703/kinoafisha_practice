        const toggleBtn = document.getElementById('toggle-review-btn');
        const cancelBtn = document.getElementById('cancel-review-btn');
        const formWrapper = document.getElementById('review-form-wrapper');

        if (toggleBtn && formWrapper) {
            toggleBtn.addEventListener('click', () => {
                formWrapper.style.display = 'block';
                toggleBtn.style.display = 'none';
            });
        }

        if (cancelBtn && formWrapper && toggleBtn) {
            cancelBtn.addEventListener('click', () => {
                formWrapper.style.display = 'none';
                toggleBtn.style.display = 'inline-flex';
            });
        }