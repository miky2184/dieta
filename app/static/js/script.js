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
            if (menu.day[giorno].pasto[pasto].ricette && menu.day[giorno].pasto[pasto].ricette.length > 0){
                menu.day[giorno].pasto[pasto].ricette.forEach(ricetta => {
                    const div = document.createElement('div');
                    div.textContent = `${ricetta.nome_ricetta} (${ricetta.qta}x)`;
                    td.appendChild(div);
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
            attivaMatch)
        {
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
            console.log('Success:', data.message);
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
        .then(data => {
            console.log('Success:', data.message);
        })
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
        .then(data => {
            console.log('Success:', data.message);
        })
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
    document.querySelector('[name="eta"]').value = data.eta || '';
    document.querySelector('[name="altezza"]').value = data.altezza || '';
    document.querySelector('[name="peso"]').value = data.peso || '';
    document.getElementById('tdee').value = data.tdee || '';
    console.log('Set TDEE to:', data.tdee);
    document.getElementById('deficit_calorico').value = data.deficit_calorico || '';
    console.log('Set TDEE to:', data.deficit_calorico);
    document.getElementById('bmi').value = data.bmi || '';
    document.getElementById('peso_ideale').value = data.peso_ideale || '';
    document.getElementById('meta_basale').value = data.meta_basale || '';
    document.getElementById('meta_giornaliero').value = data.meta_giornaliero || '';
    document.getElementById('calorie_giornaliere').value = data.calorie_giornaliere || '';
    document.getElementById('calorie_settimanali').value = data.calorie_settimanali || '';
    document.getElementById('carboidrati_input').value = data.carboidrati || '';
    document.getElementById('proteine_input').value = data.proteine || '';
    document.getElementById('grassi_input').value = data.grassi || '';
}

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById("defaultOpen").click();

    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
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
        let bmi = (data.peso / Math.pow(data.altezza/100, 2)).toFixed(1); // esempio di calcolo del BMI, con un'altezza fissa
        let idealWeight;
        let formulaLorenz;
        let formulaBroca;
        let formulaBerthean;
        let formulaKeys;
        if (data.altezza > 0) {
            if (data.eta > 0) {
            if (data.sesso === 'M') {
                formulaLorenz = data.altezza - 100 - (data.altezza - 150)/4;
                formulaBroca = data.altezza - 100;
                formulaBerthean = 0.8 * (data.altezza - 100) + data.eta/2;
                formulaKeys = 22.1 * Math.pow(data.altezza / 100, 2);
            } else if (data.sesso === 'F') {
                formulaLorenz = data.altezza - 100 - (data.altezza - 150)/2;
                formulaBroca = data.altezza - 104;
                formulaBerthean = 0.8 * (data.altezza - 100) + data.eta/2;
                formulaKeys = 20.6 * Math.pow(data.altezza / 100, 2);
            }
            }
        }

        idealWeight = ((formulaLorenz + formulaBroca + formulaBerthean + formulaKeys)/4).toFixed(0)

        let harrisBenedict;
        let mifflinStJeor;

        if (data.sesso === 'M') {
            harrisBenedict = 88.362 + (13.397 * data.peso) + (4.799 * data.altezza) - (5.677 * data.eta);
            mifflinStJeor = 10 * data.peso + 6.25 * data.altezza - 5 * data.eta + 5;
        } else if (data.sesso === 'F') {
            harrisBenedict = 47.593+(9.247*data.peso)+(3.098*data.altezza)- (4,330*data.eta) ;
            mifflinStJeor = 10 * data.peso + 6.25 * data.altezza - 5 * data.eta -161;
        }

        let metaBasaleValue = ((harrisBenedict + mifflinStJeor)/2).toFixed(0);

        let metaDailyValue = (metaBasaleValue * data.tdee).toFixed(0);

        let calorieGiornaliereValue = ((metaDailyValue - (metaDailyValue * data.deficit/100))).toFixed(0);

        let calorieSettimanaliValue = (calorieGiornaliereValue * 7).toFixed(0);

        let carboidratiValue = (calorieGiornaliereValue * 0.6 / 4).toFixed(0);
        let proteineValue = (calorieGiornaliereValue * 0.15 / 4).toFixed(0);;
        let grassiValue = (calorieGiornaliereValue * 0.25 / 9).toFixed(0);;


        if (isNaN(bmi)) {
            bmi = 0;  // Imposta un valore di default o gestisci l'errore come necessario
        }

        if (isNaN(idealWeight)) {
            idealWeight = 0;  // Imposta un valore di default o gestisci l'errore come necessario
        }

        if (isNaN(metaBasaleValue)) {
            metaBasaleValue = 0;  // Imposta un valore di default o gestisci l'errore come necessario
        }

        if (isNaN(metaDailyValue)) {
            metaDailyValue = 0;  // Imposta un valore di default o gestisci l'errore come necessario
        }

        if (isNaN(calorieGiornaliereValue)) {
            calorieGiornaliereValue = 0;  // Imposta un valore di default o gestisci l'errore come necessario
        }

        if (isNaN(calorieSettimanaliValue)) {
            calorieSettimanaliValue = 0;  // Imposta un valore di default o gestisci l'errore come necessario
        }

        if (isNaN(carboidratiValue)) {
            carboidratiValue = 0;  // Imposta un valore di default o gestisci l'errore come necessario
        }

        if (isNaN(proteineValue)) {
            proteineValue = 0;  // Imposta un valore di default o gestisci l'errore come necessario
        }

        if (isNaN(grassiValue)) {
            grassiValue = 0;  // Imposta un valore di default o gestisci l'errore come necessario
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

    form.addEventListener('input', calculateResults);

    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
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
        .then(data => {
        })
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
            body: JSON.stringify({ id: alimentoId })
        })
        .then(response => response.json())
        .then(data => {
            window.location.reload(); // Ricarica la pagina per aggiornare la lista
        })
        .catch((error) => {
            console.error('Errore:', error);
        });
    }
});

