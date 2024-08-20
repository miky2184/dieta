let currentDay = '';
let currentMeal = '';
let selectedWeekId = null;
var myChart;

function openTab(evt, tabName) {
    const tabcontent = document.querySelectorAll(".tabcontent");
    tabcontent.forEach(tab => tab.style.display = "none");
    const tablinks = document.querySelectorAll(".tablinks");
    tablinks.forEach(link => link.className = link.className.replace(" active", ""));
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}

function cambiaMenuSettimana() {
    const select = document.getElementById('settimana_select');
    const settimanaId = select.value;
    fetch(`/menu_settimana/${settimanaId}`)
        .then(response => response.json())
        .then(data => {
            if (data.menu) {
                // Aggiorna il contenuto del menu con i dati ricevuti
                aggiornaTabellaMenu(data.menu);
                aggiornaTabellaListaDellaSpesa(data.menu.all_food);
            }
        });
}

function aggiornaTabellaMenu(menu) {
    const tbody = document.getElementById('menu_tbody');
    tbody.innerHTML = ''; // Pulisci la tabella

    const days = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato', 'domenica'];
    const macroNutrients = ['kcal', 'carboidrati', 'proteine', 'grassi'];

    // Itera su ogni pasto e giorno
    ['colazione', 'spuntino_mattina', 'pranzo', 'spuntino_pomeriggio', 'cena'].forEach(pasto => {
        const tr = document.createElement('tr');
        const tdPasto = document.createElement('td');
        tdPasto.textContent = capitalize(pasto.replace('_', ' '));
        tr.appendChild(tdPasto);
        days.forEach(giorno => {
            const td = document.createElement('td');
            if (menu.day[giorno].pasto[pasto].ricette && menu.day[giorno].pasto[pasto].ricette.length > 0) {
                menu.day[giorno].pasto[pasto].ricette.forEach(ricetta => {
                    const div = document.createElement('div');
                    // Aggiungi il contenuto di testo
                    div.textContent = `${ricetta.nome_ricetta} (${ricetta.qta}x)`;

                    // Aggiungi gli attributi per il popover
                    div.setAttribute('data-bs-toggle', 'popover');
                    div.setAttribute('data-bs-title', ricetta.ricetta);

                    // Aggiungi la classe "recipe-cell"
                    div.classList.add('recipe-cell');

                    // Aggiungi il div all'elemento td (o un altro elemento genitore)
                    td.appendChild(div);

                    // Inizializza il popover sul nuovo elemento
                    new bootstrap.Popover(div);
                });
            }
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });

    // Aggiorna le informazioni rimanenti
    days.forEach(giorno => {
        macroNutrients.forEach(macro => {
            const remainingValue = menu.day[giorno][macro];
            document.getElementById(`remaining-${macro}-${giorno}`).textContent = remainingValue.toFixed(2);
        });
    });
}

function aggiornaTabellaListaDellaSpesa(idsAllFood) {
    const tbody = document.getElementById('spesa_tbody');
    tbody.innerHTML = ''; // Pulisci la tabella

    // Esegui una chiamata fetch per ottenere la lista della spesa basata sugli ID degli alimenti
    fetch('/get_lista_spesa', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ids_all_food: idsAllFood
            })
        })
        .then(response => response.json())
        .then(data => {
            data.lista_spesa.forEach(item => {
                const tr = document.createElement('tr');
                const tdAlimento = document.createElement('td');
                const tdQuantita = document.createElement('td');
                tdAlimento.textContent = item.alimento;
                tdQuantita.textContent = item.qta_totale;
                tr.appendChild(tdAlimento);
                tr.appendChild(tdQuantita);
                tbody.appendChild(tr);
            });
        })
        .catch(error => console.error('Errore nel recupero della lista della spesa:', error));
}

function saveRicetta(ricettaData) {
    fetch('/save_recipe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(ricettaData)
        })
        .then(response => response.json())
        .then(data => {
            // window.location.href = '/';
        })
        .catch((error) => {
            console.error('Error:', error);
        });
}

function toggleStatusRicetta(ricettaData) {
    fetch('/toggle_recipe_status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(ricettaData)
        })
        .then(response => response.json())
        .then(data => {
            // window.location.href = '/';
        })
        .catch((error) => {
            console.error('Error:', error);
        });
}

