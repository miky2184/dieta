// Aggiungi eventi per i filtri stagionalità
document.querySelectorAll('.month-filter-btn').forEach(button => {
    button.addEventListener('click', function() {
        // Cicla tra tre stati: normale -> include (blu) -> exclude (rosso) -> normale
        if (this.classList.contains('btn-outline-secondary')) {
            // Stato normale -> include (blu)
            this.classList.remove('btn-outline-secondary');
            this.classList.add('btn-primary');
        } else if (this.classList.contains('btn-primary')) {
            // Include -> exclude (rosso)
            this.classList.remove('btn-primary');
            this.classList.add('btn-danger');
        } else {
            // Exclude -> normale
            this.classList.remove('btn-danger');
            this.classList.add('btn-outline-secondary');
        }
        filterAlimentiTable();
    });
});

// Inizializza tooltip
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
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
});

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

// Funzione per pulire i filtri
function cleanFiltersAlimenti() {
    // Pulisci input di testo e numerici
    document.getElementById('filter-nome-alimento').value = '';
    ['calorie', 'carbo', 'proteine', 'grassi', 'fibre', 'zucchero', 'sale'].forEach(filter => {
        document.getElementById(`filter-${filter}-min`).value = '';
        document.getElementById(`filter-${filter}-max`).value = '';
    });

    // Reset select
    document.getElementById('filter-gruppo').value = 'all';
    document.getElementById('filter-vegan').value = 'all';
    document.getElementById('filter-surgelato').value = 'all';

    // Reset bottoni stagionalità
    document.querySelectorAll('.month-filter-btn').forEach(button => {
        button.classList.remove('btn-primary', 'btn-danger');
        button.classList.add('btn-outline-secondary');
    });

    filterAlimentiTable();
}

// Placeholder per le funzioni esistenti
function sortTable(tableId, columnIndex) {
    console.log(`Sorting table ${tableId} by column ${columnIndex}`);
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
            cells[11].querySelectorAll('.btn-primary')
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

function fetchAlimentiData() {
    fetch('/alimenti')
        .then(response => response.json())
        .then(data => {
            populateAlimentiTable(data.alimenti);
        })
        .catch(error => console.error('Errore nel caricamento degli alimenti:', error));
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