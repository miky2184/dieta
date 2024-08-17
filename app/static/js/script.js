function openTab(evt, tabName) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
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
    ['colazione', 'spuntino_mattina', 'pranzo', 'spuntino_pomeriggio', 'cena'].forEach(pasto => {
        const tr = document.createElement('tr');
        const tdPasto = document.createElement('td');
        tdPasto.textContent = pasto.replace('_', ' ').capitalize();
        tr.appendChild(tdPasto);
        ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato', 'domenica'].forEach(giorno => {
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
            window.location.href = '/';
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
    const calorieFilter = document.getElementById('filter-calorie').value.toLowerCase();
    const carboFilter = document.getElementById('filter-carbo').value.toLowerCase();
    const proteineFilter = document.getElementById('filter-proteine').value.toLowerCase();
    const grassiFilter = document.getElementById('filter-grassi').value.toLowerCase();

    const table = document.querySelector('.table tbody');
    const rows = table.getElementsByTagName('tr');

    for (let i = 0; i < rows.length; i++) {
        const cells = rows[i].getElementsByTagName('td');
        const nomeCell = cells[0].textContent.toLowerCase();
        const calorieCell = cells[1].textContent.toLowerCase();
        const carboCell = cells[2].textContent.toLowerCase();
        const proteineCell = cells[3].textContent.toLowerCase();
        const grassiCell = cells[4].textContent.toLowerCase();

        if (nomeCell.includes(nomeFilter) &&
            proteineCell.includes(calorieFilter) &&
            carboCell.includes(carboFilter) &&
            proteineCell.includes(proteineFilter) &&
            grassiCell.includes(grassiFilter)) {
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

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById("defaultOpen").click();
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
            const ricettaAttiva = this.getAttribute('data-ricetta-attiva');
            const ricettaData = {
                id: ricettaId,
                attiva: ricettaAttiva
            };
            toggleStatusRicetta(ricettaData);
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

    /*var editRecipeModal = document.getElementById('editRecipeModal');
    editRecipeModal.addEventListener('hidden.bs.modal', function() {
        if (!$('#addIngredientModal').hasClass('show')) {
            window.location.href = '/';
        }
    })*/

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

});

// Utility function to capitalize the first letter of a string
String.prototype.capitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
}

$(document).ready(function() {
    // Il tuo codice che utilizza jQuery va qui
    $('#addIngredientModal').on('show.bs.modal', function(event) {
        // Pulisci il vecchio contenuto
        const select = document.getElementById('ingredient-select');
        select.innerHTML = '';

        // Carica l'elenco degli ingredienti
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