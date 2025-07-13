// PWA Installer semplificato
let deferredPrompt;
let installButton = document.getElementById('install-button');

// Gestione del prompt di installazione
window.addEventListener('beforeinstallprompt', (e) => {
    console.log('PWA: Prompt di installazione disponibile');
    e.preventDefault();
    deferredPrompt = e;
    showInstallButton();
});

function showInstallButton() {
    if (installButton) {
        installButton.style.display = 'block';
        installButton.addEventListener('click', installApp);
    }
}

function installApp() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                console.log('PWA: App installata con successo');
                hideInstallButton();
            } else {
                console.log('PWA: Installazione annullata');
            }
            deferredPrompt = null;
        });
    }
}

function hideInstallButton() {
    if (installButton) {
        installButton.style.display = 'none';
    }
}

// Nascondi il pulsante se l'app è già installata
window.addEventListener('appinstalled', (evt) => {
    console.log('PWA: App installata');
    hideInstallButton();
});

// Rileva se l'app è in modalità standalone
function isStandalone() {
    return window.matchMedia('(display-mode: standalone)').matches ||
           window.navigator.standalone === true;
}

// Nascondi il pulsante se già in modalità standalone
if (isStandalone()) {
    hideInstallButton();
}