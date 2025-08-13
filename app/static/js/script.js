// app/js/script.js
let currentDay = '';
let currentMeal = '';
let selectedWeekId = null;
let gruppi = []; // Variabile globale per memorizzare i gruppi
var myChart;

// in alto
function debounce(fn, wait=200) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), wait);
  };
}

function openTab(evt, tabName) {
    const tabcontent = document.querySelectorAll(".tabcontent");
    tabcontent.forEach(tab => tab.style.display = "none");
    const tablinks = document.querySelectorAll(".tablinks");
    tablinks.forEach(link => link.className = link.className.replace(" active", ""));
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}

function showAlertModal(message) {
    // Imposta il messaggio nel modal
    document.getElementById('modalMessage').textContent = message;

    // Mostra il modal usando Bootstrap
    var myModal = new bootstrap.Modal(document.getElementById('genericModal'));
    myModal.show();
}


function populateWeekDropdowns() {
    fetch('/get_weeks')
        .then(response => response.json())
        .then(data => {
            if (data.status == 'success'){
                const weekFromSelect = document.getElementById('weekFrom');
                const weekToSelect = document.getElementById('weekTo');

                // Svuota le dropdown prima di popolare
                weekFromSelect.innerHTML = '';
                weekToSelect.innerHTML = '';

                data.weeks.forEach(week => {
                    const optionFrom = document.createElement('option');
                    optionFrom.value = week.id;
                    optionFrom.textContent = week.name;
                    weekFromSelect.appendChild(optionFrom);

                    const optionTo = document.createElement('option');
                    optionTo.value = week.id;
                    optionTo.textContent = week.name;
                    weekToSelect.appendChild(optionTo);
                });
            }
        })
        .catch(error => console.error('Errore nel caricamento delle settimane:', error));
}

function copyWeek() {
    const weekFrom = document.getElementById('weekFrom').value;
    const weekTo = document.getElementById('weekTo').value;

    if (weekFrom === weekTo) {
        showAlertModal("Seleziona due settimane diverse per la copia.");
        return;
    }

    fetch('/copy_week', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            week_from: weekFrom,
            week_to: weekTo
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showAlertModal('Copia completata con successo.');
            // Ricarica il menu della settimana selezionata
            loadAndUpdateMenuData();
        } else {
            console.error('Errore:', data.message);
            showAlertModal('Errore nella copia della settimana. Riprova.');
        }
    })
    .catch(error => console.error('Errore:', error));
}

function sortTable(tableId, columnIndex) {
    const table = document.getElementById(tableId);
    const rows = Array.from(table.querySelector('tbody').rows);
    let ascending = table.dataset.sortOrder === 'asc';

    rows.sort((a, b) => {
        const aText = a.cells[columnIndex].textContent.trim();
        const bText = b.cells[columnIndex].textContent.trim();

        // Controlla se i valori possono essere interpretati come numeri
        const aValue = isNaN(aText) ? aText.toLowerCase() : parseFloat(aText);
        const bValue = isNaN(bText) ? bText.toLowerCase() : parseFloat(bText);

        if (aValue < bValue) {
            return ascending ? -1 : 1;
        }
        if (aValue > bValue) {
            return ascending ? 1 : -1;
        }
        return 0;
    });

    // Aggiorna l'ordine delle righe nel tbody
    rows.forEach(row => table.querySelector('tbody').appendChild(row));

    // Alterna l'ordine di ordinamento per la prossima volta
    table.dataset.sortOrder = ascending ? 'desc' : 'asc';
}


function invertDays() {
    const day1 = document.getElementById('day1').value;
    const day2 = document.getElementById('day2').value;
    const weekId = selectedWeekId;

    // Controlla che i giorni non siano uguali
    if (day1 === day2) {
        showAlertModal("Seleziona due giorni diversi per l'inversione.");
        return;
    }

    fetch(`/inverti_pasti_giorni/${weekId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            day1: day1,
            day2: day2
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            renderMenuEditor(data);
        } else {
            console.error('Error:', data.message);
            showAlertModal('Errore nell\'inversione dei pasti. Riprova.');
        }
    })
    .catch(error => console.error('Error:', error));
}


function invertMeals(day) {
    // Invia la richiesta al backend per salvare l'inversione
    fetch(`/inverti_pasti/${selectedWeekId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ day: day })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            renderMenuEditor(data);
        }
    })
    .catch(error => {
        console.error('Errore di rete:', error);
        showAlertModal(error)
    });
}

function cancellaMealDaily(day, meal_type) {
    fetch(`/cancella_pasto/${selectedWeekId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ day: day, meal_type: meal_type })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            renderMenuEditor(data);
        }
    })
    .catch(error => {
        console.error('Errore di rete:', error);
        showAlertModal(error)
    });
}


function aggiornaTabellaMenu(menu) {
    const tbody = document.getElementById('menu_tbody');
    tbody.innerHTML = ''; // Pulisci la tabella

    const days = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato', 'domenica'];
    const macroNutrients = ['kcal', 'carboidrati', 'proteine', 'grassi', 'sale'];

    // Itera su ogni pasto e giorno
    ['colazione', 'spuntino_mattina', 'pranzo', 'spuntino_pomeriggio', 'cena', 'spuntino_sera'].forEach(pasto => {
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
                    div.textContent = `${ricetta.nome_ricetta} (${ricetta.qta}x) ${ricetta.info}`;

                    // Aggiungi gli attributi per il popover
                    div.setAttribute('data-bs-toggle', 'tooltip');
                    div.setAttribute(
                        'data-bs-html', 'true' // Indica che il tooltip utilizza HTML
                    );
                    div.setAttribute(
                        'data-bs-title',
                        ricetta.ricetta && ricetta.ricetta.length > 0
                            ? ricetta.ricetta.map(item => `${item.nome} ${item.qta}g.`).join('<br>')
                            : 'vuoto'
                    );

                    // Aggiungi la classe "recipe-cell"
                    div.classList.add('recipe-cell');

                    // Aggiungi il div all'elemento td (o un altro elemento genitore)
                    td.appendChild(div);

                    // Inizializza il popover sul nuovo elemento
                    new bootstrap.Tooltip(div);
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

    aggiornaTabellaListaDellaSpesa();
}

function aggiornaTabellaListaDellaSpesa() {
    var weekId = selectedWeekId; // Ottieni l'ID della settimana selezionata

    if (!selectedWeekId) {
        weekId = document.querySelector('.week-select').value;
    }

    const tbody = document.getElementById('spesa_tbody');
    tbody.innerHTML = ''; // Pulisci la tabella

    // Esegui una chiamata fetch per ottenere la lista della spesa basata sugli ID degli alimenti
    fetch(`/get_lista_spesa/${weekId}`)
        .then(response => response.json())
        .then(data => {
            data.lista_spesa.forEach(item => {
                const tr = document.createElement('tr');
                const tdAlimento = document.createElement('td');
                const tdQuantita = document.createElement('td');
                tdAlimento.textContent = item.alimento;
                tdQuantita.textContent = item.qta_totale;
                tdQuantita.style.textAlign = 'right';
                tr.appendChild(tdAlimento);
                tr.appendChild(tdQuantita);
                tbody.appendChild(tr);
            });
        })
        .catch(error => console.error('Errore nel recupero della lista della spesa:', error));
}

function updateRicetta(ricettaData) {
    fetch(`/ricette/${ricettaData.id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(ricettaData)
        })
        .then(response => response.json())
        .then(data => {
            recupera_tutte_le_ricette();
        })
        .catch((error) => {
            console.error('Error:', error);
        });
}

function toggleStatusRicetta(ricettaId) {
    fetch(`/ricette/${ricettaId}/stato`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            recupera_tutte_le_ricette();
        })
        .catch((error) => {
            console.error('Error:', error);
        });
}

