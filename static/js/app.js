const API_BASE = ''; // Use relative paths since frontend and backend are same origin

// Helper function to make API calls with credentials
async function apiCall(url, options = {}) {
    return fetch(url, {
        ...options,
        credentials: 'include', // Include cookies for session
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    });
}

// Check if user is logged in on page load
async function checkSession() {
    try {
        const response = await apiCall(`${API_BASE}/me`);
        const data = await response.json();
        
        if (data.logged_in) {
            showLoggedInState(data.email, data.username, data.role);
        } else {
            showLoginForm();
        }
    } catch (error) {
        console.error('Error checking session:', error);
        showLoginForm();
    }
}

// Show logged-in state
function showLoggedInState(email, username, role) {
    document.getElementById('loginSection').style.display = 'none';
    document.getElementById('userInfo').style.display = 'block';
    document.getElementById('displayUsername').textContent = username || email;
    document.getElementById('displayRole').textContent = role;
}

// Show login form
function showLoginForm() {
    document.getElementById('loginSection').style.display = 'block';
    document.getElementById('userInfo').style.display = 'none';
    showEmailStep();
    document.getElementById('email').value = '';
    document.getElementById('otp').value = '';
}

// Show email input step
function showEmailStep() {
    document.getElementById('emailStep').style.display = 'block';
    document.getElementById('otpStep').style.display = 'none';
}

// Show OTP input step
function showOTPStep(email) {
    document.getElementById('emailStep').style.display = 'none';
    document.getElementById('otpStep').style.display = 'block';
    document.getElementById('emailDisplay').textContent = email;
    document.getElementById('otp').focus();
}

// Email form handler - request OTP
document.getElementById('emailForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value.trim().toLowerCase();
    const messageDiv = document.getElementById('message');
    
    // Clear previous messages
    messageDiv.className = 'message';
    messageDiv.textContent = '';
    messageDiv.style.display = 'none';
    
    try {
        const response = await apiCall(`${API_BASE}/request-otp`, {
            method: 'POST',
            body: JSON.stringify({ email: email })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showOTPStep(email);
            messageDiv.className = 'message success';
            messageDiv.textContent = data.message || 'OTP sent to your email!';
            messageDiv.style.display = 'block';
        } else {
            messageDiv.className = 'message error';
            messageDiv.textContent = data.message || 'Failed to send OTP. Please try again.';
            messageDiv.style.display = 'block';
        }
    } catch (error) {
        messageDiv.className = 'message error';
        messageDiv.textContent = 'Error connecting to server. Please try again.';
        messageDiv.style.display = 'block';
        console.error('Error:', error);
    }
});

// OTP form handler - verify OTP
document.getElementById('otpForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('emailDisplay').textContent;
    const otp = document.getElementById('otp').value.trim();
    const messageDiv = document.getElementById('message');
    
    // Clear previous messages
    messageDiv.className = 'message';
    messageDiv.textContent = '';
    messageDiv.style.display = 'none';
    
    try {
        const response = await apiCall(`${API_BASE}/verify-otp`, {
            method: 'POST',
            body: JSON.stringify({
                email: email,
                otp: otp
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showLoggedInState(data.email, data.username, data.role);
            messageDiv.className = 'message success';
            messageDiv.textContent = data.message || 'Login successful!';
            messageDiv.style.display = 'block';
        } else {
            messageDiv.className = 'message error';
            messageDiv.textContent = data.message || 'Invalid OTP. Please try again.';
            messageDiv.style.display = 'block';
        }
    } catch (error) {
        messageDiv.className = 'message error';
        messageDiv.textContent = 'Error connecting to server. Please try again.';
        messageDiv.style.display = 'block';
        console.error('Error:', error);
    }
});

// Back to email step
document.getElementById('backToEmail').addEventListener('click', function() {
    showEmailStep();
    document.getElementById('otp').value = '';
    const messageDiv = document.getElementById('message');
    messageDiv.style.display = 'none';
});

// Auto-format OTP input (numbers only)
document.getElementById('otp').addEventListener('input', function(e) {
    e.target.value = e.target.value.replace(/\D/g, '');
});

// Logout handler
document.getElementById('logoutBtn').addEventListener('click', async function() {
    const messageDiv = document.getElementById('message');
    
    try {
        const response = await apiCall(`${API_BASE}/logout`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showLoginForm();
            messageDiv.className = 'message success';
            messageDiv.textContent = data.message || 'Logged out successfully!';
            messageDiv.style.display = 'block';
        } else {
            messageDiv.className = 'message error';
            messageDiv.textContent = data.message || 'Logout failed.';
            messageDiv.style.display = 'block';
        }
    } catch (error) {
        messageDiv.className = 'message error';
        messageDiv.textContent = 'Error connecting to server. Please try again.';
        messageDiv.style.display = 'block';
        console.error('Error:', error);
    }
});

// Check session when page loads
checkSession();
