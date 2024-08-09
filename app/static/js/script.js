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
        body: JSON.stringify({ ids_all_food: idsAllFood })
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

        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById("defaultOpen").click();
        });

        // Utility function to capitalize the first letter of a string
        String.prototype.capitalize = function() {
            return this.charAt(0).toUpperCase() + this.slice(1);
        }