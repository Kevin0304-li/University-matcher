document.addEventListener('DOMContentLoaded', function() {
    // Handle form range inputs with visual feedback
    const rangeInputs = document.querySelectorAll('input[type="range"]');
    rangeInputs.forEach(input => {
        const output = document.querySelector(`output[for="${input.id}"]`);
        if (output) {
            // Update output when slider moves
            input.addEventListener('input', function() {
                output.textContent = input.value;
            });
            // Set initial value
            output.textContent = input.value;
        }
    });

    // Handle mobile navigation toggle
    const navToggle = document.querySelector('.nav-toggle');
    if (navToggle) {
        navToggle.addEventListener('click', function() {
            const mainNav = document.querySelector('.main-nav');
            mainNav.classList.toggle('active');
        });
    }

    // Form validation
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            
            // Check required fields
            const required = form.querySelectorAll('[required]');
            required.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    showError(field, 'This field is required');
                } else {
                    clearError(field);
                }
            });
            
            // GPA validation
            const gpaField = form.querySelector('input[name="gpa"]');
            if (gpaField && gpaField.value) {
                const gpa = parseFloat(gpaField.value);
                if (isNaN(gpa) || gpa < 0 || gpa > 4.0) {
                    isValid = false;
                    showError(gpaField, 'GPA must be between 0 and 4.0');
                }
            }
            
            // SAT validation
            const satField = form.querySelector('input[name="sat_score"]');
            if (satField && satField.value) {
                const sat = parseInt(satField.value);
                if (isNaN(sat) || sat < 400 || sat > 1600) {
                    isValid = false;
                    showError(satField, 'SAT score must be between 400 and 1600');
                }
            }
            
            // Budget validation
            const budgetField = form.querySelector('input[name="budget"]');
            if (budgetField && budgetField.value) {
                const budget = parseInt(budgetField.value);
                if (isNaN(budget) || budget <= 0) {
                    isValid = false;
                    showError(budgetField, 'Budget must be a positive number');
                }
            }
            
            if (!isValid) {
                e.preventDefault();
            }
        });
    });

    // Error display functions
    function showError(field, message) {
        // Clear any existing error
        clearError(field);
        
        // Add error class to the field
        field.classList.add('error');
        
        // Create and insert error message
        const error = document.createElement('div');
        error.className = 'form-error';
        error.textContent = message;
        
        field.parentNode.appendChild(error);
    }

    function clearError(field) {
        // Remove error class
        field.classList.remove('error');
        
        // Remove any error messages
        const error = field.parentNode.querySelector('.form-error');
        if (error) {
            error.remove();
        }
    }

    // Comparison page: handle university selection
    const compareForm = document.getElementById('compare-form');
    if (compareForm) {
        const checkboxes = compareForm.querySelectorAll('input[type="checkbox"]');
        const submitButton = compareForm.querySelector('button[type="submit"]');
        
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', updateSubmitButton);
        });
        
        function updateSubmitButton() {
            const checked = compareForm.querySelectorAll('input[type="checkbox"]:checked');
            submitButton.disabled = checked.length < 2;
            
            if (checked.length < 2) {
                submitButton.classList.add('disabled');
            } else {
                submitButton.classList.remove('disabled');
            }
        }
        
        // Initial state
        updateSubmitButton();
    }

    // Handle notification dismissal
    (document.querySelectorAll('.notification .delete') || []).forEach(($delete) => {
        const $notification = $delete.parentNode;
        $delete.addEventListener('click', () => {
            $notification.parentNode.removeChild($notification);
        });
    });
    
    // Handle navbar burger menu toggle
    const $navbarBurgers = Array.prototype.slice.call(document.querySelectorAll('.navbar-burger'), 0);
    if ($navbarBurgers.length > 0) {
        $navbarBurgers.forEach(el => {
            el.addEventListener('click', () => {
                const target = el.dataset.target;
                const $target = document.getElementById(target);
                el.classList.toggle('is-active');
                $target.classList.toggle('is-active');
            });
        });
    }

    // Optional: Auto-close notifications after 5 seconds
    setTimeout(() => {
        (document.querySelectorAll('.notification') || []).forEach(($notification) => {
            $notification.style.transition = 'opacity 1s';
            $notification.style.opacity = '0';
            setTimeout(() => {
                if ($notification.parentNode) {
                    $notification.parentNode.removeChild($notification);
                }
            }, 1000);
        });
    }, 5000);
}); 