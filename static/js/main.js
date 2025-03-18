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

    // Set university match score colors based on value
    function setMatchScoreColors() {
        const scoreCircles = document.querySelectorAll('.score-circle');
        
        scoreCircles.forEach(circle => {
            const scoreText = circle.innerText;
            const score = parseFloat(scoreText);
            
            // Remove existing data attribute
            circle.removeAttribute('data-score');
            
            // Apply color based on score
            if (score >= 85) {
                circle.setAttribute('data-score', 'excellent');
                circle.style.backgroundColor = '#4CAF50'; // Green
            } else if (score >= 70) {
                circle.setAttribute('data-score', 'good');
                circle.style.backgroundColor = '#2196F3'; // Blue
            } else if (score >= 50) {
                circle.setAttribute('data-score', 'moderate');
                circle.style.backgroundColor = '#FF9800'; // Orange
            } else {
                circle.setAttribute('data-score', 'poor');
                circle.style.backgroundColor = '#F44336'; // Red
            }
        });
    }

    // Color each component score bar differently
    function styleComponentScores() {
        const componentBars = document.querySelectorAll('.score-fill');
        const colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#E91E63'];
        
        componentBars.forEach((bar, index) => {
            const colorIndex = index % colors.length;
            bar.style.backgroundColor = colors[colorIndex];
        });
    }

    // Initialize page-specific functions
    const tooltips = document.querySelectorAll('.tooltip');
    if (tooltips.length > 0) {
        tooltips.forEach(tooltip => {
            new Tooltip(tooltip);
        });
    }
    
    // Set match score colors
    setMatchScoreColors();
    
    // Style component scores
    styleComponentScores();
    
    // Initialize compare form
    const compareForm = document.getElementById('compare-form');
    if (compareForm) {
        const checkboxes = compareForm.querySelectorAll('input[type="checkbox"]');
        const submitButton = compareForm.querySelector('button[type="submit"]');

        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const checked = compareForm.querySelectorAll('input[type="checkbox"]:checked');
                submitButton.disabled = checked.length < 2;
                submitButton.classList.toggle('active', checked.length >= 2);
            });
        });
    }
    
    // Set up save university functionality
    const saveButtons = document.querySelectorAll('.save-university');
    if (saveButtons.length > 0) {
        saveButtons.forEach(button => {
            button.addEventListener('click', function(event) {
                event.preventDefault();
                const universityId = this.getAttribute('data-id');
                saveUniversity(universityId, this);
            });
        });
    }
});

// Function to save university via AJAX
function saveUniversity(universityId, button) {
    fetch(`/save_university/${universityId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update button to show saved
            button.classList.add('is-info');
            button.classList.remove('is-success');
            button.querySelector('span:not(.icon)').textContent = 'Saved';
            button.querySelector('.fas').classList.remove('fa-bookmark');
            button.querySelector('.fas').classList.add('fa-check');
            
            // Show notification
            showNotification('University saved to your list!', 'success');
        } else {
            showNotification(data.message || 'Error saving university', 'error');
        }
    })
    .catch(error => {
        showNotification('Error saving university', 'error');
        console.error('Error:', error);
    });
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification is-${type}`;
    notification.innerHTML = `
        <button class="delete"></button>
        ${message}
    `;
    
    // Add to notifications container or create one
    let container = document.querySelector('.notifications-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'notifications-container';
        document.body.appendChild(container);
    }
    
    container.appendChild(notification);
    
    // Close button functionality
    notification.querySelector('.delete').addEventListener('click', function() {
        notification.remove();
    });
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
} 