function deleteRicetta(ricettaId) {
        fetch(`/ricette/${ricettaId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            recupera_tutte_le_ricette();
        })
        .catch((error) => {
            console.error('Error:', error);
        });
}

function filterTable() {
    const nomeFilter = document.getElementById('filter-nome').value.toLowerCase();

    const calorieMin = parseFloat(document.getElementById('filter-ricette-calorie-min').value) || -Infinity;
    const calorieMax = parseFloat(document.getElementById('filter-ricette-calorie-max').value) || Infinity;
    const carboMin = parseFloat(document.getElementById('filter-ricette-carbo-min').value) || -Infinity;
    const carboMax = parseFloat(document.getElementById('filter-ricette-carbo-max').value) || Infinity;
    const proteineMin = parseFloat(document.getElementById('filter-ricette-proteine-min').value) || -Infinity;
    const proteineMax = parseFloat(document.getElementById('filter-ricette-proteine-max').value) || Infinity;
    const grassiMin = parseFloat(document.getElementById('filter-ricette-grassi-min').value) || -Infinity;
    const grassiMax = parseFloat(document.getElementById('filter-ricette-grassi-max').value) || Infinity;
    const fibreMin = parseFloat(document.getElementById('filter-ricette-fibre-min').value) || -Infinity;
    const fibreMax = parseFloat(document.getElementById('filter-ricette-fibre-max').value) || Infinity;

    const zuccheroMin = parseFloat(document.getElementById('filter-ricette-zucchero-min').value) || -Infinity;
    const zuccheroMax = parseFloat(document.getElementById('filter-ricette-zucchero-max').value) || Infinity;
    const saleMin = parseFloat(document.getElementById('filter-ricette-sale-min').value) || -Infinity;
    const saleMax = parseFloat(document.getElementById('filter-ricette-sale-max').value) || Infinity;

    const colazioneFilter = document.getElementById('filter-colazione').value;
    const colazioneSecFilter = document.getElementById('filter-colazione-sec').value;
    const spuntinoFilter = document.getElementById('filter-spuntino').value;
    const principaleFilter = document.getElementById('filter-principale').value;
    const contornoFilter = document.getElementById('filter-contorno').value;
    const complementoFilter = document.getElementById('filter-complemento-ricette').value;
    const attivaFilter = document.getElementById('filter-attiva').value;

    const infoFilterOptions = Array.from(document.getElementById('filter-info').selectedOptions).map(option => option.value);

    const table = document.getElementById('ricette-table').querySelector('tbody');
    const rows = table.getElementsByTagName('tr');

    // Se "Tutti" è selezionato, ignora i filtri "Info"
    const infoFilterActive = !infoFilterOptions.includes("all");

    for (let i = 0; i < rows.length; i++) {
        const cells = rows[i].getElementsByTagName('td');
        const nomeCell = cells[0].textContent.toLowerCase();

        const calorieCell = parseFloat(cells[1].textContent) || 0;
        const carboCell = parseFloat(cells[2].textContent) || 0;
        const proteineCell = parseFloat(cells[3].textContent) || 0;
        const grassiCell = parseFloat(cells[4].textContent) || 0;
        const fibreCell = parseFloat(cells[5].textContent) || 0;
        const zuccheroCell = parseFloat(cells[6].textContent) || 0;
        const saleCell = parseFloat(cells[7].textContent) || 0;
        const colazioneCell = cells[8].querySelector('input').checked.toString();
        const colazioneSecCell = cells[9].querySelector('input').checked.toString();
        const spuntinoCell = cells[10].querySelector('input').checked.toString();
        const principaleCell = cells[11].querySelector('input').checked.toString();
        const contornoCell = cells[12].querySelector('input').checked.toString();
        const complementoCell = cells[13].querySelector('input').checked.toString();
        const attivaCell = cells[14].querySelector('input').checked.toString();
        const infoCell = cells[15].textContent; // Colonna "Info"

        const colazioneMatch = (colazioneFilter === 'all') || (colazioneFilter === colazioneCell);
        const colazioneSecMatch = (colazioneSecFilter === 'all') || (colazioneSecFilter === colazioneSecCell);
        const spuntinoMatch = (spuntinoFilter === 'all') || (spuntinoFilter === spuntinoCell);
        const principaleMatch = (principaleFilter === 'all') || (principaleFilter === principaleCell);
        const contornoMatch = (contornoFilter === 'all') || (contornoFilter === contornoCell);
        const complementoMatch = (complementoFilter === 'all') || (complementoFilter === complementoCell);
        const attivaMatch = (attivaFilter === 'all') || (attivaFilter === attivaCell);

        const calorieMatch = calorieCell >= calorieMin && calorieCell <= calorieMax;
        const carboMatch = carboCell >= carboMin && carboCell <= carboMax;
        const proteineMatch = proteineCell >= proteineMin && proteineCell <= proteineMax;
        const grassiMatch = grassiCell >= grassiMin && grassiCell <= grassiMax;
        const fibreMatch = fibreCell >= fibreMin && fibreCell <= fibreMax;
        const zuccheroMatch = zuccheroCell >= zuccheroMin && zuccheroCell <= zuccheroMax;
        const saleMatch = saleCell >= saleMin && saleCell <= saleMax;

        // Se il filtro "Info" è attivo, verifica la corrispondenza
        const infoMatch = !infoFilterActive || infoFilterOptions.some(option => infoCell.includes(option));

        if (nomeCell.includes(nomeFilter) &&
            calorieMatch &&
            carboMatch &&
            proteineMatch &&
            grassiMatch &&
            fibreMatch &&
            zuccheroMatch &&
            saleMatch &&
            colazioneMatch &&
            colazioneSecMatch &&
            spuntinoMatch &&
            principaleMatch &&
            contornoMatch &&
            complementoMatch &&
            attivaMatch &&
            infoMatch) {
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
    const fibreMin = parseFloat(document.getElementById('filter-fibre-min').value) || -Infinity;
    const fibreMax = parseFloat(document.getElementById('filter-fibre-max').value) || Infinity;

    const zuccheroMin = parseFloat(document.getElementById('filter-zucchero-min').value) || -Infinity;
    const zuccheroMax = parseFloat(document.getElementById('filter-zucchero-max').value) || Infinity;
    const saleMin = parseFloat(document.getElementById('filter-sale-min').value) || -Infinity;
    const saleMax = parseFloat(document.getElementById('filter-sale-max').value) || Infinity;

    const veganFilter = document.getElementById('filter-vegan').value;
    const surgelatoFilter = document.getElementById('filter-surgelato').value;
    const gruppoFilter = document.getElementById('filter-gruppo').value;

    // Recupera i mesi selezionati per il filtro stagionalità
    const monthButtons = document.querySelectorAll('.month-filter-btn');
    const includeMonths = [];
    const excludeMonths = [];
    monthButtons.forEach(button => {
        const month = parseInt(button.getAttribute('data-month'));
        if (button.classList.contains('btn-primary')) {
            includeMonths.push(month);
        } else if (button.classList.contains('btn-danger')) {
            excludeMonths.push(month);
        }
    });

    const table = document.getElementById('alimenti-table').querySelector('tbody');
    const rows = table.getElementsByTagName('tr');

    for (let i = 0; i < rows.length; i++) {
        const cells = rows[i].getElementsByTagName('td');
        const nomeCell = cells[0].textContent.toLowerCase();

        const calorieCell = parseFloat(cells[1].textContent) || 0;
        const carboCell = parseFloat(cells[2].textContent) || 0;
        const proteineCell = parseFloat(cells[3].textContent) || 0;
        const grassiCell = parseFloat(cells[4].textContent) || 0;
        const fibreCell = parseFloat(cells[5].textContent) || 0;
        const zuccheroCell = parseFloat(cells[6].textContent) || 0;
        const saleCell = parseFloat(cells[7].textContent) || 0;
        const gruppoCell = cells[8].querySelector('select').value;
        const veganCell = cells[9].querySelector('input').checked.toString();
        const surgelatoCell = cells[10].querySelector('input').checked.toString();

        // Ottieni i mesi di stagionalità dell'alimento
        const stagionalitaCell = Array.from(
            cells[9].querySelectorAll('.btn-primary')
        ).map(button => parseInt(button.getAttribute('data-month')));

        const calorieMatch = calorieCell >= calorieMin && calorieCell <= calorieMax;
        const carboMatch = carboCell >= carboMin && carboCell <= carboMax;
        const proteineMatch = proteineCell >= proteineMin && proteineCell <= proteineMax;
        const grassiMatch = grassiCell >= grassiMin && grassiCell <= grassiMax;
        const fibreMatch = fibreCell >= fibreMin && fibreCell <= fibreMax;
        const zuccheroMatch = zuccheroCell >= zuccheroMin && zuccheroCell <= zuccheroMax;
        const saleMatch = saleCell >= saleMin && saleCell <= saleMax;

        const veganMatch = (veganFilter === 'all') || (veganFilter === veganCell);
        const surgelatoMatch = (surgelatoFilter === 'all') || (surgelatoFilter === surgelatoCell);
        const gruppoMatch = (gruppoFilter === 'all') || (gruppoFilter === gruppoCell);

         // Controllo stagionalità
        const includeMatch = includeMonths.every(month => stagionalitaCell.includes(month));
        const excludeMatch = excludeMonths.every(month => !stagionalitaCell.includes(month));


        if (
            nomeCell.includes(nomeFilter) &&
            calorieMatch &&
            carboMatch &&
            proteineMatch &&
            grassiMatch &&
            fibreMatch &&
            zuccheroMatch &&
            saleMatch &&
            veganMatch &&
            surgelatoMatch &&
            gruppoMatch &&
            includeMatch &&
            excludeMatch
        ) {
            rows[i].style.display = '';
        } else {
            rows[i].style.display = 'none';
        }
    }
}

function populateIngredientsModal(ingredients) {
    if (ingredients && ingredients.length > 0 && ingredients[0]['nome_ricetta']) {
        document.getElementById('editIngredientsModalLabel').textContent = 'Ingredienti Ricetta: ' + ingredients[0]['nome_ricetta'];
    } else {
        document.getElementById('editIngredientsModalLabel').textContent = 'Ingredienti Ricetta';
    }

    const tbody = document.getElementById('ingredientsBody');
    tbody.innerHTML = ''; // Clear existing rows
    ingredients.forEach(ingredient => {
        const row = `<tr>
            <td>${ingredient['nome']}</td>
            <td><input type="number" class="form-control form-control-sm input-hidden-border" id="quantity-${ingredient['id']}" value="${ingredient['qta']}"></td>
            <td>
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-primary btn-sm update-ingredient" data-id="${ingredient['id']}" data-recipe-id="${ingredient['id_ricetta']}">Salva</button>
                    <button type="button" class="btn btn-danger btn-sm delete-ingredient" data-id="${ingredient['id']}" data-recipe-id="${ingredient['id_ricetta']}">Elimina</button>
                </div>
            </td>
        </tr>`;
        tbody.innerHTML += row;
    });
}


function deleteIngredient(ingredientId, recipeId, button) {
    fetch('/delete_ingredienti', {
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
                recupera_tutte_le_ricette();
            }
        })
        .catch((error) => {
            console.error('Error:', error);
        });
}

function updateIngredient(ingredientId, recipeId, qta) {
    fetch('/aggiorna_ingredienti_ricetta', {
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
        .then(data => {
            recupera_tutte_le_ricette();
        })
        .catch((error) => {
            console.error('Error:', error);
        });
}


function addIngredientToRecipe() {
    const ingredientId = document.getElementById('ingredient-select').value;
    const quantity = document.getElementById('ingredient-quantity').value;
    const recipeId = document.getElementById('modal-recipe-id').value;

    fetch('/aggiorna_ingredienti_ricetta', {
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
        .then(data => {
            recupera_tutte_le_ricette()
        })
        .catch((error) => {
            console.error('Error:', error);
        });
}

function populateRicetteTable(ricette) {
    const tbody = document.getElementById('ricette-tbody');
    tbody.innerHTML = ''; // Svuota il contenuto attuale della tabella

    ricette.forEach(ricetta => {
        const row = document.createElement('tr');

        // Determina le emoji per le caratteristiche della ricetta
        let infoEmoji = '';
        if (ricetta.is_vegan) infoEmoji += '🌱'; // Emoji per ricetta vegana
        if (ricetta.is_carne_rossa) infoEmoji += '🥩'; // Emoji per ricetta di carne rossa
        if (ricetta.contains_fish) infoEmoji += '🐟'; // Emoji per ricetta con pesce
        if (ricetta.is_frutta) infoEmoji += '🍎';
        if (ricetta.is_verdura) infoEmoji += '🥕';
        if (ricetta.is_carne_bianca) infoEmoji += '🍗';
        if (ricetta.contains_uova) infoEmoji += '🥚';
        if (ricetta.contains_legumi) infoEmoji += '🫘';
        if (ricetta.contains_cereali) infoEmoji += '🌾';
        if (ricetta.contains_pane) infoEmoji += '🍞';
        if (ricetta.contains_latticini) infoEmoji += '🧀';
        if (ricetta.contains_frutta_secca) infoEmoji += '🥜';
        if (ricetta.contains_patate) infoEmoji += '🥔';
        if (ricetta.contains_grassi) infoEmoji += '🧈';

        row.innerHTML = `
            <td>
                <div>
                    <input type="text" class="form-control form-control-sm input-hidden-border" data-ricetta-id="${ricetta.id}" name="nome_ricetta_${ricetta.id}" value="${ricetta.nome_ricetta}">
                    <label hidden class="form-control form-control-sm">${ricetta.nome_ricetta}</label>
                </div>
            </td>
            <td style="text-align: center;">
                 <div>
                    <input type="number" class="form-control form-control-sm input-hidden-border"  min="0.1" step="0.1" data-ricetta-id="${ricetta.id}" name="kcal_{ricetta.id}" value="${ricetta.kcal}">
                    <label hidden class="form-control form-control-sm">${ricetta.kcal}</label>
                </div>
            </td>

            <td style="text-align: center;">
                <div>
                    <input type="number" class="form-control form-control-sm input-hidden-border"  min="0.1" step="0.1" data-ricetta-id="${ricetta.id}" name="carboidrati_{ricetta.id}" value="${ricetta.carboidrati}">
                    <label hidden class="form-control form-control-sm">${ricetta.carboidrati}</label>
                </div>
            </td>
            <td style="text-align: center;">
                <div>
                    <input type="number" class="form-control form-control-sm input-hidden-border"  min="0.1" step="0.1" data-ricetta-id="${ricetta.id}" name="proteine_{ricetta.id}" value="${ricetta.proteine}">
                    <label hidden class="form-control form-control-sm">${ricetta.proteine}</label>
                </div>
            </td>
            <td style="text-align: center;">
                <div>
                    <input type="number" class="form-control form-control-sm input-hidden-border"  min="0.1" step="0.1" data-ricetta-id="${ricetta.id}" name="grassi_{ricetta.id}" value="${ricetta.grassi}">
                    <label hidden class="form-control form-control-sm">${ricetta.grassi}</label>
                </div>
            </td>
            <td style="text-align: center;">
                <div>
                    <input type="number" class="form-control form-control-sm input-hidden-border"  min="0.1" step="0.1" data-ricetta-id="${ricetta.id}" name="fibre_{ricetta.id}" value="${ricetta.fibre}">
                    <label hidden class="form-control form-control-sm">${ricetta.fibre}</label>
                </div>
            </td>
            <td style="text-align: center;">
                <div>
                    <input type="number" class="form-control form-control-sm input-hidden-border"  min="0.1" step="0.1" data-ricetta-id="${ricetta.id}" name="zucchero_{ricetta.id}" value="${ricetta.zucchero}">
                    <label hidden class="form-control form-control-sm">${ricetta.zucchero}</label>
                </div>
            </td>
            <td style="text-align: center;">
                <div>
                    <input type="number" class="form-control form-control-sm input-hidden-border"  min="0.1" step="0.1" data-ricetta-id="${ricetta.id}" name="sale_{ricetta.id}" value="${ricetta.sale}">
                    <label hidden class="form-control form-control-sm">${ricetta.sale}</label>
                </div>
            </td>

            <td style="text-align: center;">
                <div>
                    <input type="checkbox" name="colazione_${ricetta.id}" ${ricetta.colazione ? 'checked' : ''}>
                    <label hidden class="form-control form-control-sm">${ricetta.colazione}</label>
                </div>
            </td>
            <td style="text-align: center;">
                <div>
                    <input type="checkbox" name="colazione_sec_${ricetta.id}" ${ricetta.colazione_sec ? 'checked' : ''}>
                    <label hidden class="form-control form-control-sm">${ricetta.colazione_sec}</label>
                </div>
            </td>
            <td style="text-align: center;">
                <div>
                    <input type="checkbox" name="spuntino_${ricetta.id}" ${ricetta.spuntino ? 'checked' : ''}>
                    <label hidden class="form-control form-control-sm">${ricetta.spuntino}</label>
                </div>
            </td>
            <td style="text-align: center;">
                <div>
                    <input type="checkbox" name="principale_${ricetta.id}" ${ricetta.principale ? 'checked' : ''}>
                    <label hidden class="form-control form-control-sm">${ricetta.principale}</label>
                </div>
            </td>
            <td style="text-align: center;">
                <div>
                    <input type="checkbox" name="contorno_${ricetta.id}" ${ricetta.contorno ? 'checked' : ''}>
                    <label hidden class="form-control form-control-sm">${ricetta.contorno}</label>
                </div>
            </td>
            <td style="text-align: center;">
                <div>
                    <input type="checkbox" name="complemento_${ricetta.id}" ${ricetta.complemento ? 'checked' : ''}>
                    <label hidden class="form-control form-control-sm">${ricetta.complemento}</label>
                </div>
            </td>
            <td style="text-align: center;">
                <div>
                    <label hidden class="form-control form-control-sm">${ricetta.attiva}</label>
                    <input type="checkbox" class="attiva-checkbox" name="attiva_${ricetta.id}" data-ricetta-id="${ricetta.id}" ${ricetta.attiva ? 'checked' : ''} disabled>
                </div>
            </td>
            <td style="text-align: center;">${infoEmoji}</td>
            <td style="text-align: center;">
                <div class="btn-group" role="group">
                    <button class="btn btn-primary btn-sm update-ricetta-btn" data-ricetta-id="${ricetta.id}" data-ricetta-nome="${ricetta.nome_ricetta}" data-ricetta-colazione="${ricetta.colazione}" data-ricetta-colazione_sec="${ricetta.colazione_sec}" data-ricetta-spuntino="${ricetta.spuntino}" data-ricetta-principale="${ricetta.principale}" data-ricetta-contorno="${ricetta.contorno}" data-ricetta-complemento="${ricetta.complemento}" data-ricetta-attiva="${ricetta.attiva}" data-bs-toggle="tooltip" title="Salva"><i class="fas fa-save"></i></button>
                    <button class="btn btn-primary btn-sm edit-btn" data-ricetta-id="${ricetta.id}" data-bs-toggle="modal" data-bs-target="#editRecipeModal" data-bs-toggle="tooltip" title="Modifica"><i class="fas fa-edit"></i></button>
                    <button class="btn btn-warning btn-sm toggle-btn" data-ricetta-id="${ricetta.id}" data-ricetta-attiva="${ricetta.attiva}" data-bs-toggle="tooltip" title="Attiva/Disattiva"><i class="fas fa-toggle-on"></i></button>
                    <button class="btn btn-danger btn-sm delete-btn" data-ricetta-id="${ricetta.id}" data-bs-toggle="tooltip" title="Elimina"><i class="fas fa-trash-alt"></i></button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });

    // Attacca i listener per i bottoni
    document.querySelectorAll('.update-ricetta-btn').forEach(button => {
        button.addEventListener('click', function() {
            const ricettaId = this.getAttribute('data-ricetta-id');
            const ricettaData = {
                id: ricettaId,
                nome: document.querySelector(`input[name='nome_ricetta_${ricettaId}']`).value,
                colazione: document.querySelector(`input[name='colazione_${ricettaId}']`).checked,
                colazione_sec: document.querySelector(`input[name='colazione_sec_${ricettaId}']`).checked,
                spuntino: document.querySelector(`input[name='spuntino_${ricettaId}']`).checked,
                principale: document.querySelector(`input[name='principale_${ricettaId}']`).checked,
                contorno: document.querySelector(`input[name='contorno_${ricettaId}']`).checked,
                complemento: document.querySelector(`input[name='complemento_${ricettaId}']`).checked
            };
            updateRicetta(ricettaData);
        });
    });

    document.querySelectorAll('.toggle-btn').forEach(button => {
        button.addEventListener('click', function() {
            const ricettaId = this.getAttribute('data-ricetta-id');
            const ricettaAttiva = this.getAttribute('data-ricetta-attiva') === 'true';
            toggleStatusRicetta(ricettaId);
            const checkbox = document.querySelector(`.attiva-checkbox[data-ricetta-id='${ricettaId}']`);
            if (checkbox) {
                checkbox.checked = !checkbox.checked;
            }
        });
    });

    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', function() {
            const ricettaId = this.getAttribute('data-ricetta-id');
            deleteRicetta(ricettaId);
        });
    });

    // Riattacca i listener dopo aver aggiornato la tabella
    document.querySelectorAll('.edit-btn').forEach(button => {
        button.addEventListener('click', function() {
            const recipeId = this.getAttribute('data-ricetta-id');
            fetch(`/ingredienti_ricetta/${recipeId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status == 'success'){
                        populateIngredientsModal(data.ricette);
                        document.getElementById('modal-recipe-id').value = recipeId;
                    }
                })
                .catch(error => console.error('Error loading the ingredients:', error));
        });
    });

    filterTable();
}

function populateDietaForm(data) {
    // Popola i campi del form con i dati ricevuti
    document.querySelector('[name="id"]').value = data.id || '';
    document.querySelector('[name="nome"]').value = data.nome || '';
    document.querySelector('[name="cognome"]').value = data.cognome || '';
    document.querySelector('[name="email"]').value = data.email || '';
    document.querySelector('[name="sesso"]').value = data.sesso || '';
    document.querySelector('[name="eta"]').value = Math.round(data.eta) || '';
    document.querySelector('[name="altezza"]').value = Math.round(data.altezza) || '';
    document.querySelector('[name="peso"]').value = parseFloat(data.peso) || '';
    document.getElementById('tdee').value = data.tdee || '';
    document.getElementById('deficit_calorico').value = data.deficit_calorico || '';
    document.getElementById('bmi').value = Math.round(data.bmi * 100) / 100 || '';
    document.getElementById('peso_ideale').value = Math.round(data.peso_ideale) || '';
    document.getElementById('meta_basale').value = Math.round(data.meta_basale) || '';
    document.getElementById('meta_giornaliero').value = Math.round(data.meta_giornaliero) || '';
    document.getElementById('calorie_giornaliere').value = Math.round(data.calorie_giornaliere) || '';
    document.getElementById('settimane_dieta').value = data.settimane_dieta || '';
    document.getElementById('carboidrati_input').value = Math.round(data.carboidrati) || '';
    document.getElementById('proteine_input').value = Math.round(data.proteine) || '';
    document.getElementById('grassi_input').value = Math.round(data.grassi) || '';
    document.getElementById('dieta').value = data.dieta || '';
    document.getElementById('attivita_fisica').value = data.attivita_fisica || '';
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

    const settimaneDietaVisible = document.getElementById('settimane_dieta');
    const settimaneDietaHidden = document.getElementById('settimane_dieta_hidden');
    settimaneDietaHidden.value = settimaneDietaVisible.value;

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

function addWeeksToDate(weeks) {
    const today = new Date(); // Data di oggi
    const resultDate = new Date(today); // Crea una nuova data basata su oggi
    resultDate.setDate(today.getDate() + weeks * 7); // Aggiunge il numero di giorni (settimane * 7)

    // Array con i nomi dei mesi in italiano
    const months = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"];

    // Estrai mese e anno
    const month = months[resultDate.getMonth()]; // Ottiene il nome del mese
    const year = resultDate.getFullYear(); // Anno

    return `${month} ${year}`;
}

function calculateResults() {

    const form = document.getElementById('personalInfoForm');

    const bmiInput = document.getElementById('bmi');
    const idealWeightInput = document.getElementById('peso_ideale');
    const metaBasale = document.getElementById('meta_basale');
    const metaDaily = document.getElementById('meta_giornaliero');
    const calorieGiornaliere = document.getElementById('calorie_giornaliere');
    const settimaneDieta = document.getElementById('settimane_dieta');
    const carboidrati = document.getElementById('carboidrati_input');
    const proteine = document.getElementById('proteine_input');
    const grassi = document.getElementById('grassi_input');

    // Verifica se il form è stato correttamente selezionato
    if (!form) {
        console.error('Form non trovato!');
        return;
    }

    const formData = new FormData(form);
    const data = {
        nome: formData.get('nome'),
        cognome: formData.get('cognome'),
        sesso: formData.get('sesso'),
        eta: formData.get('eta'),
        peso: formData.get('peso'),
        altezza: formData.get('altezza'),
        tdee: formData.get('tdee'),
        deficit: Number(formData.get('deficit_calorico')),
        dieta: formData.get('dieta'),
        attivita_fisica: formData.get('attivita_fisica')
    };

    // Esegui i calcoli basati sui dati inseriti
    let bmi = (data.peso / Math.pow(data.altezza / 100, 2)).toFixed(1); // esempio di calcolo del BMI, con un'altezza fissa

    //idealWeight = calcolaPesoIdeale(data)

    idealWeight = (21.7 * (data.altezza/100 * data.altezza/100)).toFixed(0)

    //calcolo del BME
    let bmrValue;

    let actualBMI;

    actualBMI = data.peso / (data.altezza/100 * data.altezza/100);

    if (data.sesso === 'M') {
        // Formula di Harris Benedict
        bmrValue = 66.5 + (13.75 * idealWeight) + (5.003 * data.altezza) - (6.775 * data.eta);
        if (actualBMI >= 30){
            // Formula di Mifflin-St Jeor in caso di obesita
            bmrValue = (10 * idealWeight) + (6.25 * data.altezza) - (5 * data.eta) + 5;
        }
    } else if (data.sesso === 'F') {
        // Formula di Harris Benedict
        bmrValue = 655.1 + (9.563 * idealWeight) + (1.85 * data.altezza) - (4.676 * data.eta);
        if (actualBMI >= 30){
            // Formula di Mifflin-St Jeor in caso di obesita
            bmrValue = (10 * idealWeight) + (6.25 * data.altezza) - (5 * data.eta) - 161;
        }
    }

    let metaBasaleValue = bmrValue.toFixed(0);

    let metaDailyValue = (metaBasaleValue * data.tdee).toFixed(0);

    let calorieGiornaliereValue = metaDailyValue;

    if (data.deficit > 0) {
        let deficitCalorico = 0;

        switch (data.sesso) {
            case 'F':
                if (data.deficit === 1) {
                    deficitCalorico = 250; // Deficit moderato per donne
                } else if (data.deficit === 2) {
                    deficitCalorico = 350; // Deficit aggressivo per donne
                }
                break;

            case 'M':
                if (data.deficit === 1) {
                    deficitCalorico = 350; // Deficit moderato per uomini
                } else if (data.deficit === 2) {
                    deficitCalorico = 500; // Deficit aggressivo per uomini
                }
                break;

            default:
                deficitCalorico = 0; // Nessun deficit
                break;
        }

    // Calcolo delle calorie giornaliere applicando la sottrazione diretta
        calorieGiornaliereValue = (Math.round((metaDailyValue - deficitCalorico) / 50) * 50).toFixed(0);
    }

    let settimaneDietaValue = 0;
    let settimaneNecessarie = 0;

    if (data.deficit > 0) {
        settimaneNecessarie = (((data.peso - idealWeight) * 7000) / ((metaDailyValue - calorieGiornaliereValue) * 7)).toFixed(0);
        settimaneDietaValue = settimaneNecessarie + ' (' + addWeeksToDate(settimaneNecessarie) + ')';
    }

    let carbsRatio, proteinRatio, fatRatio;

    switch (data.dieta) {
        case 'balanced':
            carbsRatio = 0.55;
            proteinRatio = 0.25;
            fatRatio = 0.20;
            break;
        case 'low_carb':
            carbsRatio = 0.25;
            proteinRatio = 0.35;
            fatRatio = 0.40;
            break;
        case 'keto':
            carbsRatio = 0.05;
            proteinRatio = 0.20;
            fatRatio = 0.75;
            break;
        case 'high_protein':
            carbsRatio = 0.35;
            proteinRatio = 0.40;
            fatRatio = 0.25;
            break;
        case 'low_fat':
            carbsRatio = 0.60;
            proteinRatio = 0.15;
            fatRatio = 0.25;
            break;
        case 'mediterranean':
            carbsRatio = 0.50;
            proteinRatio = 0.20;
            fatRatio = 0.30;
            break;
        case 'personalizzata':
            carbsRatio = 0.50;
            proteinRatio = 0.20;
            fatRatio = 0.30;
            break;
    }

    //var carboidratiValue = (calorieGiornaliereValue * carbsRatio / 4).toFixed(0);
    //var proteineValue = (calorieGiornaliereValue * proteinRatio / 4).toFixed(0);
    //var grassiValue = (calorieGiornaliereValue * fatRatio / 9).toFixed(0);

    var proteineValue = (idealWeight * data.attivita_fisica).toFixed(0);
    var grassiValue = (idealWeight * 1).toFixed(0);
    var carboidratiValue = ((calorieGiornaliereValue - ((proteineValue * 4) + (grassiValue * 9))) / 4).toFixed(0);

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
    if (carboidrati.disabled && proteine.disabled && grassi.disabled){
        calorieGiornaliere.value = calorieGiornaliereValue;
    } else {
        calorieGiornaliere.value = (carboidrati.value * 4) + (proteine.value * 4) + (grassi.value * 9);
    }

    settimaneDieta.value = settimaneDietaValue;
    if (carboidrati.disabled) {
        carboidrati.value = carboidratiValue;
    }
    if (proteine.disabled) {
        proteine.value = proteineValue;
    }
    if (grassi.disabled){
        grassi.value = grassiValue;
    }

    synchronizeFields();
}

// Funzione per salvare l'alimento
function saveAlimento(alimentoData) {
    fetch(`/alimenti/${alimentoData.id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(alimentoData),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            console.log('Alimento salvato con successo.');
            fetchAlimentiData();
        } else {
            console.error('Errore nel salvataggio:', data.message);
        }
    })
    .catch(error => {
        console.error('Errore:', error);
    });
}

// Funzione per eliminare l'alimento
function deleteAlimento(alimentoId) {
    fetch(`/alimenti/${alimentoId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            fetchAlimentiData();
            filterAlimentiTable();
        })
        .catch((error) => {
            console.error('Errore:', error);
        });
}

// Utility function to capitalize the first letter of a string
function capitalize(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

function loadAndUpdateMenuData() {
    var weekId = selectedWeekId; // Ottieni l'ID della settimana selezionata

    if (!selectedWeekId) {
        weekId = document.querySelector('.week-select').value;
    }
    // Fai il fetch per caricare i dati del menu per la settimana selezionata
    fetch(`/menu_settimana/${weekId}`)
        .then(response => response.json())
        .then(data => {
            if (data.menu) {
                // Qui inserisci la logica per caricare i dati del menu nel div #menuEditor
                renderMenuEditor(data);
            }
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
        case 'spuntino_sera':
            return 'Spuntino Sera';
        default:
            return capitalize(meal);
    }
}


function buildRemainingGruppiTable(menuConsumi, gruppi) {
    // Filtra i gruppi in base agli ID presenti in menuConsumi
    const filteredGruppi = gruppi.filter(gruppo => menuConsumi.hasOwnProperty(gruppo.id.toString()));

    // Seleziona gli elementi HTML della tabella
    const remainingGruppiTableHeader = document.querySelector('#remaining-consumi-table thead');
    const remainingGruppiTableBody = document.querySelector('#remaining-consumi-table tbody');

    // Costruisce l'header dinamicamente
    let headerHTML = '<tr>';
    filteredGruppi.forEach(gruppo => {
        headerHTML += `<th style="text-align: center;">${gruppo.nome}</th>`;
    });
    headerHTML += '</tr>';
    remainingGruppiTableHeader.innerHTML = headerHTML;

    // Costruisce la riga dei consumi rimanenti
    let bodyHTML = '<tr>';
    filteredGruppi.forEach(gruppo => {
        const id = gruppo.id.toString();
        const consumoRimanente = menuConsumi[id] || 0; // Prendi il consumo rimanente o 0 se non trovato
        bodyHTML += `<td style="width:11% !important; text-align: center;">${consumoRimanente} g</td>`;
    });
    bodyHTML += '</tr>';
    remainingGruppiTableBody.innerHTML = bodyHTML;
}


function renderMenuEditor(data) {

    // Chiama questa funzione quando la pagina viene caricata per popolare i dropdown
    populateWeekDropdowns();

    const selectedWeek = selectedWeekId;
    const selectedDay = document.getElementById('day_select') ? document.getElementById('day_select').value : null;

    const menuEditor = document.getElementById("menuEditor");
    menuEditor.innerHTML = ''; // Pulisce l'editor

    // Cerca il contenitore esistente dei macronutrienti rimanenti
    const macrosContainer = document.getElementById('remaining-macros-container');
    macrosContainer.innerHTML = '';

    const menu = data.menu;

    const days = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato', 'domenica'];
    const meals = ['colazione', 'spuntino_mattina', 'pranzo', 'spuntino_pomeriggio', 'cena', 'spuntino_sera'];

    // Creazione della tabellina per i rimanenti giornalieri
    const remainingTable = document.createElement('table');
    remainingTable.id = 'remainingTable';
    remainingTable.classList.add('table', 'table-sm', 'table-bordered', 'table-striped');

    const remainingTableHeader = document.createElement('thead');
    remainingTableHeader.innerHTML = `
        <tr>
            <th style="width:20%; text-align: center;">Giorno</th>
            <th style="width:20%; text-align: center;">Kcal</th>
            <th style="width:20%; text-align: center;">Carbs</th>
            <th style="width:20%; text-align: center;">Prot</th>
            <th style="width:20%; text-align: center;">Fat</th>
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
            <td style="text-align: center;">${remaining.kcal.toFixed(2)}</td>
            <td style="text-align: center;">${remaining.carboidrati.toFixed(2)}</td>
            <td style="text-align: center;">${remaining.proteine.toFixed(2)}</td>
            <td style="text-align: center;">${remaining.grassi.toFixed(2)}</td>
        `;
        remainingTableBody.appendChild(row);
    });

    // Aggiungi i totali settimanali come ultima riga della tabella
    const totalRow = document.createElement('tr');
    totalRow.innerHTML = `
        <th>Totale</th>
        <th style="text-align: center;">${totalKcal.toFixed(2)}</th>
        <th style="text-align: center;">${totalCarboidrati.toFixed(2)}</th>
        <th style="text-align: center;">${totalProteine.toFixed(2)}</th>
        <th style="text-align: center;">${totalGrassi.toFixed(2)}</th>
    `;
    remainingTableBody.appendChild(totalRow);

    remainingTable.appendChild(remainingTableBody);
    macrosContainer.appendChild(remainingTable); // Inserisci la card nel macrosContainer

    buildRemainingGruppiTable(menu['consumi'], gruppi);

    // Aggiungi la tabella sotto al week selector
    const menuContainer = document.getElementById('menuEditor');

    // Creazione delle card per ogni giorno
    days.forEach(day => {
        const dayContainer = document.createElement('div');
        dayContainer.classList.add('day-container', 'mb-2');
        dayContainer.setAttribute('data-day', day); // Aggiungi l'attributo data-day per il filtraggio

        const card = document.createElement('div');
        card.classList.add('card');

        const cardBody = document.createElement('div');
        cardBody.classList.add('card-body');

        const dayTitleContainer = document.createElement('div');
        dayTitleContainer.classList.add('d-flex', 'align-items-center', 'justify-content-between'); // Contenitore flessibile

        const dayTitle = document.createElement('h5');
        dayTitle.classList.add('card-title', 'mb-0'); // Rimuove il margine inferiore
        dayTitle.textContent = `${capitalize(day)}`;

        const buttonDayGroup = document.createElement('div');
        buttonDayGroup.classList.add('btn-group', 'ms-3');

        const cancellaColazioneDailyBtn = document.createElement('button');
        cancellaColazioneDailyBtn.innerHTML = `<i class="fa fa-trash"></i> Colazione ${capitalize(day)}`;
        cancellaColazioneDailyBtn.classList.add('btn', 'btn-danger', 'btn-sm');

        const cancellaPranzoCenaDailyBtn = document.createElement('button');
        cancellaPranzoCenaDailyBtn.innerHTML = `<i class="fa fa-trash"></i> Pranzo/Cena ${capitalize(day)}`;
        cancellaPranzoCenaDailyBtn.classList.add('btn', 'btn-danger', 'btn-sm');

        const cancellaSpuntiniDailyBtn = document.createElement('button');
        cancellaSpuntiniDailyBtn.innerHTML = `<i class="fa fa-trash"></i> Spuntini ${capitalize(day)}`;
        cancellaSpuntiniDailyBtn.classList.add('btn', 'btn-danger', 'btn-sm');

        const cancellaTuttoDailyBtn = document.createElement('button');
        cancellaTuttoDailyBtn.innerHTML = `<i class="fa fa-trash"></i> ${capitalize(day)}`;
        cancellaTuttoDailyBtn.classList.add('btn', 'btn-danger', 'btn-sm');

        const invertMealsBtn = document.createElement('button');
        invertMealsBtn.innerHTML = `<i class="fas fa-exchange-alt"></i> Pranzo/Cena`;
        invertMealsBtn.classList.add('btn', 'btn-warning', 'btn-sm'); // Margine a sinistra
        buttonDayGroup.appendChild(invertMealsBtn);
        buttonDayGroup.appendChild(cancellaColazioneDailyBtn);
        buttonDayGroup.appendChild(cancellaPranzoCenaDailyBtn);
        buttonDayGroup.appendChild(cancellaSpuntiniDailyBtn);
        buttonDayGroup.appendChild(cancellaTuttoDailyBtn);

        // Aggiungi il titolo e il pulsante al contenitore
        dayTitleContainer.appendChild(dayTitle);
        dayTitleContainer.appendChild(buttonDayGroup);

        // Aggiungi il contenitore al cardBody
        cardBody.appendChild(dayTitleContainer);

        // Imposta l'evento clic per il pulsante
        invertMealsBtn.onclick = function() {
            invertMeals(day);
        };

        cancellaPranzoCenaDailyBtn.onclick = function() {
            cancellaMealDaily(day, 'principali');
        };

        cancellaColazioneDailyBtn.onclick = function() {
            cancellaMealDaily(day, 'colazione');
        };

        cancellaSpuntiniDailyBtn.onclick = function() {
            cancellaMealDaily(day, 'spuntini');
        };

        cancellaTuttoDailyBtn.onclick = function() {
            cancellaMealDaily(day, 'all');
        };


        meals.forEach(meal => {
            const mealContainer = document.createElement('div');
            mealContainer.classList.add('meal-container');

            // Creare una tabella per ogni pasto
            const mealTable = document.createElement('table');

            mealTable.classList.add('table', 'table-sm', 'table-bordered', 'mb-2', 'table-striped');

            const mealTableHead = document.createElement('thead');
            mealTableHead.innerHTML = `
                <tr>
                    <th style="width:34%; text-align: center;">${formatMealName(meal)}</th>
                    <th style="width:11%; text-align: center;">Kcal</th>
                    <th style="width:11%; text-align: center;">Carbs</th>
                    <th style="width:11%; text-align: center;">Prot</th>
                    <th style="width:11%; text-align: center;">Fat</th>
                    <th style="width:11%; text-align: center;">Quantità</th>
                    <th style="width:11%; text-align: center;">Azioni</th>
                </tr>
            `;
            mealTable.appendChild(mealTableHead);

            const mealTableBody = document.createElement('tbody');

            if (menu.day[day].pasto[meal].ricette.length > 0) {
                menu.day[day].pasto[meal].ricette.forEach(ricetta => {
                    const row = document.createElement('tr');
                    row.id = `meal-${ricetta.id}-${day}-${meal}`;
                    row.innerHTML = `
                        <td><div data-bs-toggle="tooltip" data-bs-title='${ricetta.ricetta.map(item => `${item.nome} ${item.qta}g`).join("; ")}' class="recipe-cell">${ricetta.nome_ricetta}</div></td>
                        <td style="text-align: center;">${(ricetta.kcal * ricetta.qta).toFixed(2)}</td>
                        <td style="text-align: center;">${(ricetta.carboidrati * ricetta.qta).toFixed(2)}</td>
                        <td style="text-align: center;">${(ricetta.proteine * ricetta.qta).toFixed(2)}</td>
                        <td style="text-align: center;">${(ricetta.grassi * ricetta.qta).toFixed(2)}</td>
                        <td style="text-align: center;"><input type="number" class="form-control form-control-sm input-hidden-border" value="${ricetta.qta}" min="0.1" step="0.1" onchange="updateMealQuantity('${day}', '${meal}', '${ricetta.id}', this.value)"></td>
                        <td style="text-align: center;"><button class="btn btn-danger btn-sm" onclick="removeMeal('${day}', '${meal}', '${ricetta.id}')"><i class="fas fa-trash-alt"></button></td>
                    `;
                    mealTableBody.appendChild(row);
                });

                mealTable.appendChild(mealTableBody);
            }

            mealContainer.appendChild(mealTable);

            const buttonGroup = document.createElement('div');
            buttonGroup.classList.add('btn-group', 'mt-2');

            // Pulsante "Aggiungi Ricetta"
            const addMealBtn = document.createElement('button');
            addMealBtn.innerHTML = `<i class="fa fa-plus" aria-hidden="true"></i> Ricetta`; // Aggiungi l'icona e il testo
            addMealBtn.classList.add('btn', 'btn-success', 'btn-sm');
            addMealBtn.onclick = function() {
                aggiungiRicettaAlPasto(true, 'no', false, 'principale', meal, day, true);
            };
            buttonGroup.appendChild(addMealBtn);

            // Pulsante "Aggiungi Contorno"
            if (meal != 'colazione' && !meal.startsWith('spuntino')){
                const addContornoBtn = document.createElement('button');
                addContornoBtn.innerHTML = `<i class="fa fa-plus" aria-hidden="true"></i> Contorno`; // Aggiungi l'icona e il testo
                addContornoBtn.classList.add('btn', 'btn-success', 'btn-sm');
                addContornoBtn.onclick = function() {
                    aggiungiRicettaAlPasto(true, 'no', true, 'contorno', meal, day, false);
                };
                buttonGroup.appendChild(addContornoBtn);
            }

            // Pulsante "Aggiungi Complemento"
            if (!meal.startsWith('spuntino')){
                const addComplementoBtn = document.createElement('button');
                addComplementoBtn.innerHTML = `<i class="fa fa-plus" aria-hidden="true"></i> Complemento`; // Aggiungi l'icona e il testo
                addComplementoBtn.classList.add('btn', 'btn-success', 'btn-sm');
                addComplementoBtn.onclick = function() {
                    aggiungiRicettaAlPasto(true, 'yes', false, 'complemento', meal, day, false);
                };
                buttonGroup.appendChild(addComplementoBtn);
            }

            // Aggiungi il gruppo di pulsanti al contenitore
            mealContainer.appendChild(buttonGroup);

            cardBody.appendChild(mealContainer);
        });

        card.appendChild(cardBody);
        dayContainer.appendChild(card);
        menuEditor.appendChild(dayContainer);
    });

    // Ripristina lo stato delle selezioni
    document.getElementById('settimana_select').value = selectedWeekId;
    if (selectedDay) {
        document.getElementById('day_select').value = selectedDay;
    }

    filterDayCards();
    aggiornaTabellaMenu(data.menu);

    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
}


function updateMealQuantity(day, meal, ricettaId, newQuantity) {
    const data = {
        day: day,
        meal: meal,
        ricetta_id: ricettaId,
        quantity: newQuantity,
        week_id: selectedWeekId
    };

    fetch(`/aggiorna_quantita_ingrediente`, {
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
    fetch(`/rimuovi_ricetta/${selectedWeekId}`, {
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
            const rowId = `meal-${mealId}-${day}-${meal}`;
            const row = document.getElementById(rowId);

            // Se la tabella non ha più righe nel corpo, lascia la `thead` intatta
            const mealTableBody = row.parentNode;

            // Se la riga esiste, rimuovila
            if (row) {
                row.parentNode.removeChild(row);
            }

            if (mealTableBody.rows.length === 0) {
                // Verifica se la tabella è ancora presente
                const mealContainer = mealTableBody.closest('.meal-container');
                const mealTable = mealContainer.querySelector('table');
                if (mealTable) {
                    // Svuota il corpo della tabella ma mantieni la `thead`
                    mealTableBody.innerHTML = '';
                }
            }
            renderMenuEditor(data);
        })
        .catch(error => console.error('Error:', error));
}

function openAddMealModal(selectedDay) {
    if (!selectedDay || selectedDay === 'all') {
        alert("Seleziona un giorno specifico per aggiungere una ricetta.");
        return;
    }

    populatePopupRemainingMacros(selectedDay);

    const addMealModal = new bootstrap.Modal(document.getElementById('addMealModal'));
    addMealModal.show();
}

function populatePopupRemainingMacros(day) {
    const remainingTable = document.getElementById('remainingTable'); // La tabella nella pagina principale
    if (!remainingTable) return;

    // Cerca la riga corrispondente al giorno selezionato
    const rows = remainingTable.getElementsByTagName('tr');
    for (let i = 1; i < rows.length; i++) {  // Salta l'intestazione
        let cells = rows[i].getElementsByTagName('td');
        if (cells[0].textContent.toLowerCase() === day.toLowerCase()) {
            document.getElementById('popup-day').textContent = cells[0].textContent;
            document.getElementById('popup-kcal').textContent = cells[1].textContent;
            document.getElementById('popup-carbs').textContent = cells[2].textContent;
            document.getElementById('popup-protein').textContent = cells[3].textContent;
            document.getElementById('popup-fat').textContent = cells[4].textContent;
            break;
        }
    }
}

function aggiungiRicettaAlPasto(stagionalita, complemento, contorno, meal_type, meal, day, available) {
    currentDay = day;
    currentMeal = meal;


    const remainingTable = document.getElementById('remainingTable'); // La tabella nella pagina principale
    if (!remainingTable) return;

    let remainingKcal = 0;
    let remainingCarbs =  0;
    let remainingProteins = 0;
    let remainingFats = 0;

    // Cerca la riga corrispondente al giorno selezionato
    const rows = remainingTable.getElementsByTagName('tr');
    for (let i = 1; i < rows.length; i++) {  // Salta l'intestazione
        let cells = rows[i].getElementsByTagName('td');
        if (cells[0].textContent.toLowerCase() === day.toLowerCase()) {
            // Recupera i valori dei macronutrienti rimanenti per il giorno selezionato
            remainingKcal = parseFloat(cells[1].textContent);
            remainingCarbs =  parseFloat(cells[2].textContent);
            remainingProteins = parseFloat(cells[3].textContent);
            remainingFats = parseFloat(cells[4].textContent);
            break;
        }
    }

    // Fetch delle ricette disponibili per quel pasto
    fetch(`/ricette?stagionalita=${stagionalita}&complemento=${complemento}&contorno=${contorno}&attive=true&meal_time=${meal}&meal_type=${meal_type}&day=${day}&week_id=${selectedWeekId}&available=${available}`)
        .then(response => response.json())
        .then(data => {
            if (data.status == 'success'){
                const mealSelectionBody = document.getElementById('mealSelectionBody');
                mealSelectionBody.innerHTML = ''; // Pulisce la tabella

                // Filtra le ricette che rispettano le kcal e almeno 2 su 3 macronutrienti
                const filteredRicette = data.ricette.filter(ricetta => {
                    const kcalOk = ricetta.kcal <= remainingKcal;

                    let validMacroCount = 0;
                    if (ricetta.carboidrati <= remainingCarbs) validMacroCount++;
                    if (ricetta.proteine <= remainingProteins) validMacroCount++;
                    if (ricetta.grassi <= remainingFats) validMacroCount++;

                    return kcalOk && validMacroCount >= 2;
                });

                // Popola la tabella solo con le ricette filtrate
                filteredRicette.forEach(ricetta => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${ricetta.nome_ricetta}</td>
                        <td>${ricetta.kcal}</td>
                        <td>${ricetta.carboidrati}</td>
                        <td>${ricetta.proteine}</td>
                        <td>${ricetta.grassi}</td>
                        <td>${ricetta.fibre}</td>
                        <td>${ricetta.zucchero}</td>
                        <td>${ricetta.sale}</td>
                        <td><input type="checkbox" value="${ricetta.id}" data-kcal="${ricetta.kcal}" class="meal-checkbox"></td>
                    `;
                    mealSelectionBody.appendChild(row);
                });

                if (filteredRicette.length === 0) {
                    const noDataRow = document.createElement('tr');
                    noDataRow.innerHTML = `<td colspan="7" class="text-center text-danger">Nessuna ricetta disponibile entro le kcal rimanenti.</td>`;
                    mealSelectionBody.appendChild(noDataRow);
                }

                // Mostra il modal
                openAddMealModal(day)
            }
        });
}

