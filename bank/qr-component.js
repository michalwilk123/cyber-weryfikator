(function() {
    'use strict';

    // Secret will be fetched from static file
    let FETCHED_SECRET = null;
    const QR_CODE_PREFIX = 'verification-code:';
    const QR_LIBRARY_URL = '/static/qrcode.min.js';
    const SECRET_FILE_URL = '/static/secret.txt';
    const REFRESH_INTERVAL_MS = 1000; // 1 second

    // Component configuration
    const config = {
        containerId: 'qr-verification',
        qrSize: 256,
        qrMargin: 2
    };

    // Track refresh interval
    let refreshIntervalId = null;

    // Inject styles for the QR code container
    function injectStyles() {
        const styleId = 'qr-component-styles';
        if (document.getElementById(styleId)) {
            return; // Styles already injected
        }

        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .qr-verification-container {
                display: inline-flex;
                flex-direction: column;
                align-items: center;
                padding: 1rem;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }

            .qr-verification-container canvas,
            .qr-verification-container img {
                border: 2px solid #e0e0e0;
                border-radius: 4px;
            }

            #qrcode-canvas {
                display: flex;
                justify-content: center;
                align-items: center;
            }

            .qr-verification-title {
                margin-bottom: 1rem;
                font-size: 1rem;
                font-weight: 600;
                color: #333;
                text-align: center;
            }

            .qr-verification-loading {
                color: #666;
                font-style: italic;
                padding: 2rem;
            }

            .qr-verification-error {
                color: #d32f2f;
                padding: 1rem;
                background-color: #ffebee;
                border-radius: 4px;
                font-size: 0.9rem;
            }
        `;
        document.head.appendChild(style);
    }

    // Fetch secret from static file
    async function fetchSecret() {
        try {
            const response = await fetch(SECRET_FILE_URL);
            if (!response.ok) {
                throw new Error(`Failed to fetch secret: ${response.status} ${response.statusText}`);
            }
            const secret = await response.text();
            return secret.trim(); // Remove any whitespace/newlines
        } catch (error) {
            console.error('Error fetching secret:', error);
            throw new Error('Failed to load verification secret');
        }
    }

    // Load QR code library dynamically
    function loadQRCodeLibrary() {
        return new Promise((resolve, reject) => {
            // Check if library is already loaded
            if (window.QRCode) {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = QR_LIBRARY_URL;
            script.onload = resolve;
            script.onerror = () => reject(new Error('Failed to load QR code library'));
            document.head.appendChild(script);
        });
    }

    // Generate the QR code
    function generateQRCode(container, secret) {
        const qrData = `${QR_CODE_PREFIX}${secret}`;
        
        // Clear previous QR code and loading message
        const existingTitle = container.querySelector('.qr-verification-title');
        const existingCanvas = container.querySelector('#qrcode-canvas');
        const loadingMessage = container.querySelector('.qr-verification-loading');
        
        // Remove loading message if exists
        if (loadingMessage) {
            loadingMessage.remove();
        }
        
        // Remove old QR code if exists
        if (existingCanvas) {
            existingCanvas.remove();
        }
        
        // Add title if it doesn't exist
        if (!existingTitle) {
            const titleDiv = document.createElement('div');
            titleDiv.className = 'qr-verification-title';
            titleDiv.textContent = 'Zweryfikuj stronę';
            container.insertBefore(titleDiv, container.firstChild);
        }

        const qrContainer = document.createElement('div');
        qrContainer.id = 'qrcode-canvas';
        container.appendChild(qrContainer);

        try {
            // Using qrcodejs library API
            new QRCode(qrContainer, {
                text: qrData,
                width: config.qrSize,
                height: config.qrSize,
                colorDark: '#000000',
                colorLight: '#FFFFFF',
                correctLevel: QRCode.CorrectLevel.H
            });
        } catch (error) {
            console.error('QR code generation error:', error);
            container.innerHTML = '<div class="qr-verification-error">Błąd generowania kodu QR</div>';
        }
    }

    // Show error message
    function showError(container, message) {
        container.innerHTML = `<div class="qr-verification-error">${message}</div>`;
    }

    // Check and update QR code if secret changed
    async function checkAndUpdateQRCode() {
        try {
            const newSecret = await fetchSecret();
            
            // Only regenerate if secret has changed
            if (newSecret !== FETCHED_SECRET) {
                FETCHED_SECRET = newSecret;
                
                const container = document.getElementById(config.containerId);
                if (container) {
                    generateQRCode(container, FETCHED_SECRET);
                }
            }
        } catch (error) {
            console.error('Error checking for secret updates:', error);
        }
    }

    // Start the refresh interval
    function startRefreshInterval() {
        // Clear any existing interval
        if (refreshIntervalId) {
            clearInterval(refreshIntervalId);
        }
        
        // Set up new interval to check every second
        refreshIntervalId = setInterval(checkAndUpdateQRCode, REFRESH_INTERVAL_MS);
    }

    // Stop the refresh interval
    function stopRefreshInterval() {
        if (refreshIntervalId) {
            clearInterval(refreshIntervalId);
            refreshIntervalId = null;
        }
    }

    // Initialize the component
    async function initialize() {
        try {
            // Inject styles
            injectStyles();

            // Find or create container
            let container = document.getElementById(config.containerId);
            
            if (!container) {
                // If no container exists, create one and append to body
                container = document.createElement('div');
                container.id = config.containerId;
                document.body.appendChild(container);
            }

            // Add container class
            container.className = 'qr-verification-container';
            container.innerHTML = '<div class="qr-verification-loading">Ładowanie...</div>';

            // Fetch secret from static file
            FETCHED_SECRET = await fetchSecret();

            // Load QR code library
            await loadQRCodeLibrary();

            // Generate QR code with fetched secret
            generateQRCode(container, FETCHED_SECRET);

            // Start automatic refresh interval
            startRefreshInterval();

        } catch (error) {
            console.error('QR Component initialization error:', error);
            const container = document.getElementById(config.containerId);
            if (container) {
                showError(container, 'Nie można załadować komponentu weryfikacyjnego');
            }
        }
    }

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

    // Expose API for manual initialization if needed
    window.QRVerificationComponent = {
        init: initialize,
        getSecret: () => FETCHED_SECRET,
        startRefresh: startRefreshInterval,
        stopRefresh: stopRefreshInterval
    };

    // Clean up interval when page is unloaded
    window.addEventListener('beforeunload', stopRefreshInterval);

})();