function filterTable() {
    const nomeFilter = document.getElementById('filter-nome').value.toLowerCase();

    const calorieMin = parseFloat(document.getElementById('filter-calorie-min').value) || -Infinity;
    const calorieMax = parseFloat(document.getElementById('filter-calorie-max').value) || Infinity;
    const carboMin = parseFloat(document.getElementById('filter-carbo-min').value) || -Infinity;
    const carboMax = parseFloat(document.getElementById('filter-carbo-max').value) || Infinity;
    const proteineMin = parseFloat(document.getElementById('filter-proteine-min').value) || -Infinity;
    const proteineMax = parseFloat(document.getElementById('filter-proteine-max').value) || Infinity;
    const grassiMin = parseFloat(document.getElementById('filter-grassi-min').value) || -Infinity;
    const grassiMax = parseFloat(document.getElementById('filter-grassi-max').value) || Infinity;

    const colazioneFilter = document.getElementById('filter-colazione').value;
    const colazioneSecFilter = document.getElementById('filter-colazione-sec').value;
    const spuntinoFilter = document.getElementById('filter-spuntino').value;
    const principaleFilter = document.getElementById('filter-principale').value;
    const contornoFilter = document.getElementById('filter-contorno').value;
    const attivaFilter = document.getElementById('filter-attiva').value;

    const table = document.getElementById('ricette-table').querySelector('tbody');

    const rows = table.getElementsByTagName('tr');

    for (let i = 0; i < rows.length; i++) {
        const cells = rows[i].getElementsByTagName('td');
        const nomeCell = cells[0].textContent.toLowerCase();

        const calorieCell = parseFloat(cells[1].textContent) || 0;
        const carboCell = parseFloat(cells[2].textContent) || 0;
        const proteineCell = parseFloat(cells[3].textContent) || 0;
        const grassiCell = parseFloat(cells[4].textContent) || 0;

        const colazioneCell = cells[5].querySelector('input').checked.toString();
        const colazioneSecCell = cells[6].querySelector('input').checked.toString();
        const spuntinoCell = cells[7].querySelector('input').checked.toString();
        const principaleCell = cells[8].querySelector('input').checked.toString();
        const contornoCell = cells[9].querySelector('input').checked.toString();
        const attivaCell = cells[10].querySelector('input').checked.toString();

        const colazioneMatch = (colazioneFilter === 'all') || (colazioneFilter === colazioneCell);
        const colazioneSecMatch = (colazioneSecFilter === 'all') || (colazioneSecFilter === colazioneSecCell);
        const spuntinoMatch = (spuntinoFilter === 'all') || (spuntinoFilter === spuntinoCell);
        const principaleMatch = (principaleFilter === 'all') || (principaleFilter === principaleCell);
        const contornoMatch = (contornoFilter === 'all') || (contornoFilter === contornoCell);
        const attivaMatch = (attivaFilter === 'all') || (attivaFilter === attivaCell);

        const calorieMatch = calorieCell >= calorieMin && calorieCell <= calorieMax;
        const carboMatch = carboCell >= carboMin && carboCell <= carboMax;
        const proteineMatch = proteineCell >= proteineMin && proteineCell <= proteineMax;
        const grassiMatch = grassiCell >= grassiMin && grassiCell <= grassiMax;

        if (nomeCell.includes(nomeFilter) &&
            calorieMatch &&
            carboMatch &&
            proteineMatch &&
            grassiMatch &&
            colazioneMatch &&
            colazioneSecMatch &&
            spuntinoMatch &&
            principaleMatch &&
            contornoMatch &&
            attivaMatch) {
            rows[i].style.display = '';
        } else {
            rows[i].style.display = 'none';
        }
    }
}

// Funzione per filtrare la tabella degli alimenti
function filterAlimentiTable() {
    const nomeFilter = document.getElementById('filter-nome-alimento').value.toLowerCase();

    const calorieMin = parseFloat(document.getElementById('filter-calorie-min').value) || -Infinity;
    const calorieMax = parseFloat(document.getElementById('filter-calorie-max').value) || Infinity;
    const carboMin = parseFloat(document.getElementById('filter-carbo-min').value) || -Infinity;
    const carboMax = parseFloat(document.getElementById('filter-carbo-max').value) || Infinity;
    const proteineMin = parseFloat(document.getElementById('filter-proteine-min').value) || -Infinity;
    const proteineMax = parseFloat(document.getElementById('filter-proteine-max').value) || Infinity;
    const grassiMin = parseFloat(document.getElementById('filter-grassi-min').value) || -Infinity;
    const grassiMax = parseFloat(document.getElementById('filter-grassi-max').value) || Infinity;

    const macroFilter = document.getElementById('filter-macro').value;
    const fruttaFilter = document.getElementById('filter-frutta').value;
    const carneBiancaFilter = document.getElementById('filter-carne-bianca').value;
    const carneRossaFilter = document.getElementById('filter-carne-rossa').value;
    const paneFilter = document.getElementById('filter-pane').value;
    const verduraFilter = document.getElementById('filter-verdura').value;
    const confezionatoFilter = document.getElementById('filter-confezionato').value;
    const veganFilter = document.getElementById('filter-vegan').value;
    const pesceFilter = document.getElementById('filter-pesce').value;

    const table = document.getElementById('alimenti-table').querySelector('tbody');
    const rows = table.getElementsByTagName('tr');

    for (let i = 0; i < rows.length; i++) {
        const cells = rows[i].getElementsByTagName('td');
        const nomeCell = cells[0].textContent.toLowerCase();

        const calorieCell = parseFloat(cells[1].textContent) || 0;
        const carboCell = parseFloat(cells[2].textContent) || 0;
        const proteineCell = parseFloat(cells[3].textContent) || 0;
        const grassiCell = parseFloat(cells[4].textContent) || 0;

        const macroCell = cells[5].textContent;
        const fruttaCell = cells[6].querySelector('input').checked.toString();
        const carneBiancaCell = cells[7].querySelector('input').checked.toString();
        const carneRossaCell = cells[8].querySelector('input').checked.toString();
        const paneCell = cells[9].querySelector('input').checked.toString();
        const verduraCell = cells[10].querySelector('input').checked.toString();
        const confezionatoCell = cells[11].querySelector('input').checked.toString();
        const veganCell = cells[12].querySelector('input').checked.toString();
        const pesceCell = cells[13].querySelector('input').checked.toString();

        const calorieMatch = calorieCell >= calorieMin && calorieCell <= calorieMax;
        const carboMatch = carboCell >= carboMin && carboCell <= carboMax;
        const proteineMatch = proteineCell >= proteineMin && proteineCell <= proteineMax;
        const grassiMatch = grassiCell >= grassiMin && grassiCell <= grassiMax;

        const macroMatch = (macroFilter === 'all') || (macroFilter === macroCell);
        const fruttaMatch = (fruttaFilter === 'all') || (fruttaFilter === fruttaCell);
        const carneBiancaMatch = (carneBiancaFilter === 'all') || (carneBiancaFilter === carneBiancaCell);
        const carneRossaMatch = (carneRossaFilter === 'all') || (carneRossaFilter === carneRossaCell);
        const paneMatch = (paneFilter === 'all') || (paneFilter === paneCell);
        const verduraMatch = (verduraFilter === 'all') || (verduraFilter === verduraCell);
        const confezionatoMatch = (confezionatoFilter === 'all') || (confezionatoFilter === confezionatoCell);
        const veganMatch = (veganFilter === 'all') || (veganFilter === veganCell);
        const pesceMatch = (pesceFilter === 'all') || (pesceFilter === pesceCell);

        if (
            nomeCell.includes(nomeFilter) &&
            calorieMatch &&
            carboMatch &&
            proteineMatch &&
            grassiMatch &&
            macroMatch &&
            fruttaMatch &&
            carneBiancaMatch &&
            carneRossaMatch &&
            paneMatch &&
            verduraMatch &&
            confezionatoMatch &&
            veganMatch &&
            pesceMatch
        ) {
            rows[i].style.display = '';
        } else {
            rows[i].style.display = 'none';
        }
    }
}