function recalculateCalories(alimentoId) {
    const carboidrati = parseFloat(document.querySelector(`input[name='carboidrati_${alimentoId}']`).value) || 0;
    const proteine = parseFloat(document.querySelector(`input[name='proteine_${alimentoId}']`).value) || 0;
    const grassi = parseFloat(document.querySelector(`input[name='grassi_${alimentoId}']`).value) || 0;
    const fibre = parseFloat(document.querySelector(`input[name='fibre_${alimentoId}']`).value) || 0;

    const calorie = (carboidrati * 4) + (proteine * 4) + (grassi * 9) + (fibre * 2);

    document.getElementById(`calorie_${alimentoId}`).textContent = calorie.toFixed(2);
}

function addMealsToMenu(day, meal, selectedMeals) {
    fetch(`/aggiungi_ricetta_menu/${selectedWeekId}`, {
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
    const vita = document.getElementById('vitaInput').value;
    const fianchi = document.getElementById('fianchiInput').value;
    const date = new Date().toISOString().slice(0, 10); // Prende la data odierna

    // Invia il peso al server (assumendo che tu abbia un endpoint API)
    fetch('/submit_weight', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                date: date,
                weight: weight,
                vita: vita,
                fianchi: fianchi
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === "error"){
                showAlertModal(data.message);
            } else {
                updateWeightChart(data.peso); // Aggiorna il grafico dopo l'invio
            }
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
    if (myChart) {
        myChart.destroy();
    }

    myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: weights.map(item => formatDate(item.data_rilevazione)),
            datasets: [{
                label: 'Peso Ideale',
                data: weights.map(item => item.peso_ideale),
                backgroundColor: 'rgba(153, 102, 255, 0.1)', // Viola chiaro
                borderColor: 'rgba(153, 102, 255, 0.5)', // Viola intenso
                borderWidth: 1,
                borderDash: [10, 5], // Linea tratteggiata
                pointRadius: 3,
                pointBackgroundColor: 'rgba(153, 102, 255, 0.5)',
                pointHoverRadius: 5,
                spanGaps: true // Collega i punti ignorando i null
            },
            {
                label: 'Peso',
                data: weights.map(item => item.peso),
                backgroundColor: 'rgba(255, 99, 132, 0.2)', // Rosso chiaro
                borderColor: 'rgba(255, 99, 132, 1)', // Rosso intenso
                borderWidth: 1,
                pointRadius: 5,
                pointBackgroundColor: 'rgba(255, 99, 132, 1)',
                pointHoverRadius: 7,
                spanGaps: true
            },
            {
                label: 'Vita',
                data: weights.map(item => item.vita),
                backgroundColor: 'rgba(54, 162, 235, 0.2)', // Blu chiaro
                borderColor: 'rgba(54, 162, 235, 1)', // Blu intenso
                borderWidth: 1,
                pointRadius: 5,
                pointBackgroundColor: 'rgba(54, 162, 235, 1)',
                pointHoverRadius: 7,
                spanGaps: true
            },
            {
                label: 'Fianchi',
                data: weights.map(item => item.fianchi),
                backgroundColor: 'rgba(75, 192, 192, 0.2)', // Verde acqua chiaro
                borderColor: 'rgba(75, 192, 192, 1)', // Verde acqua intenso
                borderWidth: 1,
                pointRadius: 5,
                pointBackgroundColor: 'rgba(75, 192, 192, 1)',
                pointHoverRadius: 7,
                spanGaps: true
            },
            {
                label: 'Vo2',
                data: weights.map(item => item.vo2),
                backgroundColor: 'rgba(255, 159, 64, 0.2)', // Arancione chiaro
                borderColor: 'rgba(255, 159, 64, 1)', // Arancione intenso
                borderWidth: 1,
                pointRadius: 5,
                pointBackgroundColor: 'rgba(255, 159, 64, 1)',
                pointHoverRadius: 7,
                spanGaps: true
            },
            {
                label: '% Massa Grassa',
                data: weights.map(item => item.perc_massa_grassa),
                backgroundColor: 'rgba(153, 102, 255, 0.2)', // Viola chiaro (diverso dal Peso Ideale per distinguere)
                borderColor: 'rgba(153, 102, 255, 1)', // Viola intenso
                borderWidth: 1,
                pointRadius: 5,
                pointBackgroundColor: 'rgba(153, 102, 255, 1)',
                pointHoverRadius: 7,
                spanGaps: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 120,
                    grid: {
                        color: 'rgba(200, 200, 200, 0.3)',
                        borderDash: [5, 5]
                    },
                    ticks: {
                        padding: 10
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        padding: 10
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        boxWidth: 20,
                        padding: 15,
                        usePointStyle: true,
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += context.parsed.y.toFixed(2);
                            if (context.dataset.label === 'Peso' || context.dataset.label === 'Peso Ideale') {
                                label += ' kg';
                            } else {
                                label += ' cm';
                            }
                            return label;
                        }
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeInOutQuad'
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
            } else if (data.status === 'error') {
                setTimeout(() => {
                    $('#errorModal').modal('show');
                    $('#generateMenuModal').modal('hide'); // Chiudi il modal
                }, 4000);
            }
        })
        .catch(error => {
            console.error('Errore durante la generazione del menu:', error);
        });
}

function completeMenu() {
    const weekId = selectedWeekId;

    // Effettua una richiesta AJAX per avviare il completamento del menu
    fetch(`/complete_menu/${weekId}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateProgress(100); // Imposta il progresso al 100%
                setTimeout(() => {
                    $('#generateMenuModal').modal('hide'); // Chiudi il modal
                    location.reload(); // Ricarica la pagina per visualizzare il nuovo menu
                }, 1000);
            } else if (data.status === 'error') {
                setTimeout(() => {
                    $('#errorModal').modal('show');
                    $('#generateMenuModal').modal('hide'); // Chiudi il modal
                }, 4000);
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
    document.getElementById('filter-ricette-calorie-min').value = '';
    document.getElementById('filter-ricette-calorie-max').value = '';
    document.getElementById('filter-ricette-carbo-min').value = '';
    document.getElementById('filter-ricette-carbo-max').value = '';
    document.getElementById('filter-ricette-proteine-min').value = '';
    document.getElementById('filter-ricette-proteine-max').value = '';
    document.getElementById('filter-ricette-grassi-min').value = '';
    document.getElementById('filter-ricette-grassi-max').value = '';
    document.getElementById('filter-ricette-fibre-min').value = '';
    document.getElementById('filter-ricette-fibre-max').value = '';
    document.getElementById('filter-ricette-zucchero-min').value = '';
    document.getElementById('filter-ricette-zucchero-max').value = '';
    document.getElementById('filter-ricette-sale-min').value = '';
    document.getElementById('filter-ricette-sale-max').value = '';
    document.getElementById('filter-colazione').value = 'all';
    document.getElementById('filter-complemento-ricette').value = 'all';
    document.getElementById('filter-colazione-sec').value = 'all';
    document.getElementById('filter-spuntino').value = 'all';
    document.getElementById('filter-principale').value = 'all';
    document.getElementById('filter-contorno').value = 'all';
    document.getElementById('filter-attiva').value = 'all';
    document.getElementById('filter-info').value = 'all';

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
    document.getElementById('filter-fibre-min').value = '';
    document.getElementById('filter-fibre-max').value = '';
    document.getElementById('filter-zucchero-min').value = '';
    document.getElementById('filter-zucchero-max').value = '';
    document.getElementById('filter-sale-min').value = '';
    document.getElementById('filter-sale-max').value = '';
    document.getElementById('filter-vegan').value = 'all';
    document.getElementById('filter-surgelato').value = 'all';
    document.getElementById('filter-gruppo').value = 'all';

    // Resetta i filtri dei pulsanti di stagionalità
    document.querySelectorAll('.month-filter-btn').forEach(button => {
        button.classList.remove('btn-primary', 'btn-danger');
        button.classList.add('btn-outline-secondary');
    });

    // Chiama la funzione che filtra la tabella per aggiornare i risultati
    filterAlimentiTable();
}

function deleteMenu() {
    var weekId = selectedWeekId; // Ottieni l'ID della settimana selezionata

    if (!selectedWeekId) {
        weekId = document.querySelector('.week-select').value;
    }

    fetch(`/delete_menu/${weekId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    }).then(response => {
        if (response.ok) {
            localStorage.removeItem('selectedWeekId');
            location.reload(); // Ricarica la pagina per aggiornare la selezione dei menu
        } else {
            return response.json(); // Elabora il messaggio di errore
        }
    }).then(data => {
        if (data && data.status === 'error') {
            showAlertModal(data.message); // Mostra il messaggio di errore nel modal
        }
    }).catch(error => {
        console.error("Errore:", error);
    });
}

function recupera_tutte_le_ricette()  {
       fetch('/ricette?stagionalita=false&complemento=all&contorno=false&attive=false')
            .then(response => response.json())
            .then(data => {
                 populateRicetteTable(data.ricette);
            })
            .catch(error => console.error('Errore nel caricamento dei dati:', error));
}


function fetchAlimentiData() {
    fetch('/alimenti')
        .then(response => response.json())
        .then(data => {
            populateAlimentiTable(data.alimenti);
        })
        .catch(error => console.error('Errore nel caricamento degli alimenti:', error));
}

// Supponendo che `gruppi` sia fornito dal backend come array
function fetchGroupsAndPopulate() {
    fetch('/get_gruppi')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                gruppi = data.gruppi; // Salva i gruppi nella variabile globale
                populateGroupDropdown(data.gruppi);
            } else {
                console.error('Errore nel recupero dei gruppi:', data.message);
            }
        })
        .catch(error => console.error('Errore di rete:', error));
}

