/**
 * Firebase Authentication Client Integration for TravelAI.
 * Enables Google One-Click Sign-In and Firebase User Authentication.
 */

(function () {
    let firebaseApp = null;
    let auth = null;
    let googleProvider = null;

    function getCsrfToken() {
        return window.__CSRF_TOKEN__ || document.querySelector('input[name="csrf_token"]')?.value || '';
    }

    function isConfigValid(cfg) {
        return cfg && cfg.apiKey && cfg.authDomain && cfg.projectId && cfg.appId;
    }

    function initFirebase() {
        if (firebaseApp) return true;
        const config = window.__FIREBASE_CONFIG__;
        if (!config || !isConfigValid(config)) return false;

        try {
            if (typeof firebase !== 'undefined') {
                if (!firebase.apps.length) {
                    firebaseApp = firebase.initializeApp(config);
                } else {
                    firebaseApp = firebase.app();
                }
                auth = firebase.auth();
                googleProvider = new firebase.auth.GoogleAuthProvider();
                googleProvider.addScope('profile');
                googleProvider.addScope('email');
                return true;
            }
        } catch (e) {
            console.warn('[Firebase Auth] Initialization warning:', e);
        }
        return false;
    }

    // Modal popup if Firebase keys haven't been provided in .env
    function showFirebaseSetupModal() {
        let existing = document.getElementById('firebaseSetupModal');
        if (existing) {
            existing.style.display = 'flex';
            return;
        }

        const modal = document.createElement('div');
        modal.id = 'firebaseSetupModal';
        modal.className = 'firebase-modal-overlay';
        modal.innerHTML = `
            <div class="firebase-modal-card">
                <div class="firebase-modal-header">
                    <div class="firebase-modal-icon">
                        <i class="fab fa-google"></i>
                    </div>
                    <div>
                        <h3>Firebase Authentication Ready</h3>
                        <p class="text-muted" style="margin:0; font-size:13px;">Connect your Firebase project</p>
                    </div>
                    <button class="firebase-modal-close" onclick="document.getElementById('firebaseSetupModal').style.display='none'">&times;</button>
                </div>
                <div class="firebase-modal-body">
                    <p>Firebase authentication integration is fully coded and ready!</p>
                    <p style="font-size:13px; color:var(--paper-muted);">
                        To activate live Google Sign-In, add your Firebase Web Credentials into your project's <code>.env</code> file:
                    </p>
                    <pre class="firebase-code-snippet">FIREBASE_API_KEY=AIzaSy...
FIREBASE_AUTH_DOMAIN=your-app.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_APP_ID=1:123456789:web:abcdef</pre>
                    <p style="font-size:13px; color:var(--lime);">
                        <i class="fas fa-check-circle"></i> In the meantime, you can create an account or sign in immediately using standard username/password!
                    </p>
                </div>
                <div class="firebase-modal-footer">
                    <button class="btn btn-primary btn-block" onclick="document.getElementById('firebaseSetupModal').style.display='none'">
                        Got it, continue with standard login
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.style.display = 'flex';
    }

    async function completeFirebaseLogin(user) {
        const idToken = await user.getIdToken();
        const response = await fetch('/api/auth/firebase-login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({
                idToken: idToken,
                next: new URLSearchParams(window.location.search).get('next') || ''
            })
        });

        const data = await response.json();
        if (!response.ok || !data.success || !data.redirect) {
            throw new Error(data.error || 'Failed to authenticate with TravelAI.');
        }
        window.location.assign(data.redirect);
    }

    async function handleGoogleSignIn(buttonEl) {
        const originalText = buttonEl ? buttonEl.innerHTML : '';
        if (buttonEl) {
            buttonEl.disabled = true;
            buttonEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Connecting with Google...';
        }

        if (!initFirebase()) {
            if (buttonEl) {
                buttonEl.disabled = false;
                buttonEl.innerHTML = originalText;
            }
            showFirebaseSetupModal();
            return;
        }

        try {
            const result = await auth.signInWithPopup(googleProvider);
            await completeFirebaseLogin(result.user);
        } catch (err) {
            if (err.code === 'auth/popup-blocked') {
                try {
                    await auth.signInWithRedirect(googleProvider);
                    return;
                } catch (redirectError) {
                    err = redirectError;
                }
            }

            console.error('[Firebase Auth Error]', err);
            if (err.code !== 'auth/popup-closed-by-user') {
                alert('Sign in failed: ' + (err.message || 'Unknown error'));
            }
            if (buttonEl) {
                buttonEl.disabled = false;
                buttonEl.innerHTML = originalText;
            }
        }
    }

    window.TravelAIFirebase = {
        init: initFirebase,
        signInWithGoogle: handleGoogleSignIn,
        showSetupModal: showFirebaseSetupModal
    };

    // Complete sign-in after a redirect fallback from browsers that block popups.
    document.addEventListener('DOMContentLoaded', async () => {
        if (!initFirebase()) return;
        try {
            const result = await auth.getRedirectResult();
            if (result && result.user) {
                await completeFirebaseLogin(result.user);
            }
        } catch (err) {
            console.error('[Firebase Auth Error]', err);
            alert('Sign in failed: ' + (err.message || 'Unknown error'));
        }
    });
})();
