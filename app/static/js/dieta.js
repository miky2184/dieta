// ============= CONFIGURAZIONE =============
const CONFIG = {
    CACHE_DURATION: 5 * 60 * 1000,
    DEBOUNCE_DELAY: 300,
    VALIDATION_RULES: {
        eta: { min: 10, max: 100 },
        altezza: { min: 100, max: 250 },
        peso: { min: 30, max: 300 }
    }
};

// ============= UTILITY FUNCTIONS =============
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function safeGetElement(id) {
    const element = document.getElementById(id);
    if (!element) {
        console.warn(`Elemento con ID '${id}' non trovato`);
    }
    return element;
}

function safeSetValue(id, value, asText = false) {
    const element = safeGetElement(id);
    if (element) {
        if (asText) {
            element.textContent = value;
        } else {
            element.value = value;
        }
    }
}

function showProgress() {
    const progress = document.querySelector('.progress-indicator');
    if (progress) progress.classList.add('active');
}

function hideProgress() {
    const progress = document.querySelector('.progress-indicator');
    if (progress) progress.classList.remove('active');
}

// ============= NUTRITION CALCULATOR =============
class NutritionCalculator {
    static calculateBMI(peso, altezza) {
        if (!peso || !altezza) return 0;
        return peso / Math.pow(altezza / 100, 2);
    }

    static getBMICategory(bmi) {
        if (bmi < 18.5) return { category: "Sottopeso", class: "warning" };
        if (bmi < 25) return { category: "Normopeso", class: "healthy" };
        if (bmi < 30) return { category: "Sovrappeso", class: "warning" };
        return { category: "Obeso", class: "danger" };
    }

    static calculateIdealWeight(altezza) {
        if (!altezza) return 0;
        return Math.round(21.7 * Math.pow(altezza / 100, 2));
    }

    static calculateBMR(data) {
        const { sesso, eta, peso, altezza } = data;
        if (!sesso || !eta || !peso || !altezza) return 0;

        // Formula di Mifflin-St Jeor
        if (sesso === 'M') {
            return Math.round((10 * peso) + (6.25 * altezza) - (5 * eta) + 5);
        } else {
            return Math.round((10 * peso) + (6.25 * altezza) - (5 * eta) - 161);
        }
    }

    static getTDEEMultiplier(activity) {
        const multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'high': 1.725,
            'athlete': 1.9
        };
        return multipliers[activity] || 1.2;
    }

    static calcCaloriesTarget(tdee, goal, variationPct) {
        if (goal === 'fat_loss') {
            return Math.round(tdee * (1 + variationPct));
        }
        if (goal === 'muscle_gain') {
            return Math.round(tdee * (1 + variationPct));
        }
        return Math.round(tdee);
    }

    static calculateMacros(calories, weightKg, goal, activity) {
        const presets = {
            fat_loss: { p: 2.0, f: 0.8 },
            maintenance: { p: 1.6, f: 0.9 },
            muscle_gain: { p: 1.8, f: 1.0 },
            performance: { p: 1.7, f: 0.8 }
        };

        const carbFloorPerActivity = {
            sedentary: 2.0,
            light: 3.0,
            moderate: 4.0,
            high: 5.0,
            athlete: 6.0
        };

        const preset = presets[goal] || presets.maintenance;
        const carbFloor = Math.round((carbFloorPerActivity[activity] || 3.0) * weightKg);

        let proteine = Math.round(preset.p * weightKg);
        let grassi = Math.round(preset.f * weightKg);
        let carboidrati = Math.round((calories - (proteine * 4 + grassi * 9)) / 4);

        if (carboidrati < carbFloor) {
            carboidrati = carbFloor;
            const remainingCals = calories - (carboidrati * 4);
            proteine = Math.round(preset.p * weightKg);
            grassi = Math.round((remainingCals - (proteine * 4)) / 9);
        }

        proteine = Math.max(0, proteine);
        grassi = Math.max(0, grassi);
        carboidrati = Math.max(0, carboidrati);

        return { proteine, grassi, carboidrati };
    }
}

// ============= GESTIONE FORM =============
class FormManager {
    constructor() {
        console.log('Inizializzazione FormManager...');
        this.form = document.getElementById('personalInfoForm');

        if (!this.form) {
            console.error('Form personalInfoForm non trovato!');
            return;
        }

        this.initEventListeners();
        this.initDietaChangeListener();

        // NON eseguire calcolo iniziale se i campi sono vuoti
        // Il calcolo verrà eseguito solo quando l'utente inserisce dati
    }