function populateGroupDropdown(gruppi) {
    const select = document.getElementById('filter-gruppo');
    const select_gruppo = document.getElementById('gruppo');
    gruppi.forEach(gruppo => {
        // Crea un'opzione per la prima select
        const option1 = document.createElement('option');
        option1.value = gruppo.id;
        option1.textContent = gruppo.nome;
        select.appendChild(option1);

        // Crea un'opzione separata per la seconda select
        const option2 = document.createElement('option');
        option2.value = gruppo.id;
        option2.textContent = gruppo.nome;
        if (gruppo.id === 11) {
            option2.selected = true; // Imposta "Altri" come predefinito se è nella lista
        }
        select_gruppo.appendChild(option2);
    });
}



function populateAlimentiTable(alimenti) {
    const tbody = document.getElementById('alimenti-tbody');
    tbody.innerHTML = '';

    alimenti.forEach(alimento => {
        const row = document.createElement('tr');

        row.innerHTML = `
            <td>
                <div>
                    <input type="text" class="form-control input-hidden-border form-control-sm" data-alimento-id="${alimento.id}" data-alimento-nome="${alimento.nome}" name="nome_${alimento.id}" value="${alimento.nome}">
                    <label hidden class="form-control form-control-sm">${alimento.nome}</label>
                </div>
            </td>
            <td id="calorie_${alimento.id}" style="text-align: center;">${alimento.kcal}</td>
            <td>
                <div>
                    <input type="number" class="form-control form-control-sm input-hidden-border"  min="0.1" step="0.1" data-alimento-id="${alimento.id}" name="carboidrati_${alimento.id}" value="${alimento.carboidrati}">
                    <label hidden class="form-control form-control-sm">${alimento.carboidrati}</label>
                </div>
            </td>
            <td>
                <div>
                    <input type="number" class="form-control  form-control-sm  input-hidden-border"  min="0.1" step="0.1" data-alimento-id="${alimento.id}" name="proteine_${alimento.id}" value="${alimento.proteine}">
                    <label hidden class="form-control form-control-sm">${alimento.proteine}</label>
                </div>
            </td>
            <td>
                <div>
                    <input type="number" class="form-control  form-control-sm  input-hidden-border"  min="0.1" step="0.1" data-alimento-id="${alimento.id}" name="grassi_${alimento.id}" value="${alimento.grassi}">
                    <label hidden class="form-control form-control-sm">${alimento.grassi}</label>
                </div>
            </td>
            <td>
                <div>
                    <input type="number" class="form-control  form-control-sm  input-hidden-border"  min="0.1" step="0.1" data-alimento-id="${alimento.id}" name="fibre_${alimento.id}" value="${alimento.fibre}">
                    <label hidden class="form-control form-control-sm">${alimento.fibre}</label>
                </div>
            </td>

            <td>
                <div>
                    <input type="number" class="form-control  form-control-sm  input-hidden-border"  min="0.1" step="0.1" data-alimento-id="${alimento.id}" name="zucchero_${alimento.id}" value="${alimento.zucchero}">
                    <label hidden class="form-control form-control-sm">${alimento.zucchero}</label>
                </div>
            </td>
            <td>
                <div>
                    <input type="number" class="form-control  form-control-sm  input-hidden-border"  min="0.1" step="0.1" data-alimento-id="${alimento.id}" name="sale_${alimento.id}" value="${alimento.sale}">
                    <label hidden class="form-control form-control-sm">${alimento.sale}</label>
                </div>
            </td>

            <td>
                <select class="form-select form-select-sm" name="gruppo_${alimento.id}" data-alimento-id="${alimento.id}">
                    <option value="null" ${!alimento.gruppo ? 'selected' : ''}>N/A</option>
                    ${gruppi.map(gruppo => `
                        <option value="${gruppo.id}" ${alimento.gruppo === gruppo.nome ? 'selected' : ''}>${gruppo.nome}</option>
                    `).join('')}
                </select>
            </td>
            <td  style="text-align: center;" >
                <div><input type="checkbox" name="vegan_${alimento.id}" ${alimento.vegan ? 'checked' : ''}><label hidden class="form-control form-control-sm">${alimento.vegan}</label></div>
            </td>
            <td  style="text-align: center;" >
                <div><input type="checkbox" name="surgelato_${alimento.id}" ${alimento.surgelato ? 'checked' : ''}><label hidden class="form-control form-control-sm">${alimento.surgelato}</label></div>
            </td>
            <td>
                <div class="month-toggle-group" id="stagionalita_${alimento.id}">
                    ${[...Array(12).keys()].map(month => `
                        <button type="button" class="btn btn-sm month-toggle-btn ${alimento.stagionalita.includes(month + 1) ? 'btn-primary' : 'btn-outline-secondary'}" data-month="${month + 1}">
                            ${new Date(2000, month).toLocaleString('it', { month: 'short' })}
                        </button>
                    `).join('')}
                </div>
            </td>
            <td  style="text-align: center;" >
                <div class="btn-group" role="group">
                    <button class="btn btn-success btn-sm save-alimento-btn" data-alimento-id="${alimento.id}" data-bs-toggle="tooltip" title="Salva"><i class="fas fa-save"></i></button>
                    <button class="btn btn-danger  btn-sm delete-alimento-btn" data-alimento-id="${alimento.id}" data-bs-toggle="tooltip" title="Elimina"><i class="fas fa-trash-alt"></i></button>
                </div>
            </td>
        `;

        tbody.appendChild(row);

        // Event listener per ricalcolare le calorie quando uno dei valori cambia
        document.querySelector(`input[name='carboidrati_${alimento.id}']`).addEventListener('input', () => {
            recalculateCalories(alimento.id);
        });

        document.querySelector(`input[name='proteine_${alimento.id}']`).addEventListener('input', () => {
            recalculateCalories(alimento.id);
        });

        document.querySelector(`input[name='grassi_${alimento.id}']`).addEventListener('input', () => {
            recalculateCalories(alimento.id);
        });

        document.querySelector(`input[name='fibre_${alimento.id}']`).addEventListener('input', () => {
            recalculateCalories(alimento.id);
        });
    });

    document.querySelectorAll('.month-toggle-group').forEach(group => {
        group.addEventListener('click', function (event) {
            const button = event.target.closest('.month-toggle-btn');
            if (!button) return;

            const alimentoId = this.id.split('_')[1]; // Estrai l'ID dell'alimento
            const month = parseInt(button.getAttribute('data-month')); // Estrai il mese

            // Alterna lo stile del pulsante
            button.classList.toggle('btn-primary');
            button.classList.toggle('btn-outline-secondary');

            // Ottieni i mesi selezionati
            const selectedMonths = Array.from(this.querySelectorAll('.btn-primary')).map(btn => parseInt(btn.getAttribute('data-month')));

            const alimentoData = {
                id: alimentoId,
                nome: document.querySelector(`input[name='nome_${alimentoId}']`).value,
                carboidrati: parseFloat(document.querySelector(`input[name='carboidrati_${alimentoId}']`).value),
                proteine: parseFloat(document.querySelector(`input[name='proteine_${alimentoId}']`).value),
                grassi: parseFloat(document.querySelector(`input[name='grassi_${alimentoId}']`).value),
                fibre: parseFloat(document.querySelector(`input[name='fibre_${alimentoId}']`).value),
                zucchero: parseFloat(document.querySelector(`input[name='zucchero_${alimentoId}']`).value),
                sale: parseFloat(document.querySelector(`input[name='sale_${alimentoId}']`).value),
                vegan: document.querySelector(`input[name='vegan_${alimentoId}']`).checked,
                surgelato: document.querySelector(`input[name='surgelato_${alimentoId}']`).checked,
                gruppo: document.querySelector(`select[name='gruppo_${alimentoId}']`).value,
                stagionalita: selectedMonths,
            };

            // Salva l'alimento aggiornato
            saveAlimento(alimentoData);
        });
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
                fibre: parseFloat(document.querySelector(`input[name='fibre_${alimentoId}']`).value),
                zucchero: parseFloat(document.querySelector(`input[name='zucchero_${alimentoId}']`).value),
                sale: parseFloat(document.querySelector(`input[name='sale_${alimentoId}']`).value),
                vegan: document.querySelector(`input[name='vegan_${alimentoId}']`).checked,
                surgelato: document.querySelector(`input[name='surgelato_${alimentoId}']`).checked,
                gruppo: document.querySelector(`select[name='gruppo_${alimentoId}']`).value
            };
            saveAlimento(alimentoData);
        });
    });

    document.querySelectorAll('.delete-alimento-btn').forEach(button => {
        button.addEventListener('click', function() {
            const alimentoId = this.getAttribute('data-alimento-id');
            const alimentoNome = this.getAttribute('data-alimento-nome');
            showConfirmDeleteAlimentoModal(alimentoId, alimentoNome);
        });
    });

    filterAlimentiTable();
}

