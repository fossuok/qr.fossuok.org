(async function () {
    // UI elements
    const scanStatus = document.getElementById('scanStatus');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const scanResult = document.getElementById('scanResult');

    // State variables
    let stream = null;
    let rafId = null;
    let processing = false;
    let lastDecoded = null;
    let decoderInstance = null;
    const COOLDOWN_MS = 3000;

    function showMessage(html, isError = false) {
        scanResult.innerHTML = html;
        if (isError) {
            scanResult.classList.add('animate__animated', 'animate__shakeX');
            setTimeout(() => scanResult.classList.remove('animate__shakeX'), 1000);
        }
    }

    async function loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    async function ensureDecoder() {
        if (decoderInstance) return;
        // Try BarcodeDetector (native) first, fallback to jsQR
        if ('BarcodeDetector' in window) {
            decoderInstance = new BarcodeDetector({formats: ['qr_code']});
        } else {
            await loadScript('https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js');
            decoderInstance = {
                detect: async (source) => {
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(source, 0, 0, canvas.width, canvas.height);
                    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    const code = jsQR(imgData.data, imgData.width, imgData.height);
                    return code ? [{rawValue: code.data}] : [];
                }
            };
        }
    }

    async function startCamera() {
        try {
            await ensureDecoder();
            startBtn.classList.add('d-none');
            stopBtn.classList.remove('d-none');
            scanStatus.innerText = 'Initializing...';
            scanStatus.classList.replace('bg-danger', 'bg-warning');
        } catch (err) {
            showMessage('<div class="text-danger">Scanner library failed to load.</div>', true);
            return;
        }

        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: {facingMode: 'environment'},
                audio: false
            });
            video.srcObject = stream;
            await video.play();

            // Set canvas size matching video source
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;

            scanLoop();
            scanStatus.innerText = 'Scanning Live';
            scanStatus.classList.replace('bg-warning', 'bg-success');
        } catch (err) {
            showMessage(`<div class="text-danger">Camera start failed: ${err.message}</div>`, true);
            stopCamera();
        }
    }

    function stopCamera() {
        if (rafId) cancelAnimationFrame(rafId);
        rafId = null;
        processing = false;
        lastDecoded = null;
        if (stream) {
            stream.getTracks().forEach(t => t.stop());
            stream = null;
        }
        video.pause();
        video.srcObject = null;
        startBtn.classList.remove('d-none');
        stopBtn.classList.add('d-none');
        scanStatus.innerText = 'Stopped';
        scanStatus.classList.replace('bg-success', 'bg-danger');
        scanStatus.classList.replace('bg-warning', 'bg-danger');
    }

    async function scanLoop() {
        if (!stream || processing) {
            rafId = requestAnimationFrame(scanLoop);
            return;
        }

        try {
            const results = await decoderInstance.detect(video);
            if (results.length > 0) {
                handleDecoded(results[0].rawValue);
            }
        } catch (e) {
            // Ignore transient errors
        }
        rafId = requestAnimationFrame(scanLoop);
    }

    function scheduleResume(ms) {
        setTimeout(() => {
            processing = false;
        }, ms);
    }

    async function handleDecoded(decodedText) {
        if (processing) return;
        if (decodedText && decodedText === lastDecoded) {
            processing = true;
            scheduleResume(COOLDOWN_MS);
            return;
        }

        processing = true;
        lastDecoded = decodedText;

        showMessage('<div class="spinner-border text-primary my-4" role="status"></div><p>Verifying Attendee...</p>');

        try {
            const res = await fetch('/api/verify', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({payload: decodedText}),
            });

            if (res.ok) {
                const json = await res.json();
                if (json.valid) {
                    const timeStr = json.user.attended_at ? new Date(json.user.attended_at).toLocaleTimeString() : 'Just now';
                    const statusColor = json.already_marked ? 'warning' : 'success';
                    const statusIcon  = json.already_marked ? 'exclamation-triangle-fill' : 'check-circle-fill';
                    const statusText  = json.already_marked ? 'ALREADY MARKED' : 'ATTENDANCE MARKED';
                    const eventLine   = json.event ? `<p class="small text-muted mb-3"><i class="bi bi-calendar-event me-1"></i>${escapeHtml(json.event.title)}</p>` : '';

                    showMessage(`
                        <div class="w-100 animate__animated animate__fadeInUp">
                            <div class="display-3 text-${statusColor} mb-3"><i class="bi bi-${statusIcon}"></i></div>
                            <h4 class="fw-bold mb-1">${escapeHtml(json.user.name)}</h4>
                            <p class="text-muted small mb-1">${escapeHtml(json.user.email)}</p>
                            ${eventLine}
                            <div class="badge bg-${statusColor} w-100 py-3 rounded-4 fs-6 py-3">
                                <i class="bi bi-${json.already_marked ? 'clock-history' : 'person-check'} me-2"></i> ${statusText}<br>
                                <small class="opacity-75">${timeStr}</small>
                            </div>
                        </div>
                    `);
                } else {
                    showMessage('<div class="display-3 text-danger mb-3"><i class="bi bi-x-circle-fill"></i></div><h4 class="fw-bold">Invalid QR</h4><p class="text-muted">This code is not recognized.</p>', true);
                }
            } else {
                showMessage('<div class="alert alert-warning">Verify API error: ' + res.status + '</div>', true);
            }
        } catch (err) {
            showMessage('<div class="alert alert-danger">Network Error</div>', true);
        } finally {
            scheduleResume(COOLDOWN_MS);
        }
    }

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, function (m) {
            return ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'})[m];
        });
    }

    startBtn.addEventListener('click', () => {
        if (!stream) startCamera();
    });
    stopBtn.addEventListener('click', () => {
        stopCamera();
    });

    window.addEventListener('beforeunload', () => stopCamera());
})();
