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
        Object.keys(menu.day).forEach(giorno => {
            const td = document.createElement('td');
            menu.day[giorno].pasto[pasto].ricette.forEach(ricetta => {
                const div = document.createElement('div');
                div.textContent = `${ricetta.nome_ricetta} (${ricetta.qta}x)`;
                td.appendChild(div);
            });
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
            window.location.href = '/';
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

function loadRecipeData(ricettaId) {
    // Assumi che i dati siano già nella pagina o recuperarli dal server
    const recipe = document.querySelector(`input[name='nome_${ricettaId}']`).value;

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
            const ricettaData = {
                id: ricettaId
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

    var editRecipeModal = document.getElementById('editRecipeModal');
    editRecipeModal.addEventListener('hidden.bs.modal', function() {
        if (!$('#addIngredientModal').hasClass('show')) {
            window.location.href = '/';
        }
    })

    var addIngredientModal = document.getElementById('addIngredientModal');
    addIngredientModal.addEventListener('hidden.bs.modal', function() {
        window.location.href = '/';
    })

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