    initEventListeners() {
        if (!this.form) return;

        // Input numerici con validazione
        ['eta', 'altezza', 'peso'].forEach(id => {
            const element = this.form.elements[id];
            if (element) {
                element.addEventListener('input', debounce(() => {
                    this.validateField(element);
                    this.calculate();
                }, CONFIG.DEBOUNCE_DELAY));
            }
        });

        // Select con calcolo immediato
        ['sesso', 'tdee', 'attivita_fisica'].forEach(id => {
            const element = this.form.elements[id];
            if (element) {
                element.addEventListener('change', () => {
                    this.calculate();
                });
            }
        });

        // Gestione speciale per deficit_calorico
        const deficitElement = this.form.elements['deficit_calorico'];
        if (deficitElement) {
            deficitElement.addEventListener('change', () => {
                this.calculate();
            });
        }

        // Submit form
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            if (this.validateForm()) {
                this.submitForm();
            }
        });

        // Peso target slider
        const slider = safeGetElement('peso_target_slider');
        if (slider) {
            slider.addEventListener('input', debounce(() => {
                const value = parseFloat(slider.value);
                safeSetValue('pesoObiettivoValue', `${value} kg`, true);
                safeSetValue('peso_target_hidden', value);
                this.updateWeightDifference();
                this.calculate();
            }, 50));
        }
    }

    initDietaChangeListener() {
        const dietaSelect = this.form.elements['dieta'];
        const deficitSelect = this.form.elements['deficit_calorico'];

        if (dietaSelect && deficitSelect) {
            dietaSelect.addEventListener('change', () => {
                const goal = dietaSelect.value;

                // Svuota le opzioni esistenti
                deficitSelect.innerHTML = '';

                // Aggiungi opzioni in base all'obiettivo
                if (goal === 'fat_loss') {
                    deficitSelect.innerHTML = `
                        <option value="-0.10">Moderato (-10%)</option>
                        <option value="-0.15" selected>Standard (-15%)</option>
                        <option value="-0.20">Aggressivo (-20%)</option>
                        <option value="-0.25">Molto Aggressivo (-25%)</option>
                    `;
                } else if (goal === 'muscle_gain') {
                    deficitSelect.innerHTML = `
                        <option value="0.05">Lean Bulk (+5%)</option>
                        <option value="0.10" selected>Standard (+10%)</option>
                        <option value="0.15">Moderato (+15%)</option>
                        <option value="0.20">Aggressivo (+20%)</option>
                    `;
                } else {
                    // maintenance o performance
                    deficitSelect.innerHTML = `
                        <option value="0" selected>Mantenimento (0%)</option>
                    `;
                }

                // Ricalcola con il nuovo valore
                this.calculate();
            });
        }
    }

    getFormData() {
        if (!this.form) return {};

        const slider = safeGetElement('peso_target_slider');

        return {
            sesso: this.form.elements['sesso']?.value,
            eta: parseFloat(this.form.elements['eta']?.value),
            peso: parseFloat(this.form.elements['peso']?.value),
            altezza: parseFloat(this.form.elements['altezza']?.value),
            tdee: this.form.elements['tdee']?.value,
            deficit_calorico: parseFloat(this.form.elements['deficit_calorico']?.value),
            attivita_fisica: this.form.elements['attivita_fisica']?.value,
            dieta: this.form.elements['dieta']?.value,
            peso_target: parseFloat(slider?.value || 0)
        };
    }

    isDataComplete(data) {
        // Verifica solo i campi essenziali per il calcolo
        return data.sesso &&
               !isNaN(data.eta) && data.eta > 0 &&
               !isNaN(data.peso) && data.peso > 0 &&
               !isNaN(data.altezza) && data.altezza > 0 &&
               data.tdee &&
               data.attivita_fisica &&
               data.dieta &&
               !isNaN(data.deficit_calorico);
    }

    performCalculations(data) {
        // 1. Calcolo BMI
        const bmi = NutritionCalculator.calculateBMI(data.peso, data.altezza);
        const bmiCategory = NutritionCalculator.getBMICategory(bmi);
        const idealWeight = NutritionCalculator.calculateIdealWeight(data.altezza);

        // 2. Calcolo BMR
        const bmr = NutritionCalculator.calculateBMR(data);

        // 3. Calcolo TDEE
        const tdeeMultiplier = NutritionCalculator.getTDEEMultiplier(data.tdee);
        const tdee = Math.round(bmr * tdeeMultiplier);

        // 4. Calcolo calorie target con variazione percentuale
        const targetCalories = NutritionCalculator.calcCaloriesTarget(tdee, data.dieta, data.deficit_calorico);

        // 5. Calcolo macronutrienti
        const macros = NutritionCalculator.calculateMacros(
            targetCalories,
            data.peso,
            data.dieta,
            data.attivita_fisica
        );

        // 6. Calcolo settimane (se necessario)
        let weeks = 0;
        if (data.peso_target && data.peso_target !== data.peso) {
            const weightDiff = Math.abs(data.peso - data.peso_target);
            const weeklyChange = data.dieta === 'fat_loss' ? 0.5 : 0.25;
            weeks = Math.round(weightDiff / weeklyChange);
        }

        return {
            bmi: bmi.toFixed(1),
            bmiCategory,
            idealWeight,
            bmr,
            tdee,
            targetCalories,
            weeks,
            ...macros
        };
    }

    updateUI(results) {
        // Aggiorna BMI
        safeSetValue('bmi', results.bmi, true);
        safeSetValue('bmi_hidden', results.bmi);

        // Aggiorna indicatore BMI
        const bmiIndicator = safeGetElement('bmiIndicator');
        const bmiCard = safeGetElement('bmiCard');

        if (bmiIndicator) {
            bmiIndicator.textContent = results.bmiCategory.category;
            bmiIndicator.className = `bmi-indicator ${results.bmiCategory.class}`;
            bmiIndicator.style.display = 'inline-block';
        }

        if (bmiCard) {
            bmiCard.className = `result-card ${results.bmiCategory.class}`;
        }

        // Aggiorna altri valori
        safeSetValue('peso_ideale', results.idealWeight, true);
        safeSetValue('peso_ideale_hidden', results.idealWeight);

        safeSetValue('meta_basale', results.bmr, true);
        safeSetValue('meta_basale_hidden', results.bmr);

        safeSetValue('meta_giornaliero', results.tdee, true);
        safeSetValue('meta_giornaliero_hidden', results.tdee);

        safeSetValue('calorie_giornaliere', results.targetCalories, true);
        safeSetValue('calorie_giornaliere_hidden', results.targetCalories);

        // Settimane
        const weeksElement = safeGetElement('settimane_dieta');
        if (weeksElement) {
            if (results.weeks > 0) {
                const endDate = this.addWeeksToDate(results.weeks);
                weeksElement.textContent = `${results.weeks} settimane (fino a ${endDate})`;
                safeSetValue('settimane_dieta_hidden', results.weeks);
            } else {
                weeksElement.textContent = 'Mantenimento';
                safeSetValue('settimane_dieta_hidden', '0');
            }
        }

        // Macronutrienti
        this.animateValue('carboidrati_input', results.carboidrati);
        this.animateValue('proteine_input', results.proteine);
        this.animateValue('grassi_input', results.grassi);

        safeSetValue('carboidrati_hidden', results.carboidrati);
        safeSetValue('proteine_hidden', results.proteine);
        safeSetValue('grassi_hidden', results.grassi);

        // Calorie per macro
        safeSetValue('carbo_kcal', results.carboidrati * 4, true);
        safeSetValue('prot_kcal', results.proteine * 4, true);
        safeSetValue('grassi_kcal', results.grassi * 9, true);

        // Inizializza slider peso se necessario
        this.initWeightSlider();
    }

    animateValue(id, value) {
        const element = safeGetElement(id);
        if (!element) return;

        const current = parseInt(element.textContent) || 0;
        const duration = 500;
        const startTime = Date.now();

        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const newValue = Math.round(current + (value - current) * progress);

            element.textContent = newValue;

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        animate();
    }

    addWeeksToDate(weeks) {
        const date = new Date();
        date.setDate(date.getDate() + (weeks * 7));
        const months = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"];
        return `${months[date.getMonth()]} ${date.getFullYear()}`;
    }

    calculate() {
        if (!this.form) return;

        showProgress();

        const formData = this.getFormData();
        if (!this.isDataComplete(formData)) {
            hideProgress();
            return;
        }

        // Esegui calcoli
        const results = this.performCalculations(formData);

        // Aggiorna UI
        this.updateUI(results);
        hideProgress();
    }

    validateField(element) {
        if (!element) return false;

        const value = element.value;
        const name = element.name;
        let isValid = true;

        // Validazione per campi numerici
        if (element.type === 'number') {
            const numValue = parseFloat(value);
            const rules = CONFIG.VALIDATION_RULES[name];

            if (rules) {
                isValid = !isNaN(numValue) && numValue >= rules.min && numValue <= rules.max;
            }
        }

        // Validazione per select
        if (element.tagName === 'SELECT') {
            isValid = value && value !== '';
        }

        // Applica classi di validazione
        element.classList.toggle('is-valid', isValid && value !== '');
        element.classList.toggle('is-invalid', !isValid && value !== '');

        return isValid;
    }

    validateForm() {
        if (!this.form) return false;

        const requiredFields = ['nome', 'cognome', 'sesso', 'eta', 'altezza', 'peso', 'tdee', 'deficit_calorico', 'attivita_fisica', 'dieta'];
        let isValid = true;

        requiredFields.forEach(fieldName => {
            const element = this.form.elements[fieldName];
            if (element) {
                const fieldValid = this.validateField(element);
                isValid = isValid && fieldValid;
            }
        });

        return isValid;
    }

    async submitForm() {
        if (!this.validateForm()) {
            alert('Compila tutti i campi richiesti');
            return;
        }

        try {
            const formData = new FormData(this.form);
            const response = await fetch('/salva_dati', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                alert('Dati salvati con successo!');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 2000);
            } else {
                throw new Error('Errore nel salvataggio');
            }
        } catch (error) {
            console.error('Errore:', error);
            alert('Errore nel salvataggio. Riprova.');
        }
    }

    updateWeightDifference() {
        const pesoInput = this.form?.elements['peso'];
        const slider = safeGetElement('peso_target_slider');

        if (!pesoInput || !slider) return;

        const pesoAttuale = parseFloat(pesoInput.value);
        const pesoObiettivo = parseFloat(slider.value);

        if (!pesoAttuale || !pesoObiettivo) return;

        const diff = pesoObiettivo - pesoAttuale;
        const diffElement = safeGetElement('pesoDifferenza');

        if (!diffElement) return;

        if (Math.abs(diff) < 0.5) {
            diffElement.textContent = '✓ Peso di mantenimento';
            diffElement.className = 'text-success';
        } else if (diff < 0) {
            diffElement.textContent = `↓ ${Math.abs(diff).toFixed(1)} kg da perdere`;
            diffElement.className = 'text-warning';
        } else {
            diffElement.textContent = `↑ ${diff.toFixed(1)} kg da guadagnare`;
            diffElement.className = 'text-info';
        }
    }

    initWeightSlider() {
        const pesoInput = this.form?.elements['peso'];
        const altezzaInput = this.form?.elements['altezza'];
        const slider = safeGetElement('peso_target_slider');

        if (!pesoInput || !altezzaInput || !slider) return;

        const peso = parseFloat(pesoInput.value);
        const altezza = parseFloat(altezzaInput.value);

        if (!peso || !altezza) return;

        const idealWeight = NutritionCalculator.calculateIdealWeight(altezza);
        const minWeight = Math.max(30, peso - 30);
        const maxWeight = Math.min(peso + 30, 200);

        slider.min = minWeight;
        slider.max = maxWeight;
        slider.value = Math.min(Math.max(idealWeight, minWeight), maxWeight);
        slider.step = 0.5;

        safeSetValue('pesoMin', `${minWeight} kg`, true);
        safeSetValue('pesoMax', `${maxWeight} kg`, true);
        safeSetValue('pesoObiettivoValue', `${slider.value} kg`, true);
        safeSetValue('peso_target_hidden', slider.value);

        this.updateWeightDifference();
    }

    // Metodo per caricare dati esistenti
    loadUserData(data) {
        if (!this.form || !data) return;

        console.log('Caricamento dati utente:', data);

        // Carica i dati nei campi del form
        Object.keys(data).forEach(key => {
            const element = this.form.elements[key];
            if (element) {
                element.value = data[key];
                console.log(`Campo ${key} impostato a:`, data[key]);
            }
        });

        // Trigger change event per dieta per impostare correttamente le opzioni di deficit
        const dietaElement = this.form.elements['dieta'];
        if (dietaElement) {
            dietaElement.dispatchEvent(new Event('change'));
        }

        // Esegui calcolo con i dati caricati
        setTimeout(() => {
            this.calculate();
        }, 100);
    }
}

// ============= INIZIALIZZAZIONE =============
document.addEventListener('DOMContentLoaded', function() {
    console.log('Inizializzazione FormManager...');

    // Crea istanza del FormManager
    const formManager = new FormManager();

    // Esporta per uso globale
    window.formManager = formManager;
    window.FormManager = FormManager;
    window.NutritionCalculator = NutritionCalculator;

    // Se ci sono dati utente preesistenti, caricali
    if (typeof userData !== 'undefined' && userData) {
        console.log('Caricamento dati utente esistenti...');
        formManager.loadUserData(userData);
    }

    console.log('Inizializzazione completata!');
});

// Funzione globale per ricalcolo (retrocompatibilità)
window.calculateResults = function() {
    if (window.formManager) {
        window.formManager.calculate();
    }
};