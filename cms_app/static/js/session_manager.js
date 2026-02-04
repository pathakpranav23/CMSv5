// Session Management (World-Class Experience)
// Handles inactivity tracking, warning modal, and auto-logout

document.addEventListener('DOMContentLoaded', function() {
    // Configuration (Sync with server settings)
    const SESSION_LIFETIME = 5 * 60 * 1000; // 5 minutes in milliseconds
    const WARNING_TIME = 30 * 1000;         // Show warning 30s before expiry
    const CHECK_INTERVAL = 5 * 1000;        // Check timer every 5s
    
    let lastActivity = Date.now();
    let warningShown = false;
    let logoutTimer = null;
    let warningTimer = null;

    const modalElement = document.getElementById('sessionWarningModal');
    let warningModal = null;
    if (modalElement) {
        warningModal = new bootstrap.Modal(modalElement, {
            backdrop: 'static',
            keyboard: false
        });
    }

    // 1. Activity Tracker
    // Reset the "last active" timestamp on user interaction
    function resetActivity() {
        lastActivity = Date.now();
        if (warningShown) {
            hideWarning();
        }
    }

    const events = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    events.forEach(evt => document.addEventListener(evt, resetActivity, true));

    // 2. Heartbeat (The "Soft" Keep-Alive)
    // If the user is active, we silently ping the server to extend the session
    // But ONLY if we are getting close to the timeout to avoid spamming
    function sendHeartbeat() {
        fetch('/api/keep-alive', { method: 'POST' })
            .then(response => {
                if (!response.ok) {
                    // If server says session is gone, force logout
                    window.location.href = '/login';
                }
            })
            .catch(() => {});
    }

    // 3. The Watchdog
    // Checks every few seconds if we should show the warning or logout
    setInterval(() => {
        const now = Date.now();
        const timeSinceActive = now - lastActivity;
        const timeRemaining = SESSION_LIFETIME - timeSinceActive;

        // Debug logging (optional, remove in prod)
        // console.log(`Session: ${timeRemaining/1000}s remaining`);

        if (timeRemaining <= 0) {
            // Hard Logout
            window.location.href = '/logout';
        } else if (timeRemaining <= WARNING_TIME) {
            // Show Warning
            if (!warningShown) {
                showWarning(timeRemaining);
            }
            updateCountdown(timeRemaining);
        } else {
            // Safe zone
            if (warningShown) {
                hideWarning();
            }
            // If user is active and we are in the last minute (but before warning), send heartbeat
            // This ensures active users never see the warning
            if (timeSinceActive < 10000 && timeRemaining < (60 * 1000)) {
                sendHeartbeat();
            }
        }
    }, CHECK_INTERVAL);

    function showWarning(timeLeft) {
        warningShown = true;
        if (warningModal) warningModal.show();
    }

    function hideWarning() {
        warningShown = false;
        if (warningModal) warningModal.hide();
        // Ping server to confirm we are back
        sendHeartbeat();
    }

    function updateCountdown(timeLeft) {
        const seconds = Math.ceil(timeLeft / 1000);
        const counter = document.getElementById('sessionCountdown');
        if (counter) counter.innerText = seconds;
    }

    // Bind "Stay Logged In" button
    const stayBtn = document.getElementById('btnStayLoggedIn');
    if (stayBtn) {
        stayBtn.addEventListener('click', function() {
            resetActivity();
            hideWarning();
        });
    }
});