function updateSelectedWeek() {
    var weekId = this.value;

    if (!weekId) {
        if (document.querySelector('.week-select') && document.querySelector('.week-select').value){
            weekId = document.querySelector('.week-select').value;
        }
    }

    if (weekId) {
        // Aggiorna il valore di selectedWeekId globale
        selectedWeekId = weekId;

        // Aggiorna tutte le select con il nuovo valore
        document.querySelectorAll('.week-select').forEach(sel => {
            sel.value = weekId;
        });

        // Chiama la funzione combinata per aggiornare la vista
        loadAndUpdateMenuData();

        // Filtra i day cards se necessario
        filterDayCards();
    }
}

// Funzione per recuperare le ricette contenenti l'alimento e aprire il modal di conferma
function showConfirmDeleteAlimentoModal(alimentoId, alimentoNome) {
    fetch(`/get_ricette_con_alimento/${alimentoId}`)
        .then(response => response.json())
        .then(data => {
            const ricetteList = document.getElementById('ricetteList');
            ricetteList.innerHTML = ''; // Pulisce l'elenco delle ricette

            data.ricette.forEach(ricetta => {
                const listItem = document.createElement('li');
                listItem.classList.add('list-group-item');
                listItem.textContent = ricetta.nome_ricetta;
                ricetteList.appendChild(listItem);
            });

            document.getElementById('alimentoName').querySelector('strong').textContent = alimentoNome;

            // Associa l'alimentoId al pulsante di conferma
            const confirmDeleteBtn = document.getElementById('confirmDeleteAlimentoBtn');
            confirmDeleteBtn.setAttribute('data-alimento-id', alimentoId);

            // Mostra il modal
            const confirmDeleteModal = new bootstrap.Modal(document.getElementById('confirmDeleteAlimentoModal'));
            confirmDeleteModal.show();
        })
        .catch(error => console.error('Errore nel recupero delle ricette:', error));
}

