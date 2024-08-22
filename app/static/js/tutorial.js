document.addEventListener('DOMContentLoaded', function () {
    if (typeof showTutorial !== 'undefined' && showTutorial) {
        // Mostra il modal di benvenuto
        var welcomeModal = new bootstrap.Modal(document.getElementById('welcomeModal'));
        welcomeModal.show();

        // Gestisci il click sul pulsante "Inizia il Tutorial"
        document.getElementById('startTutorial').addEventListener('click', function () {
            welcomeModal.hide();
            startTutorial();
        });
    }
});

function startTutorial() {
    // Fase 1: Vai al tab 'Dieta'
    var dietaTab = document.getElementById('dieta-tab');
    dietaTab.click();

    // Aggiungi un piccolo delay per mostrare i dati mancanti
    setTimeout(function () {
        alert("Per iniziare, completa i dati mancanti nel tab 'Dieta'.");
    }, 500);

    // Aggiungi altre fasi del tutorial come passare al menu settimanale ecc.
}

// Funzione per aggiornare che il tutorial è stato completato
function completeTutorial() {
    fetch('/complete_tutorial', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ tutorial_completed: true })
    }).then(response => {
        if (response.ok) {
            alert('Tutorial completato!');
        }
    });
}
