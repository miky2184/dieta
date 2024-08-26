// app/js/auth.js
document.addEventListener('DOMContentLoaded', function() {

    document.getElementById('recipe-form').addEventListener('submit', function(event) {
        const vegan = document.getElementById('include-vegan').checked;
        const carne = document.getElementById('include-carne').checked;
        const pesce = document.getElementById('include-pesce').checked;

        if (!vegan && !carne && !pesce) {
            event.preventDefault();
            alert('Devi selezionare almeno una opzione tra le ricette.');
        }
    });

    var veganCheckbox = document.getElementById('include-vegan');
    var carneCheckbox = document.getElementById('include-carne');
    var pesceCheckbox = document.getElementById('include-pesce');

    veganCheckbox.addEventListener('change', function () {
        if (veganCheckbox.checked) {
            carneCheckbox.checked = false;
            pesceCheckbox.checked = false;
        }
    });

    carneCheckbox.addEventListener('change', function () {
        if (carneCheckbox.checked) {
            veganCheckbox.checked = false;
        }
    });

    pesceCheckbox.addEventListener('change', function () {
        if (pesceCheckbox.checked) {
            veganCheckbox.checked = false;
        }
    });

    const emailInput = document.getElementById('email');
    if (emailInput){
        let emailFeedback = emailInput.parentNode.querySelector('.invalid-feedback');
        if (!emailFeedback) {
            emailFeedback = document.createElement('div');
            emailFeedback.className = 'invalid-feedback';
            emailInput.parentNode.appendChild(emailFeedback);
        }

        emailInput.addEventListener('blur', function() {
            const email = emailInput.value;
            fetch('/check_email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({email: email}),
            })
            .then(response => response.json())
            .then(data => {
                if (data.exists) {
                    emailInput.classList.add('is-invalid');
                    emailFeedback.textContent = 'Email gia\' in uso. Inserisci una mail differente.';
                } else if (data.bad) {
                    emailInput.classList.add('is-invalid');
                    emailFeedback.textContent = 'Email in un formato errato.';
                } else {
                    emailInput.classList.remove('is-invalid');
                    emailFeedback.textContent = '';
                }
            })
            .catch(error => console.error('Errore nel controllo dell\'email:', error));
        });
    }

    const usernameInput = document.getElementById('username');
    if (usernameInput){
        let usernameFeedback = usernameInput.parentNode.querySelector('.invalid-feedback');
        if (!usernameFeedback) {
            usernameFeedback = document.createElement('div');
            usernameFeedback.className = 'invalid-feedback';
            usernameInput.parentNode.appendChild(usernameFeedback);
        }

        usernameInput.addEventListener('blur', function() {
            const username = usernameInput.value;
            fetch('/check_username', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({username: username}),
            })
            .then(response => response.json())
            .then(data => {
                if (data.exists) {
                    usernameInput.classList.add('is-invalid');
                    usernameFeedback.textContent = 'Username già in uso. Scegli un altro username.';
                } else {
                    usernameInput.classList.remove('is-invalid');
                    usernameFeedback.textContent = '';
                }
            })
            .catch(error => console.error('Errore nel controllo dell\'username:', error));
        });
    }

});
