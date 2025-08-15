// app/js/tutorial.js
function startTutorial() {
    // Fase 1: Vai al tab 'Dieta'
    var dietaTab = document.getElementById('dieta-tab');
    var tooltipDietaTab = new bootstrap.Tooltip(dietaTab, {
        title: "Clicca sul Tab Dieta!!!",
        trigger: 'manual'
    });
    tooltipDietaTab.show()

    setTimeout(function() {
        dietaTab.click();
        setTimeout(function() {
            tooltipDietaTab.hide();

            var tdeeInput = document.getElementById('tdee');
            var deficitInput = document.getElementById('deficit_calorico');
            var saveButton = document.querySelector('#personalInfoForm button[type="submit"]');

            // Mostra tooltip sul campo TDEE
            var tooltipTDEE = new bootstrap.Tooltip(tdeeInput, {
                title: "Inserisci il tuo TDEE (dispendio energetico giornaliero)",
                trigger: 'manual'
            });
            tooltipTDEE.show();

            // Passa al prossimo tooltip
            setTimeout(function() {
                tooltipTDEE.hide();

                // Mostra tooltip sul campo Deficit Calorico
                var tooltipDeficit = new bootstrap.Tooltip(deficitInput, {
                    title: "Inserisci il deficit calorico desiderato",
                    trigger: 'manual'
                });
                tooltipDeficit.show();

                // Passa al prossimo tooltip
                setTimeout(function() {
                    tooltipDeficit.hide();

                    // Mostra tooltip sul pulsante di Salva
                    var tooltipSave = new bootstrap.Tooltip(saveButton, {
                        title: "Clicca qui per salvare i tuoi dati",
                        trigger: 'manual'
                    });
                    tooltipSave.show();

                    // Nascondi l'ultimo tooltip dopo un breve ritardo
                    setTimeout(function() {
                        tooltipSave.hide();
                        goToWeeklyMenu();
                    }, 4000); // Mostra il tooltip per 4 secondi
                }, 4000); // Mostra il tooltip per 4 secondi
            }, 4000); // Mostra il tooltip per 4 secondi
        }, 500);
    }, 4000);
}

function goToWeeklyMenu() {
    // Fase 2: Vai al tab 'Menu Settimanale'
    var menuTab = document.getElementById('defaultOpen');
    var tooltipMenuTab = new bootstrap.Tooltip(menuTab, {
        title: "Clicca sul Tab Menu Settimanale!!!",
        trigger: 'manual'
    });
    tooltipMenuTab.show()

    setTimeout(function() {
        menuTab.click();

        setTimeout(function() {
            tooltipMenuTab.hide();
            var generateButton = document.getElementById('generateMenuBtn');
            var generateTooltip = new bootstrap.Tooltip(generateButton, {
                title: "Clicca qui per generare il menu settimanale",
                trigger: "manual",
                placement: "right"
            });

            generateTooltip.show();

            setTimeout(function() {
                generateTooltip.hide();
                completeTutorial();
            }, 4000);
        }, 500)
    }, 4000);
};


// Funzione per aggiornare che il tutorial è stato completato
function completeTutorial() {
    fetch('/complete_tutorial', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            tutorial_completed: true
        })
    }).then(response => {
        if (response.ok) {
            location.reload();
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    if (window.__MENU_TUTORIAL_DONE__) return;
    window.__MENU_TUTORIAL_DONE__ = true;

    if (typeof showTutorial !== 'undefined' && showTutorial) {
        // Mostra il modal di benvenuto
        var welcomeModal = new bootstrap.Modal(document.getElementById('welcomeModal'));
        welcomeModal.show();

        // Gestisci il click sul pulsante "Inizia il Tutorial"
        document.getElementById('startTutorial').addEventListener('click', function() {
            welcomeModal.hide();
            startTutorial();
        });
    }

    const closeButton = document.getElementById('closeTutorial');

    // Aggiungi un event listener al clic sul pulsante "Chiudi"
    if (closeButton){
        closeButton.addEventListener('click', function() {
            completeTutorial();
        });
    }
});