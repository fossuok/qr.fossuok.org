document.getElementById('github-btn').addEventListener('click', function () {
    document.getElementById('github-icon').classList.add('d-none');
    document.getElementById('github-spinner').classList.remove('d-none');
    document.getElementById('github-label').textContent = 'Redirecting to GitHub…';
    this.classList.add('disabled');
    this.setAttribute('aria-disabled', 'true');
});

// Show error banner if redirected back due to a failed OAuth callback
if (new URLSearchParams(window.location.search).has('error')) {
    const el = document.getElementById('login-error');
    el.classList.remove('d-none');
    el.classList.add('show');
    // Clean the URL so a refresh doesn't re-show the error
    history.replaceState(null, '', '/');
}