function populateIngredientsModal(ingredients) {
    const tbody = document.getElementById('ingredientsBody');
    tbody.innerHTML = ''; // Clear existing rows
    ingredients.forEach(ingredient => {
        const row = `<tr>
            <td>${ingredient['nome']}</td>
            <td><input type="number" class="form-control form-control-sm" id="quantity-${ingredient['id']}" value="${ingredient['qta']}"></td>
            <td>
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-outline-success btn-sm update-ingredient" data-id="${ingredient['id']}" data-recipe-id="${ingredient['id_ricetta']}">Salva</button>
                    <button type="button" class="btn btn-outline-danger btn-sm delete-ingredient" data-id="${ingredient['id']}" data-recipe-id="${ingredient['id_ricetta']}">Elimina</button>
                </div>
            </td>
        </tr>`;
        tbody.innerHTML += row;
    });
}


function deleteIngredient(ingredientId, recipeId, button) {
    fetch('/delete_ingredient', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ingredient_id: ingredientId,
                recipe_id: recipeId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Rimuovi la riga della tabella se l'eliminazione è avvenuta con successo
                button.closest('tr').remove();
            }
        })
        .catch((error) => {
            console.error('Error:', error);
        });
}

function updateIngredient(ingredientId, recipeId, qta) {
    fetch('/update_ingredient', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ingredient_id: ingredientId,
                recipe_id: recipeId,
                quantity: qta
            })
        })
        .then(response => response.json())
        .then(data => {})
        .catch((error) => {
            console.error('Error:', error);
        });
}


function addIngredientToRecipe() {
    const ingredientId = document.getElementById('ingredient-select').value;
    const quantity = document.getElementById('ingredient-quantity').value;
    const recipeId = document.getElementById('modal-recipe-id').value;

    fetch('/add_ingredient_to_recipe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                recipe_id: recipeId,
                ingredient_id: ingredientId,
                quantity: quantity
            })
        })
        .then(response => response.json())
        .then(data => {})
        .catch((error) => {
            console.error('Error:', error);
        });
}

function populateDietaForm(data) {
    // Popola i campi del form con i dati ricevuti
    document.querySelector('[name="id"]').value = data.id || '';
    document.querySelector('[name="nome"]').value = data.nome || '';
    document.querySelector('[name="cognome"]').value = data.cognome || '';
    document.querySelector('[name="sesso"]').value = data.sesso || '';
    document.querySelector('[name="eta"]').value = Math.round(data.eta) || '';
    document.querySelector('[name="altezza"]').value = Math.round(data.altezza) || '';
    document.querySelector('[name="peso"]').value = Math.round(data.peso) || '';
    document.getElementById('tdee').value = data.tdee || '';
    document.getElementById('deficit_calorico').value = data.deficit_calorico || '';
    document.getElementById('bmi').value = Math.round(data.bmi * 100) / 100 || '';
    document.getElementById('peso_ideale').value = Math.round(data.peso_ideale) || '';
    document.getElementById('meta_basale').value = Math.round(data.meta_basale) || '';
    document.getElementById('meta_giornaliero').value = Math.round(data.meta_giornaliero) || '';
    document.getElementById('calorie_giornaliere').value = Math.round(data.calorie_giornaliere) || '';
    document.getElementById('calorie_settimanali').value = Math.round(data.calorie_settimanali) || '';
    document.getElementById('carboidrati_input').value = Math.round(data.carboidrati) || '';
    document.getElementById('proteine_input').value = Math.round(data.proteine) || '';
    document.getElementById('grassi_input').value = Math.round(data.grassi) || '';
}

function calcolaPesoIdeale(data) {
    const formule = {
        lorenz: (altezza, sesso, eta) => sesso === 'M' ? altezza - 100 - (altezza - 150) / 4 : altezza - 100 - (altezza - 150) / 2,
        broca: (altezza, sesso, eta) => sesso === 'M' ? altezza - 100 : altezza - 104,
        berthean: (altezza, sesso, eta) => 0.8 * (altezza - 100) + eta / 2,
        keys: (altezza, sesso, eta) => sesso === 'M' ? 22.1 * Math.pow(altezza / 100, 2) : 20.6 * Math.pow(altezza / 100, 2),
    };

    const risultati = Object.values(formule).map(f => f(data.altezza, data.sesso, data.eta));
    return (risultati.reduce((a, b) => a + b, 0) / risultati.length).toFixed(0);
}