document.addEventListener('DOMContentLoaded', function() {

    // Gestisci i click sui filtri
    document.querySelectorAll('.month-filter-btn').forEach(button => {
        button.addEventListener('click', function () {
            if (button.classList.contains('btn-outline-secondary')) {
                // Primo click: selezione del mese
                button.classList.remove('btn-outline-secondary');
                button.classList.add('btn-primary');
                filterAlimentiTable();
            } else if (button.classList.contains('btn-primary')) {
                // Secondo click: esclusione del mese
                button.classList.remove('btn-primary');
                button.classList.add('btn-danger');
                filterAlimentiTable();
            } else if (button.classList.contains('btn-danger')) {
                // Terzo click: reset
                button.classList.remove('btn-danger');
                button.classList.add('btn-outline-secondary');
                filterAlimentiTable();
            }
        });
    });

    /* document.getElementById('override_macros_btn').addEventListener('click', function () {
        // Rendi i campi modificabili
        const carbsInput = document.getElementById('carboidrati_input');
        const proteinInput = document.getElementById('proteine_input');
        const fatInput = document.getElementById('grassi_input');
        const dietaInput = document.getElementById('dieta');

        carbsInput.disabled = !carbsInput.disabled; // Toggle stato abilitato/disabilitato
        proteinInput.disabled = !proteinInput.disabled;
        fatInput.disabled = !fatInput.disabled;

        // Cambia il testo del pulsante
        if (!carbsInput.disabled) {
            this.textContent = 'Lock';
            this.classList.remove('btn-secondary');
            this.classList.add('btn-danger');
            dietaInput.value = 'personalizzata';
        } else {
            this.textContent = 'Override';
            this.classList.remove('btn-danger');
            this.classList.add('btn-secondary');
        }
    }); */

    // Invoca il fetch durante il caricamento della pagina
    fetchGroupsAndPopulate();

    document.getElementById("defaultOpen").click();

    // Aggiungi listener al pulsante di conferma eliminazione nel modal
    document.getElementById('confirmDeleteAlimentoBtn').addEventListener('click', function() {
        const alimentoId = this.getAttribute('data-alimento-id');
        deleteAlimento(alimentoId);

        const confirmDeleteModal = bootstrap.Modal.getInstance(document.getElementById('confirmDeleteAlimentoModal'));
        confirmDeleteModal.hide();
    });


document.getElementById('addFoodForm').addEventListener('submit', function(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    fetch('/alimento', {
        method: 'POST',
        body: formData
    }).then(response => response.json())
      .then(data => {
          if (data.status == 'success') {
              // Chiudi il modal
              const modal = bootstrap.Modal.getInstance(document.getElementById('addFoodModal'));
              modal.hide();
              fetchAlimentiData();
              // Facoltativamente, aggiorna la pagina o i dati dinamicamente
              // location.reload();
          } else {
              // Gestisci errori, se necessario
              showAlertModal('Errore durante il salvataggio dell\'alimento');
          }
      });
});

    document.querySelector('#addRecipeModal form').addEventListener('submit', function(event) {
    event.preventDefault();

    const formData = new FormData(this);

    fetch(this.action, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Aggiorna la tabella delle ricette o ricarica i dati
            recupera_tutte_le_ricette();
            // Chiudi il modal
            $('#addRecipeModal').modal('hide');
        } else {
            console.error('Errore durante il salvataggio della ricetta:', data);
        }
    })
    .catch(error => console.error('Errore:', error));
});

    const tutorialActive = document.body.getAttribute('data-tutorial-active') === 'True';

    if (tutorialActive) {
        document.querySelectorAll('input, select, textarea, button').forEach(function(element) {
            if (!element.classList.contains('tutorial-ignore')) {
                element.disabled = true;
            }
        });

        document.querySelectorAll('.tutorial-disable').forEach(function(element) {
            element.disabled = false;
        });
    }

    // Recupera il valore salvato nel localStorage, se esiste
    const savedWeekId = localStorage.getItem('selectedWeekId');
    if (savedWeekId) {
        selectedWeekId = savedWeekId;
        // Aggiorna tutte le select con il valore salvato
        document.querySelectorAll('.week-select').forEach(sel => {
            sel.value = savedWeekId;
        });
        // Carica i dati del menu per la settimana selezionata
        loadAndUpdateMenuData();
    } else {
        updateSelectedWeek();  // Caricamento iniziale della settimana
    }

    // Event Listener per cambiare la settimana
    document.querySelectorAll('.week-select').forEach(select => {
        select.addEventListener('change', updateSelectedWeek);
    });

    // Riferimento al modal di conferma
    const confirmDeleteModal = new bootstrap.Modal(document.getElementById('confirmDeleteModal'));

    // Listener per i pulsanti di eliminazione
    document.querySelectorAll('.delete-menu-btn').forEach(button => {
        button.addEventListener('click', function() {
            confirmDeleteModal.show();
        });
    });

    document.getElementById('confirmDeleteBtn').addEventListener('click', deleteMenu);

    const form = document.getElementById('personalInfoForm');

    if (form) {
        form.addEventListener('input', calculateResults);
        form.addEventListener('submit', synchronizeFields);
    }

    if (document.getElementById("captureButton")) {
        document.getElementById("captureButton").addEventListener("click", function() {
            const weekId = selectedWeekId; // Ottieni l'ID della settimana selezionata
            const menuContainer = document.querySelector("#capture");

            // Imposta temporaneamente l'altezza del div per contenere tutto il contenuto
            menuContainer.style.height = "auto";
            menuContainer.style.maxHeight = "none";

            html2canvas(menuContainer, {
            useCORS: true,
            scale: 2, // Aumenta la risoluzione per evitare immagini sgranate
            logging: true,
            windowWidth: document.documentElement.scrollWidth,
            windowHeight: document.documentElement.scrollHeight,
            scrollY: 0 // Impedisci lo scroll
        }).then(canvas => {
                const imgData = canvas.toDataURL('image/png');

                // Ritorna l'altezza originale dopo la cattura
            menuContainer.style.height = "";
            menuContainer.style.maxHeight = "";

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
    }

    if (document.getElementById("generateMenuBtn")){
        document.getElementById("generateMenuBtn").addEventListener("click", function() {
            // Avvia la generazione del menu al click del bottone
            startMenuGeneration();
        });
    }

    if (document.getElementById("completeMenuBtn")){
        document.getElementById("completeMenuBtn").addEventListener("click", function() {
            // Avvia il completamento del menu al click del bottone
            completeMenu();
        });
    }

    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Tooltip(popoverTriggerEl);
    });


    if (document.getElementById('confirmAddMeal')) {
        document.getElementById('confirmAddMeal').addEventListener('click', function () {
            let selectedMeals = [];

            document.querySelectorAll('.meal-checkbox:checked').forEach(checkbox => {
                const mealId = checkbox.value;
                const kcal = parseFloat(checkbox.getAttribute('data-kcal')) || 0; // Leggi le kcal dall'attributo data-kcal
                selectedMeals.push({ id: mealId, kcal: kcal });
            });

            if (selectedMeals.length > 0) {
                // Ordina i pasti selezionati in base alle kcal (dal più basso al più alto)
                selectedMeals.sort((a, b) => b.kcal - a.kcal);

                // Estrai solo gli ID ordinati
                const orderedMealIds = selectedMeals.map(meal => meal.id);

                // Aggiungi le ricette ordinate al menu
                addMealsToMenu(currentDay, currentMeal, orderedMealIds);
            }

            // Chiudi il modal
            const addMealModal = bootstrap.Modal.getInstance(document.getElementById('addMealModal'));
            addMealModal.hide();
        });
    }

    // Assicurati che gli event listeners siano aggiunti dopo il caricamento dei dati nel modal
    if (document.querySelector('#editRecipeModal')){
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
    }

    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    if (document.getElementById("peso-tab")){
    document.getElementById("peso-tab").addEventListener("click", () => {
        fetch('/get_peso_data')
            .then(response => response.json())
            .then(data => {
                if (data.status == 'success'){
                    if (data.peso.length > 0) {
                        updateWeightChart(data.peso);
                    }
                }
            })
            .catch(error => console.error('Errore nel caricamento dei dati:', error));
    });
    }


    document.getElementById("ricette-tab").addEventListener("click", function() {
        recupera_tutte_le_ricette();
    });

    document.getElementById('alimenti-tab').addEventListener('click', function() {
        fetchAlimentiData();
    });


    if (document.getElementById("dieta-tab")){
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
    }

    $(document).ready(function() {
        $('#addIngredientModal').on('show.bs.modal', function(event) {
            const select = document.getElementById('ingredient-select');
            select.innerHTML = '';

            fetch('/alimenti')
                .then(response => response.json())
                .then(data => {
                    if (data.status == 'success'){
                        data.alimenti.forEach(ingredient => {
                            const option = new Option(ingredient.nome, ingredient.id);
                            select.add(option);
                        });
                    }
                })
                .catch(error => console.error('Error loading ingredients:', error));
        });
    });
});
