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
    document.getElementById('loginSection').parentElement.style.display = 'none';
    document.getElementById('homePage').style.display = 'block';
    document.getElementById('displayUsername').textContent = username || email;
    loadHomePageData();
}

// Show login form
function showLoginForm() {
    document.getElementById('loginSection').parentElement.style.display = 'block';
    document.getElementById('homePage').style.display = 'none';
    showEmailStep();
    document.getElementById('email').value = '';
    document.getElementById('otp').value = '';
    // Clear any auto-refresh intervals
    if (window.raceRefreshInterval) {
        clearInterval(window.raceRefreshInterval);
        window.raceRefreshInterval = null;
    }
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

// Load home page data
async function loadHomePageData() {
    try {
        // Fetch all data in parallel
        const [standingsResponse, raceStatusResponse] = await Promise.all([
            apiCall(`${API_BASE}/api/f1/standings`),
            apiCall(`${API_BASE}/api/f1/race-status`)
        ]);

        // Handle standings
        if (standingsResponse.ok) {
            const standingsData = await standingsResponse.json();
            renderStandings(standingsData.driver_standings, standingsData.constructor_standings);
        } else {
            renderStandingsError();
        }

        // Handle race status
        if (raceStatusResponse.ok) {
            const raceStatusData = await raceStatusResponse.json();
            if (raceStatusData.race_ongoing) {
                await renderLiveRace(raceStatusData.race_id);
                // Start auto-refresh for live race
                startRaceAutoRefresh(raceStatusData.race_id);
            } else {
                renderNoOngoingRace();
                await renderLastRace();
            }
        } else {
            renderRaceStatusError();
        }
    } catch (error) {
        console.error('Error loading home page data:', error);
        renderStandingsError();
        renderRaceStatusError();
    }
}

// Render standings tables
function renderStandings(driverStandings, constructorStandings) {
    const driverContainer = document.getElementById('driverStandings');
    const constructorContainer = document.getElementById('constructorStandings');

    if (!driverStandings || driverStandings.length === 0) {
        driverContainer.innerHTML = '<div class="error-message">No driver standings available</div>';
    } else {
        let html = '<table class="standings-table"><thead><tr><th>Pos</th><th>Driver</th><th>Points</th></tr></thead><tbody>';
        driverStandings.forEach(driver => {
            html += `<tr>
                <td>${driver.position || '-'}</td>
                <td>${driver.driver_name || 'Unknown'}</td>
                <td>${driver.points || 0}</td>
            </tr>`;
        });
        html += '</tbody></table>';
        driverContainer.innerHTML = html;
    }

    if (!constructorStandings || constructorStandings.length === 0) {
        constructorContainer.innerHTML = '<div class="error-message">No constructor standings available</div>';
    } else {
        let html = '<table class="standings-table"><thead><tr><th>Pos</th><th>Constructor</th><th>Points</th></tr></thead><tbody>';
        constructorStandings.forEach(constructor => {
            html += `<tr>
                <td>${constructor.position || '-'}</td>
                <td>${constructor.constructor_name || 'Unknown'}</td>
                <td>${constructor.points || 0}</td>
            </tr>`;
        });
        html += '</tbody></table>';
        constructorContainer.innerHTML = html;
    }
}

function renderStandingsError() {
    document.getElementById('driverStandings').innerHTML = '<div class="error-message">Failed to load driver standings</div>';
    document.getElementById('constructorStandings').innerHTML = '<div class="error-message">Failed to load constructor standings</div>';
}

// Render live race tracker
async function renderLiveRace(raceId) {
    const container = document.getElementById('liveRaceTracker');
    
    try {
        const response = await apiCall(`${API_BASE}/api/f1/telemetry${raceId ? `?race_id=${raceId}` : ''}`);
        
        if (response.ok) {
            const telemetry = await response.json();
            let html = `<div class="live-race-header">
                <h3>${telemetry.race_name || 'Live Race'}</h3>
                <span class="live-indicator">LIVE</span>
            </div>`;
            
            if (telemetry.results && telemetry.results.length > 0) {
                html += '<table class="race-results-table"><thead><tr><th>Pos</th><th>Driver</th><th>Constructor</th></tr></thead><tbody>';
                telemetry.results.forEach(result => {
                    const driverName = result.driver_name || result.driver?.name || 'Unknown';
                    const constructorName = result.constructor_name || result.team?.name || 'Unknown';
                    html += `<tr>
                        <td>${result.position || '-'}</td>
                        <td>${driverName}</td>
                        <td>${constructorName}</td>
                    </tr>`;
                });
                html += '</tbody></table>';
            } else {
                html += '<div class="info-message">Race positions not available yet</div>';
            }
            
            container.innerHTML = html;
            document.getElementById('lastRaceSection').style.display = 'none';
        } else {
            container.innerHTML = '<div class="error-message">Failed to load live race data</div>';
        }
    } catch (error) {
        console.error('Error loading live race:', error);
        container.innerHTML = '<div class="error-message">Error loading live race data</div>';
    }
}

function renderNoOngoingRace() {
    const container = document.getElementById('liveRaceTracker');
    container.innerHTML = '<div class="info-message">No ongoing race</div>';
    document.getElementById('lastRaceSection').style.display = 'block';
}

function renderRaceStatusError() {
    const container = document.getElementById('liveRaceTracker');
    container.innerHTML = '<div class="error-message">Failed to check race status</div>';
}

// Render last race results
async function renderLastRace() {
    const container = document.getElementById('lastRaceResults');
    
    try {
        const response = await apiCall(`${API_BASE}/api/f1/last-race`);
        
        if (response.ok) {
            const raceData = await response.json();
            
            if (raceData.race_found && raceData.results && raceData.results.length > 0) {
                let html = `<div class="race-header">
                    <h3>${raceData.race_name || 'Race'}</h3>
                    ${raceData.date ? `<p class="race-date">${raceData.date}</p>` : ''}
                </div>`;
                
                html += '<table class="race-results-table"><thead><tr><th>Pos</th><th>Driver</th><th>Constructor</th><th>Points</th></tr></thead><tbody>';
                raceData.results.forEach(result => {
                    html += `<tr>
                        <td>${result.position || '-'}</td>
                        <td>${result.driver_name || 'Unknown'}</td>
                        <td>${result.constructor_name || 'Unknown'}</td>
                        <td>${result.points || 0}</td>
                    </tr>`;
                });
                html += '</tbody></table>';
                
                container.innerHTML = html;
            } else {
                container.innerHTML = '<div class="info-message">No race results available</div>';
            }
        } else if (response.status === 404) {
            container.innerHTML = '<div class="info-message">No finished race found</div>';
        } else {
            container.innerHTML = '<div class="error-message">Failed to load last race results</div>';
        }
    } catch (error) {
        console.error('Error loading last race:', error);
        container.innerHTML = '<div class="error-message">Error loading last race results</div>';
    }
}

// Auto-refresh live race data
function startRaceAutoRefresh(raceId) {
    // Clear any existing interval
    if (window.raceRefreshInterval) {
        clearInterval(window.raceRefreshInterval);
    }
    
    // Refresh every 30 seconds
    window.raceRefreshInterval = setInterval(async () => {
        const response = await apiCall(`${API_BASE}/api/f1/race-status`);
        if (response.ok) {
            const data = await response.json();
            if (data.race_ongoing) {
                await renderLiveRace(data.race_id || raceId);
            } else {
                // Race ended, stop refreshing and show last race
                clearInterval(window.raceRefreshInterval);
                window.raceRefreshInterval = null;
                renderNoOngoingRace();
                await renderLastRace();
            }
        }
    }, 30000);
}

// Check session when page loads
checkSession();