function synchronizeFields() {
    // Copia i valori dai campi visibili/disabilitati ai campi nascosti
    const bmiVisible = document.getElementById('bmi');
    const bmiHidden = document.getElementById('bmi_hidden');
    bmiHidden.value = bmiVisible.value;

    const pesoIdealeVisible = document.getElementById('peso_ideale');
    const pesoIdealeHidden = document.getElementById('peso_ideale_hidden');
    pesoIdealeHidden.value = pesoIdealeVisible.value;

    // Aggiungi altre sincronizzazioni qui
    const metaBasaleVisible = document.getElementById('meta_basale');
    const metaBasaleHidden = document.getElementById('meta_basale_hidden');
    metaBasaleHidden.value = metaBasaleVisible.value;

    const metaGiornalieroVisible = document.getElementById('meta_giornaliero');
    const metaGiornalieroHidden = document.getElementById('meta_giornaliero_hidden');
    metaGiornalieroHidden.value = metaGiornalieroVisible.value;

    const calorieGiornaliereVisible = document.getElementById('calorie_giornaliere');
    const calorieGiornaliereHidden = document.getElementById('calorie_giornaliere_hidden');
    calorieGiornaliereHidden.value = calorieGiornaliereVisible.value;

    const calorieSettimanaliVisible = document.getElementById('calorie_settimanali');
    const calorieSettimanaliHidden = document.getElementById('calorie_settimanali_hidden');
    calorieSettimanaliHidden.value = calorieSettimanaliVisible.value;

    const carboidratiVisible = document.getElementById('carboidrati_input');
    const carboidratiHidden = document.getElementById('carboidrati_hidden');
    carboidratiHidden.value = carboidratiVisible.value;

    const proteineVisible = document.getElementById('proteine_input');
    const proteineHidden = document.getElementById('proteine_hidden');
    proteineHidden.value = proteineVisible.value;

    const grassiVisible = document.getElementById('grassi_input');
    const grassiHidden = document.getElementById('grassi_hidden');
    grassiHidden.value = grassiVisible.value;
}

function calculateResults() {
    const formData = new FormData(form);
    const data = {
        nome: formData.get('nome'),
        cognome: formData.get('cognome'),
        sesso: formData.get('sesso'),
        eta: formData.get('eta'),
        peso: formData.get('peso'),
        altezza: formData.get('altezza'),
        tdee: formData.get('tdee'),
        deficit: formData.get('deficit_calorico')
    };

    // Esegui i calcoli basati sui dati inseriti
    let bmi = (data.peso / Math.pow(data.altezza / 100, 2)).toFixed(1); // esempio di calcolo del BMI, con un'altezza fissa

    idealWeight = calcolaPesoIdeale(data)

    let harrisBenedict;
    let mifflinStJeor;

    if (data.sesso === 'M') {
        harrisBenedict = 88.362 + (13.397 * data.peso) + (4.799 * data.altezza) - (5.677 * data.eta);
        mifflinStJeor = 10 * data.peso + 6.25 * data.altezza - 5 * data.eta + 5;
    } else if (data.sesso === 'F') {
        harrisBenedict = 47.593 + (9.247 * data.peso) + (3.098 * data.altezza) - (4, 330 * data.eta);
        mifflinStJeor = 10 * data.peso + 6.25 * data.altezza - 5 * data.eta - 161;
    }

    let metaBasaleValue = ((harrisBenedict + mifflinStJeor) / 2).toFixed(0);

    let metaDailyValue = (metaBasaleValue * data.tdee).toFixed(0);

    let calorieGiornaliereValue = ((metaDailyValue - (metaDailyValue * data.deficit / 100))).toFixed(0);

    let calorieSettimanaliValue = (calorieGiornaliereValue * 7).toFixed(0);

    let carboidratiValue = (calorieGiornaliereValue * 0.6 / 4).toFixed(0);
    let proteineValue = (calorieGiornaliereValue * 0.15 / 4).toFixed(0);;
    let grassiValue = (calorieGiornaliereValue * 0.25 / 9).toFixed(0);;


    if (isNaN(bmi)) {
        bmi = 0; // Imposta un valore di default o gestisci l'errore come necessario
    }

    if (isNaN(idealWeight)) {
        idealWeight = 0; // Imposta un valore di default o gestisci l'errore come necessario
    }

    if (isNaN(metaBasaleValue)) {
        metaBasaleValue = 0; // Imposta un valore di default o gestisci l'errore come necessario
    }

    if (isNaN(metaDailyValue)) {
        metaDailyValue = 0; // Imposta un valore di default o gestisci l'errore come necessario
    }

    if (isNaN(calorieGiornaliereValue)) {
        calorieGiornaliereValue = 0; // Imposta un valore di default o gestisci l'errore come necessario
    }

    if (isNaN(calorieSettimanaliValue)) {
        calorieSettimanaliValue = 0; // Imposta un valore di default o gestisci l'errore come necessario
    }

    if (isNaN(carboidratiValue)) {
        carboidratiValue = 0; // Imposta un valore di default o gestisci l'errore come necessario
    }

    if (isNaN(proteineValue)) {
        proteineValue = 0; // Imposta un valore di default o gestisci l'errore come necessario
    }

    if (isNaN(grassiValue)) {
        grassiValue = 0; // Imposta un valore di default o gestisci l'errore come necessario
    }

    bmiInput.value = bmi;
    idealWeightInput.value = idealWeight;
    metaBasale.value = metaBasaleValue;
    metaDaily.value = metaDailyValue;
    calorieGiornaliere.value = calorieGiornaliereValue;
    calorieSettimanali.value = calorieSettimanaliValue;
    carboidrati.value = carboidratiValue;
    proteine.value = proteineValue;
    grassi.value = grassiValue;
}

// Funzione per salvare l'alimento
function saveAlimento(alimentoData) {
    fetch('/save_alimento', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(alimentoData)
        })
        .then(response => response.json())
        .then(data => {})
        .catch((error) => {
            console.error('Errore:', error);
        });
}

// Funzione per eliminare l'alimento
function deleteAlimento(alimentoId) {
    fetch('/delete_alimento', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id: alimentoId
            })
        })
        .then(response => response.json())
        .then(data => {
            window.location.reload(); // Ricarica la pagina per aggiornare la lista
        })
        .catch((error) => {
            console.error('Errore:', error);
        });
}

