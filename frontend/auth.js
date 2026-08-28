/**
 * Athena Authentication Client Logic
 */

// Dynamically determine the backend API base URL
function getApiBase() {
    if (window.location.protocol === "file:") {
        return "http://127.0.0.1:8000";
    }
    if (window.location.port === "8000") {
        return window.location.origin;
    }
    const host = window.location.hostname || "127.0.0.1";
    const protocol = window.location.protocol === "https:" ? "https:" : "http:";
    return `${protocol}//${host}:8000`;
}

const API_BASE = getApiBase();

document.addEventListener("DOMContentLoaded", () => {
    initPasswordToggles();
    initAlertBox();

    const signupForm = document.getElementById("signup-form");
    const loginForm = document.getElementById("login-form");

    if (signupForm) {
        initSignup(signupForm);
    }

    if (loginForm) {
        initLogin(loginForm);
    }
});

/**
 * Initialize password visibility toggles
 */
function initPasswordToggles() {
    const toggleButtons = document.querySelectorAll(".toggle-password");
    
    toggleButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-target");
            const input = document.getElementById(targetId);
            if (!input) return;

            const isPassword = input.type === "password";
            input.type = isPassword ? "text" : "password";

            const eyeOpen = btn.querySelector(".eye-open");
            const eyeClosed = btn.querySelector(".eye-closed");

            if (eyeOpen && eyeClosed) {
                if (isPassword) {
                    eyeOpen.classList.add("hidden");
                    eyeClosed.classList.remove("hidden");
                    btn.setAttribute("title", "Hide password");
                } else {
                    eyeOpen.classList.remove("hidden");
                    eyeClosed.classList.add("hidden");
                    btn.setAttribute("title", "Show password");
                }
            }
        });
    });
}

/**
 * Alert box display utilities
 */
let alertTimeout = null;

function initAlertBox() {
    const alertBox = document.getElementById("alert-box");
    if (!alertBox) return;
}

function showAlert(type, message) {
    const alertBox = document.getElementById("alert-box");
    const alertIcon = document.getElementById("alert-icon");
    const alertMessage = document.getElementById("alert-message");

    if (!alertBox || !alertMessage) return;

    if (alertTimeout) {
        clearTimeout(alertTimeout);
    }

    alertBox.className = `alert ${type}`;
    alertMessage.textContent = message;

    if (alertIcon) {
        if (type === "success") {
            alertIcon.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
            `;
        } else {
            alertIcon.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
            `;
        }
    }

    alertBox.classList.remove("hidden");
}

function hideAlert() {
    const alertBox = document.getElementById("alert-box");
    if (alertBox) {
        alertBox.classList.add("hidden");
    }
}

/**
 * Submit button loading state handler
 */
function setButtonLoading(isLoading, defaultText = "Submit") {
    const submitBtn = document.getElementById("submit-btn");
    const btnText = document.getElementById("btn-text");
    const btnSpinner = document.getElementById("btn-spinner");

    if (!submitBtn) return;

    submitBtn.disabled = isLoading;
    if (btnText) {
        btnText.textContent = isLoading ? "Processing..." : defaultText;
    }
    if (btnSpinner) {
        if (isLoading) {
            btnSpinner.classList.remove("hidden");
        } else {
            btnSpinner.classList.add("hidden");
        }
    }
}

/**
 * Handle Sign Up logic
 */
function initSignup(form) {
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const confirmPasswordInput = document.getElementById("confirm-password");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        hideAlert();

        const email = emailInput.value.trim();
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;

        // Basic client validation
        if (!email) {
            showAlert("error", "Please enter a valid email address.");
            emailInput.focus();
            return;
        }

        if (!password) {
            showAlert("error", "Please enter a password.");
            passwordInput.focus();
            return;
        }

        if (password.length < 8) {
            showAlert("error", "Password must be at least 8 characters long.");
            passwordInput.focus();
            return;
        }

        if (password !== confirmPassword) {
            showAlert("error", "Passwords do not match. Please verify and try again.");
            confirmPasswordInput.focus();
            return;
        }

        setButtonLoading(true, "Create Account");

        try {
            const response = await fetch(`${API_BASE}/signup`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ email, password }),
            });

            const data = await response.json();

            if (response.ok) {
                showAlert("success", "Account created successfully! Redirecting to Sign In...");
                
                // Disable inputs during redirect
                emailInput.disabled = true;
                passwordInput.disabled = true;
                confirmPasswordInput.disabled = true;

                // Move to sign in page after signup with email pre-populated
                setTimeout(() => {
                    window.location.href = `login.html?registered=true&email=${encodeURIComponent(email)}`;
                }, 1200);
            } else {
                setButtonLoading(false, "Create Account");
                const errorMsg = data.detail || "Registration failed. Please try again.";
                showAlert("error", errorMsg);
            }
        } catch (err) {
            console.error("Signup error:", err);
            setButtonLoading(false, "Create Account");
            showAlert("error", "Unable to connect to the server. Please ensure the backend is running at " + API_BASE);
        }
    });
}

/**
 * Handle Login logic
 */
function initLogin(form) {
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");

    // Check if redirected from successful signup
    const params = new URLSearchParams(window.location.search);
    if (params.get("registered") === "true") {
        const registeredEmail = params.get("email");
        if (registeredEmail && emailInput) {
            emailInput.value = registeredEmail;
        }
        showAlert("success", "Account created successfully! Please enter your password to sign in.");
        if (passwordInput) {
            passwordInput.focus();
        }
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        hideAlert();

        const email = emailInput.value.trim();
        const password = passwordInput.value;

        if (!email) {
            showAlert("error", "Please enter your email address.");
            emailInput.focus();
            return;
        }

        if (!password) {
            showAlert("error", "Please enter your password.");
            passwordInput.focus();
            return;
        }

        setButtonLoading(true, "Sign In");

        try {
            const response = await fetch(`${API_BASE}/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ email, password }),
            });

            const data = await response.json();

            if (response.ok && data.token) {
                // Save auth token & user info to localStorage
                localStorage.setItem("athena_token", data.token);
                localStorage.setItem(
                    "athena_user", 
                    JSON.stringify(data.user || { email: email })
                );

                showAlert("success", "Signed in successfully! Redirecting to Athena...");

                // Navigate to main application dashboard
                setTimeout(() => {
                    window.location.href = "index.html";
                }, 600);
            } else {
                setButtonLoading(false, "Sign In");
                const errorMsg = data.detail || "Invalid email or password.";
                showAlert("error", errorMsg);
            }
        } catch (err) {
            console.error("Login error:", err);
            setButtonLoading(false, "Sign In");
            showAlert("error", "Unable to connect to the server. Please ensure the backend is running at " + API_BASE);
        }
    });
}
