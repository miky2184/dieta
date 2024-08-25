
# **MenuScheduler**

**MenuScheduler** è un'applicazione web progettata per aiutare gli utenti a pianificare e gestire il proprio piano alimentare settimanale. Gli utenti possono creare, personalizzare e salvare menu settimanali, monitorare il proprio peso e gestire ricette e alimenti in modo efficace.

## **Caratteristiche Principali**

- **Autenticazione e Registrazione**: Gli utenti possono registrarsi e accedere al proprio account.
- **Gestione Menu Settimanale**: Creazione e gestione di menu settimanali con ricette personalizzabili.
- **Monitoraggio del Peso**: Registrazione e visualizzazione del peso corporeo nel tempo.
- **Gestione Ricette e Alimenti**: Aggiunta, modifica e gestione di ricette e alimenti, con opzioni per includere preferenze alimentari (vegan, carne, pesce, ecc.).
- **Generazione Automatica del Menu**: Creazione automatica del menu settimanale in base ai macronutrienti dell'utente.
- **Esportazione in PDF**: Generazione di un PDF del menu settimanale e della lista della spesa.

## **Installazione**

1. **Clona il Repository**
   ```bash
   git clone https://github.com/miky2184/dieta.git
   cd dieta
   ```

2. **Crea un Ambiente Virtuale**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Su Windows: venv\Scripts\activate
   ```

3. **Installa le Dipendenze**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura le Variabili d'Ambiente**
   Crea un file `.env` nella directory principale e aggiungi le seguenti variabili:
   ```env
   SECRET_KEY=la_tua_secret_key
   DB_USER=il_tuo_username_db
   DB_PASSWORD=la_tua_password_db
   DB_HOST=indirizzo_host_db
   DB_PORT=porta_db
   DB_NAME=nome_del_db
   WEBAPP_HOST=localhost
   WEBAPP_PORT=5000
   ```

5. **Inizializza il Database**
   ```bash
   flask db upgrade
   ```

6. **Esegui l'Applicazione**
   ```bash
   python run.py
   ```

7. **Accedi all'Applicazione**
   Apri il browser e vai all'indirizzo [http://localhost:5000](http://localhost:5000).

## **Utilizzo**

### **Dashboard**

Una volta effettuato l'accesso, l'utente verrà reindirizzato alla dashboard dove può visualizzare e gestire il proprio menu settimanale, registrare il peso e monitorare i progressi.

### **Gestione Ricette**

Gli utenti possono aggiungere, modificare o eliminare ricette. Ogni ricetta può essere classificata per tipo di pasto (colazione, pranzo, cena, ecc.) e può essere attivata o disattivata per l'inclusione automatica nei menu.

### **Generazione Menu**

L'utente può generare automaticamente un menu settimanale in base ai propri macronutrienti calcolati. Se il menu per la settimana corrente o la settimana prossima esiste già, l'applicazione genererà il menu per la settimana successiva.

### **Esportazione PDF**

L'utente può esportare il menu settimanale e la lista della spesa in formato PDF per una facile consultazione offline.

## **Struttura del Progetto**

- **app/**: Contiene il codice dell'applicazione, suddiviso in moduli come `views`, `models`, `services`, ecc.
- **templates/**: Contiene i file HTML per il rendering delle pagine.
- **static/**: Contiene file statici come CSS e JavaScript.
- **config.py**: Contiene la configurazione dell'applicazione.
- **run.py**: Il punto di ingresso principale dell'applicazione.

## **Contributi**

I contributi sono benvenuti! Se desideri contribuire, ti preghiamo di seguire questi passaggi:

1. Fai un fork del progetto.
2. Crea un nuovo branch per la tua funzione (`git checkout -b funzione-nuova`).
3. Fai le modifiche necessarie e committale (`git commit -m 'Aggiunta nuova funzione'`).
4. Pusha il branch (`git push origin funzione-nuova`).
5. Apri una Pull Request.

## **Licenza**

Questo progetto è distribuito sotto la licenza MIT. Per maggiori informazioni, consulta il file [LICENSE](LICENSE).

## **Contatti**

Per qualsiasi domanda o problema, puoi contattare il team di sviluppo all'indirizzo email: `miky2184@gmail.com`.