// Utility function to capitalize the first letter of a string
function capitalize(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

function loadMenuData() {
    selectedWeekId = document.getElementById('selectMenu').value;
    // Fai il fetch per caricare i dati del menu per la settimana selezionata
    fetch(`/menu_settimana/${selectedWeekId}`)
        .then(response => response.json())
        .then(data => {
            // Qui inserisci la logica per caricare i dati del menu nel div #menuEditor
            renderMenuEditor(data);
        })
        .catch(error => console.error('Errore nel caricamento del menu:', error));
}

function filterDayCards() {
    const selectedDay = document.getElementById('selectDay').value;
    const cards = document.querySelectorAll('.day-container');

    cards.forEach(card => {
        const cardDay = card.getAttribute('data-day');
        if (selectedDay === 'all' || selectedDay === cardDay) {
            card.style.display = 'block'; // Mostra la card
        } else {
            card.style.display = 'none'; // Nascondi la card
        }
    });
}

// Funzione per formattare i nomi dei pasti
function formatMealName(meal) {
    switch (meal) {
        case 'spuntino_mattina':
            return 'Spuntino Mattina';
        case 'spuntino_pomeriggio':
            return 'Spuntino Pomeriggio';
        default:
            return capitalize(meal);
    }
}


function renderMenuEditor(data) {
    const selectedWeek = document.getElementById('settimana_select').value;
    const selectedDay = document.getElementById('day_select') ? document.getElementById('day_select').value : null;

    const menuEditor = document.getElementById("menuEditor");
    menuEditor.innerHTML = ''; // Pulisce l'editor

    // Cerca il contenitore esistente dei macronutrienti rimanenti
    let macrosContainer = document.querySelector('.remaining-macros-container');
    if (!macrosContainer) {
        // Se il contenitore non esiste, creane uno nuovo
        macrosContainer = document.createElement('div');
        macrosContainer.classList.add('remaining-macros-container');
        const menuContainer = document.getElementById('menuEditor');
        menuContainer.parentNode.insertBefore(macrosContainer, menuContainer);
    } else {
        // Se il contenitore esiste, puliscilo
        macrosContainer.innerHTML = '';
    }

    const menu = data.menu;

    const days = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato', 'domenica'];
    const meals = ['colazione', 'spuntino_mattina', 'pranzo', 'spuntino_pomeriggio', 'cena'];

    // Creazione della tabellina per i rimanenti giornalieri
    const remainingTable = document.createElement('table');
    remainingTable.id = 'remainingTable';
    remainingTable.classList.add('table', 'table-sm', 'table-bordered');

    const remainingTableHeader = document.createElement('thead');
    remainingTableHeader.innerHTML = `
        <tr>
            <th>Giorno</th>
            <th class="calorie-edit">Calorie</th>
            <th class="carboidrati-edit">Carboidrati (g)</th>
            <th class="proteine-edit">Proteine (g)</th>
            <th class="grassi-edit">Grassi (g)</th>
        </tr>
    `;
    remainingTable.appendChild(remainingTableHeader);

    const remainingTableBody = document.createElement('tbody');

    let totalKcal = 0,
        totalCarboidrati = 0,
        totalProteine = 0,
        totalGrassi = 0;

    days.forEach(day => {
        const remaining = data['remaining_macronutrienti'][day];

        totalKcal += remaining.kcal;
        totalCarboidrati += remaining.carboidrati;
        totalProteine += remaining.proteine;
        totalGrassi += remaining.grassi;

        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${capitalize(day)}</td>
            <td class="calorie-edit">${remaining.kcal.toFixed(2)}</td>
            <td class="carboidrati-edit">${remaining.carboidrati.toFixed(2)}</td>
            <td class="proteine-edit">${remaining.proteine.toFixed(2)}</td>
            <td class="grassi-edit">${remaining.grassi.toFixed(2)}</td>
        `;
        remainingTableBody.appendChild(row);
    });

    // Aggiungi i totali settimanali come ultima riga della tabella
    const totalRow = document.createElement('tr');
    totalRow.innerHTML = `
        <th>Totale</th>
        <th class="calorie-edit">${totalKcal.toFixed(2)}</th>
        <th class="carboidrati-edit">${totalCarboidrati.toFixed(2)}</th>
        <th class="proteine-edit">${totalProteine.toFixed(2)}</th>
        <th class="grassi-edit">${totalGrassi.toFixed(2)}</th>
    `;
    remainingTableBody.appendChild(totalRow);

    remainingTable.appendChild(remainingTableBody);
    macrosContainer.appendChild(remainingTable);

    // Aggiungi la tabella sotto al week selector
    const menuContainer = document.getElementById('menuEditor');
    menuContainer.parentNode.insertBefore(macrosContainer, menuContainer);

    // Creazione delle card per ogni giorno
    days.forEach(day => {
        const dayContainer = document.createElement('div');
        dayContainer.classList.add('day-container', 'mb-4');
        dayContainer.setAttribute('data-day', day); // Aggiungi l'attributo data-day per il filtraggio

        const card = document.createElement('div');
        card.classList.add('card');

        const cardBody = document.createElement('div');
        cardBody.classList.add('card-body');

        const dayTitle = document.createElement('h5');
        dayTitle.classList.add('card-title');
        dayTitle.textContent = `${capitalize(day)}`;

        cardBody.appendChild(dayTitle);

        meals.forEach(meal => {
            const mealContainer = document.createElement('div');
            mealContainer.classList.add('meal-container');
            const mealTitle = document.createElement('h6');
            mealTitle.classList.add('card-subtitle', 'mb-2', 'text-muted');
            mealTitle.textContent = formatMealName(meal);
            mealContainer.appendChild(mealTitle);

            if (menu.day[day].pasto[meal].ricette.length > 0) {
                menu.day[day].pasto[meal].ricette.forEach(ricetta => {
                    const ricettaDiv = document.createElement('div');
                    const dynamicId = `meal-${ricetta.id}-${day}-${meal}`;
                    ricettaDiv.id = dynamicId;
                    ricettaDiv.classList.add('ricetta', 'mb-2');

                    ricettaDiv.innerHTML = `
                        <input hidden type="text" class="form-control form-control-sm" value="${ricetta.id}">
                        <input type="text" class="form-control form-control-sm" value="${ricetta.nome_ricetta}" readonly>
                        <input type="text" class="form-control form-control-sm" style="width: 10%" value="KCAL: ${ricetta.kcal}" readonly>
                        <input type="text" class="form-control form-control-sm" style="width: 10%" value="CARB: ${ricetta.carboidrati}" readonly>
                        <input type="text" class="form-control form-control-sm" style="width: 10%" value="PROT: ${ricetta.proteine}" readonly>
                        <input type="text" class="form-control form-control-sm" style="width: 10%" value="GRAS: ${ricetta.grassi}" readonly>
                        <input type="number" class="form-control form-control-sm" style="width: 10%" value="${ricetta.qta}" min="0.1" step="0.1" onchange="updateMealQuantity('${day}', '${meal}', '${ricetta.id}', this.value)">
                        <button class="btn btn-danger btn-sm mt-2" onclick="removeMeal('${day}', '${meal}', '${ricetta.id}')">Rimuovi</button>
                    `;
                    mealContainer.appendChild(ricettaDiv);
                });
            }

            const addMealBtn = document.createElement('button');
            addMealBtn.textContent = "Aggiungi Ricetta";
            addMealBtn.classList.add('btn', 'btn-success', 'btn-sm', 'mt-2');
            addMealBtn.onclick = function() {
                addNewMeal(day, meal);
            };
            mealContainer.appendChild(addMealBtn);

            cardBody.appendChild(mealContainer);
        });

        card.appendChild(cardBody);
        dayContainer.appendChild(card);
        menuEditor.appendChild(dayContainer);
    });

    // Ripristina lo stato delle selezioni
    document.getElementById('settimana_select').value = selectedWeek;
    if (selectedDay) {
        document.getElementById('day_select').value = selectedDay;
    }
}

function updateMealQuantity(day, meal, ricettaId, newQuantity) {
    const data = {
        day: day,
        meal: meal,
        meal_id: ricettaId,
        quantity: newQuantity,
        week_id: selectedWeekId
    };

    fetch(`/update_meal_quantity`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            renderMenuEditor(data);
            //aggiornaMacronutrientiRimanenti(data.remaining_macronutrienti);
        })
        .catch(error => console.error('Error:', error));
}

function removeMeal(day, meal, mealId) {
    fetch(`/remove_meal/${selectedWeekId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                day: day,
                meal: meal,
                meal_id: mealId
            })
        })
        .then(response => response.json())
        .then(data => {
            // Rimuovi il pasto dalla visualizzazione
            document.getElementById(`meal-${mealId}-${day}-${meal}`).remove();
            renderMenuEditor(data);
            // Aggiorna i macronutrienti rimanenti nella visualizzazione
            //aggiornaMacronutrientiRimanenti(data.remaining_macronutrienti);
        })
        .catch(error => console.error('Error:', error));
}