// Utility function to capitalize the first letter of a string
function capitalize(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

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

let selectedWeekId = null;

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

function renderMenuEditor(data) {
    const menuEditor = document.getElementById("menuEditor");
    menuEditor.innerHTML = ''; // Pulisce l'editor
    const menu = data.menu;

    const days = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato', 'domenica'];
    const meals = ['colazione', 'spuntino_mattina', 'pranzo', 'spuntino_pomeriggio', 'cena'];

    days.forEach(day => {
        const remaining = data.remaining_macronutrients[day];

        const dayContainer = document.createElement('div');
        dayContainer.classList.add('day-container');
        const dayTitle = document.createElement('h4');
        dayTitle.textContent = `${capitalize(day)} - Calorie rimanenti: ${remaining.kcal.toFixed(2)}, Carboidrati: ${remaining.carboidrati.toFixed(2)}g, Proteine: ${remaining.proteine.toFixed(2)}g, Grassi: ${remaining.grassi.toFixed(2)}g`;
        dayContainer.appendChild(dayTitle);

        meals.forEach(meal => {
            const mealContainer = document.createElement('div');
            mealContainer.classList.add('meal-container');
            const mealTitle = document.createElement('h5');
            mealTitle.textContent = capitalize(meal);
            mealContainer.appendChild(mealTitle);

            if (menu.day[day].pasto[meal].ricette.length > 0) {
                menu.day[day].pasto[meal].ricette.forEach(ricetta => {
                    const ricettaDiv = document.createElement('div');
                    const dynamicId = `meal-${ricetta.id}-${day}-${meal}`;
                    ricettaDiv.id = dynamicId;
                    ricettaDiv.classList.add('ricetta');
                    ricettaDiv.innerHTML = `
                        <input hidden type="text" class="form-control" value="${ricetta.id}">
                        <input type="text" class="form-control" value="${ricetta.nome_ricetta}" readonly>
                        <input type="number" class="form-control" value="${ricetta.qta}" min="0.1" step="0.1" onchange="updateMealQuantity('${day}', '${meal}', '${ricetta.id}', this.value)">
                        <button class="btn btn-danger btn-sm" onclick="removeMeal('${day}', '${meal}', '${ricetta.id}')">Rimuovi</button>
                    `;
                    mealContainer.appendChild(ricettaDiv);
                });
            }

            const addMealBtn = document.createElement('button');
            addMealBtn.textContent = "Aggiungi Ricetta";
            addMealBtn.classList.add('btn', 'btn-success', 'btn-sm');
            addMealBtn.onclick = function() {
                addNewMeal(day, meal);
            };
            mealContainer.appendChild(addMealBtn);

            dayContainer.appendChild(mealContainer);
        });

        menuEditor.appendChild(dayContainer);
    });
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
        if (data.status === 'success') {
            aggiornaMacronutrientiRimanenti(data.remaining_macronutrienti);
        }
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
        if (data.status === 'success') {
            // Rimuovi il pasto dalla visualizzazione
            document.getElementById(`meal-${mealId}-${day}-${meal}`).remove();

            // Aggiorna i macronutrienti rimanenti nella visualizzazione
            aggiornaMacronutrientiRimanenti(data.remaining_macronutrienti);
        }
    })
    .catch(error => console.error('Error:', error));
}


let currentDay = '';
let currentMeal = '';

function addNewMeal(day, meal) {
    currentDay = day;
    currentMeal = meal;

    // Fetch delle ricette disponibili per quel pasto
    fetch(`/get_available_meals?meal=${meal}`)
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
        if (data.status === 'success') {
            // Aggiorna la vista del menu
            aggiornaTabellaMenu(data.menu);
            // Aggiorna i macronutrienti rimanenti
            aggiornaMacronutrientiRimanenti(data.remaining_macronutrienti);
        }
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
        body: JSON.stringify({ date: date, weight: weight })
    })
    .then(response => response.json())
    .then(data => {
        updateWeightChart(data); // Aggiorna il grafico dopo l'invio
    })
    .catch(error => console.error('Errore nel salvataggio del peso:', error));
}

var myChart;

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