function addNewMeal(day, meal) {
    currentDay = day;
    currentMeal = meal;

    // Fetch delle ricette disponibili per quel pasto
    fetch(`/get_available_meals?meal=${meal}&day=${day}&week_id=${selectedWeekId}`)
        .then(response => response.json())
        .then(data => {
            const mealSelectionBody = document.getElementById('mealSelectionBody');
            mealSelectionBody.innerHTML = ''; // Pulisce la tabella

            data.forEach(ricetta => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${ricetta.nome_ricetta}</td>
                    <td>${ricetta.kcal}</td>
                    <td>${ricetta.carboidrati}</td>
                    <td>${ricetta.proteine}</td>
                    <td>${ricetta.grassi}</td>
                    <td><input type="checkbox" value="${ricetta.id}" class="meal-checkbox"></td>
                `;
                mealSelectionBody.appendChild(row);
            });

            // Mostra il modal
            const addMealModal = new bootstrap.Modal(document.getElementById('addMealModal'));
            addMealModal.show();
        });
}


function addMealsToMenu(day, meal, selectedMeals) {
    fetch(`/add_meals_to_menu/${selectedWeekId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                day: day,
                meal: meal,
                selectedMeals: selectedMeals
            }),
        })
        .then(response => response.json())
        .then(data => {
            renderMenuEditor(data);
        })
        .catch((error) => {
            console.error('Error:', error);
        });
}

function aggiornaMacronutrientiRimanenti(remaining_macronutrienti) {
    const days = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato', 'domenica'];
    const macroNutrients = ['kcal', 'carboidrati', 'proteine', 'grassi'];

    days.forEach(giorno => {
        macroNutrients.forEach(macro => {
            const remainingValue = remaining_macronutrienti[giorno][macro];
            document.getElementById(`remaining-${macro}-${giorno}`).textContent = remainingValue.toFixed(2);
        });
    });
}


function submitWeight() {
    const weight = document.getElementById('weightInput').value;
    const date = new Date().toISOString().slice(0, 10); // Prende la data odierna

    // Invia il peso al server (assumendo che tu abbia un endpoint API)
    fetch('/submit-weight', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                date: date,
                weight: weight
            })
        })
        .then(response => response.json())
        .then(data => {
            updateWeightChart(data); // Aggiorna il grafico dopo l'invio
        })
        .catch(error => console.error('Errore nel salvataggio del peso:', error));
}

function formatDate(dateStr) {
    var date = new Date(dateStr);
    return date.getFullYear() + '-' +
        ('0' + (date.getMonth() + 1)).slice(-2) + '-' +
        ('0' + date.getDate()).slice(-2);
}

function updateWeightChart(weights) {
    const ctx = document.getElementById('weightChartCanvas').getContext('2d');
    // Distruggi il grafico esistente se esiste
    if (myChart) {
        myChart.destroy();
    }

    myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: weights.map(item => formatDate(item.date)),
            datasets: [{
                label: 'Peso',
                data: weights.map(item => item.weight),
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                borderColor: 'rgba(255, 99, 132, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

function startMenuGeneration() {
    // Effettua una richiesta AJAX per avviare la generazione del menu
    fetch('/generate_menu', {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateProgress(100); // Imposta il progresso al 100%
                setTimeout(() => {
                    $('#generateMenuModal').modal('hide'); // Chiudi il modal
                    location.reload(); // Ricarica la pagina per visualizzare il nuovo menu
                }, 1000);
            }
        })
        .catch(error => {
            console.error('Errore durante la generazione del menu:', error);
        });
}

function updateProgress(progress) {
    const progressBar = document.getElementById("menuGenerationProgress");
    progressBar.style.width = `${progress}%`;
    progressBar.setAttribute("aria-valuenow", progress);
}

function cleanFilters() {
    // Resetta i valori dei filtri
    document.getElementById('filter-nome').value = '';
    document.getElementById('filter-calorie-min').value = '';
    document.getElementById('filter-calorie-max').value = '';
    document.getElementById('filter-carbo-min').value = '';
    document.getElementById('filter-carbo-max').value = '';
    document.getElementById('filter-proteine-min').value = '';
    document.getElementById('filter-proteine-max').value = '';
    document.getElementById('filter-grassi-min').value = '';
    document.getElementById('filter-grassi-max').value = '';
    document.getElementById('filter-colazione').value = 'all';
    document.getElementById('filter-colazione-sec').value = 'all';
    document.getElementById('filter-spuntino').value = 'all';
    document.getElementById('filter-principale').value = 'all';
    document.getElementById('filter-contorno').value = 'all';
    document.getElementById('filter-attiva').value = 'all';

    // Chiama la funzione che filtra la tabella per aggiornare i risultati
    filterTable();
}

function cleanFiltersAlimenti() {
    // Resetta i valori dei filtri
    document.getElementById('filter-nome-alimento').value = '';
    document.getElementById('filter-calorie-min').value = '';
    document.getElementById('filter-calorie-max').value = '';
    document.getElementById('filter-carbo-min').value = '';
    document.getElementById('filter-carbo-max').value = '';
    document.getElementById('filter-proteine-min').value = '';
    document.getElementById('filter-proteine-max').value = '';
    document.getElementById('filter-grassi-min').value = '';
    document.getElementById('filter-grassi-max').value = '';
    document.getElementById('filter-macro').value = 'all';
    document.getElementById('filter-frutta').value = 'all';
    document.getElementById('filter-carne-bianca').value = 'all';
    document.getElementById('filter-carne-rossa').value = 'all';
    document.getElementById('filter-pane').value = 'all';
    document.getElementById('filter-verdura').value = 'all';
    document.getElementById('filter-confezionato').value = 'all';
    document.getElementById('filter-vegan').value = 'all';
    document.getElementById('filter-pesce').value = 'all';

    // Chiama la funzione che filtra la tabella per aggiornare i risultati
    filterAlimentiTable();
}


document.addEventListener('DOMContentLoaded', function() {
    document.getElementById("defaultOpen").click();

    document.getElementById("captureButton").addEventListener("click", function() {
        const weekId = document.getElementById("settimana_select").value; // Ottieni l'ID della settimana selezionata
        const menuContainer = document.querySelector("#capture");

        html2canvas(document.querySelector("#capture")).then(canvas => {
            const imgData = canvas.toDataURL('image/png');
            // Ora puoi usare imgData per creare un PDF o visualizzare l'immagine
            fetch('/generate_pdf', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        image: imgData,
                        week_id: weekId
                    })
                })
                .then(response => response.blob())
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'menu_settimanale.pdf';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                })
                .catch(error => console.error('Error:', error));
        });
    });

    document.getElementById("generateMenuBtn").addEventListener("click", function() {
        // Avvia la generazione del menu al click del bottone
        startMenuGeneration();
    });

    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    document.getElementById('confirmAddMeal').addEventListener('click', function() {
        const selectedMeals = [];
        document.querySelectorAll('.meal-checkbox:checked').forEach(checkbox => {
            selectedMeals.push(checkbox.value);
        });

        if (selectedMeals.length > 0) {
            // Aggiungi le ricette selezionate al menu
            addMealsToMenu(currentDay, currentMeal, selectedMeals);
        }

        // Chiudi il modal
        const addMealModal = bootstrap.Modal.getInstance(document.getElementById('addMealModal'));
        addMealModal.hide();
    });

    document.querySelectorAll('.save-btn').forEach(button => {
        button.addEventListener('click', function() {
            const ricettaId = this.getAttribute('data-ricetta-id');
            const ricettaData = {
                id: ricettaId,
                nome: document.querySelector(`input[name='nome_${ricettaId}']`).value,
                colazione: document.querySelector(`input[name='colazione_${ricettaId}']`).checked,
                colazione_sec: document.querySelector(`input[name='colazione_sec_${ricettaId}']`).checked,
                spuntino: document.querySelector(`input[name='spuntino_${ricettaId}']`).checked,
                principale: document.querySelector(`input[name='principale_${ricettaId}']`).checked,
                contorno: document.querySelector(`input[name='contorno_${ricettaId}']`).checked
            };
            saveRicetta(ricettaData);
        });
    });

    document.querySelectorAll('.toggle-btn').forEach(button => {
        button.addEventListener('click', function() {
            const ricettaId = this.getAttribute('data-ricetta-id');
            const ricettaAttiva = this.getAttribute('data-ricetta-attiva') === 'true';
            const ricettaData = {
                id: ricettaId,
                attiva: !ricettaAttiva
            };
            toggleStatusRicetta(ricettaData);
            const checkbox = document.querySelector(`.attiva-checkbox[data-ricetta-id='${ricettaId}']`);
            if (checkbox) {
                checkbox.checked = !checkbox.checked;
            }
        });
    });

    document.querySelectorAll('.edit-btn').forEach(button => {
        button.addEventListener('click', function() {
            const recipeId = this.getAttribute('data-ricetta-id');
            fetch(`/recipe/${recipeId}`)
                .then(response => response.json())
                .then(data => {
                    populateIngredientsModal(data);
                    document.getElementById('modal-recipe-id').value = recipeId;
                })
                .catch(error => console.error('Error loading the ingredients:', error));
        });
    });

    // Assicurati che gli event listeners siano aggiunti dopo il caricamento dei dati nel modal
    document.querySelector('#editRecipeModal').addEventListener('click', function(event) {
        const target = event.target;
        if (target.classList.contains('delete-ingredient')) {
            const ingredientId = target.getAttribute('data-id');
            const recipeId = target.getAttribute('data-recipe-id');
            deleteIngredient(ingredientId, recipeId, target);
        }

        if (target.classList.contains('update-ingredient')) {
            const ingredientId = target.getAttribute('data-id');
            const recipeId = target.getAttribute('data-recipe-id');
            const qta = document.getElementById(`quantity-${ingredientId}`).value
            updateIngredient(ingredientId, recipeId, qta);
        }
    });

    var addIngredientModal = document.getElementById('addIngredientModal');
    addIngredientModal.addEventListener('hidden.bs.modal', function() {
        window.location.href = '/';
    })

    synchronizeFields();
    document.getElementById('personalInfoForm').addEventListener('submit', synchronizeFields);

    const form = document.getElementById('personalInfoForm');
    const resultsContainer = document.getElementById('results');
    //const calculatedResults = document.getElementById('calculatedResults');

    const bmiInput = document.getElementById('bmi');
    const idealWeightInput = document.getElementById('peso_ideale');
    const metaBasale = document.getElementById('meta_basale');
    const metaDaily = document.getElementById('meta_giornaliero');
    const calorieGiornaliere = document.getElementById('calorie_giornaliere');
    const calorieSettimanali = document.getElementById('calorie_settimanali');
    const carboidrati = document.getElementById('carboidrati_input');
    const proteine = document.getElementById('proteine_input');
    const grassi = document.getElementById('grassi_input');

    form.addEventListener('input', calculateResults);

    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    document.getElementById("peso-tab").addEventListener("click", () => {
        fetch('/get_peso_data')
            .then(response => response.json())
            .then(data => {
                if (data.length > 0) {
                    updateWeightChart(data);
                }
            })
            .catch(error => console.error('Errore nel caricamento dei dati:', error));
    });

    document.getElementById("dieta-tab").addEventListener("click", () => {
        fetch('/get_data_utente')
            .then(response => response.json())
            .then(data => {
                if (data) {
                    populateDietaForm(data);
                }
            })
            .catch(error => console.error('Errore nel caricamento dei dati:', error));
    });

    // Event listener per il salvataggio degli alimenti
    document.querySelectorAll('.save-alimento-btn').forEach(button => {
        button.addEventListener('click', function() {
            const alimentoId = this.getAttribute('data-alimento-id');
            const alimentoData = {
                id: alimentoId,
                nome: document.querySelector(`input[name='nome_${alimentoId}']`).value,
                carboidrati: parseFloat(document.querySelector(`input[name='carboidrati_${alimentoId}']`).value),
                proteine: parseFloat(document.querySelector(`input[name='proteine_${alimentoId}']`).value),
                grassi: parseFloat(document.querySelector(`input[name='grassi_${alimentoId}']`).value),
                frutta: document.querySelector(`input[name='frutta_${alimentoId}']`).checked,
                carne_bianca: document.querySelector(`input[name='carne_bianca_${alimentoId}']`).checked,
                carne_rossa: document.querySelector(`input[name='carne_rossa_${alimentoId}']`).checked,
                pane: document.querySelector(`input[name='pane_${alimentoId}']`).checked,
                verdura: document.querySelector(`input[name='verdura_${alimentoId}']`).checked,
                confezionato: document.querySelector(`input[name='confezionato_${alimentoId}']`).checked,
                vegan: document.querySelector(`input[name='vegan_${alimentoId}']`).checked,
                pesce: document.querySelector(`input[name='pesce_${alimentoId}']`).checked
            };
            saveAlimento(alimentoData);
        });
    });

    // Event listener per l'eliminazione degli alimenti
    document.querySelectorAll('.delete-alimento-btn').forEach(button => {
        button.addEventListener('click', function() {
            const alimentoId = this.getAttribute('data-alimento-id');
            deleteAlimento(alimentoId);
        });
    });

    $(document).ready(function() {
        $('#addIngredientModal').on('show.bs.modal', function(event) {
            const select = document.getElementById('ingredient-select');
            select.innerHTML = '';

            fetch('/get_all_ingredients')
                .then(response => response.json())
                .then(ingredients => {
                    ingredients.forEach(ingredient => {
                        const option = new Option(ingredient.nome, ingredient.id);
                        select.add(option);
                    });
                })
                .catch(error => console.error('Error loading ingredients:', error));
        });
    });
});