// ============= CONFIGURAZIONE E UTILITÀ =============
const CONFIG = {
    DEBOUNCE_DELAY: 300,
    ANIMATION_DURATION: 300,
    CACHE_DURATION: 5000,
    VALIDATION_RULES: {
        eta: { min: 10, max: 120 },
        altezza: { min: 100, max: 250 },
        peso: { min: 30, max: 300 }
    }
};

// Cache manager semplificato
class CacheManager {
    constructor(duration = CONFIG.CACHE_DURATION) {
        this.cache = new Map();
        this.duration = duration;
    }

    set(key, value) {
        this.cache.set(key, {
            value,
            timestamp: Date.now()
        });
    }

    get(key) {
        const item = this.cache.get(key);
        if (!item) return null;

        if (Date.now() - item.timestamp > this.duration) {
            this.cache.delete(key);
            return null;
        }

        return item.value;
    }

    clear() {
        this.cache.clear();
    }
}

const cache = new CacheManager();

// ============= FUNZIONI DI UTILITÀ =============
function debounce(func, wait = CONFIG.DEBOUNCE_DELAY) {
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

// Versioni sicure delle funzioni di progress
function showProgress() {
    const indicator = document.getElementById('progressIndicator');
    if (indicator) {
        indicator.classList.add('active');
    }
}

function hideProgress() {
    const indicator = document.getElementById('progressIndicator');
    if (indicator) {
        setTimeout(() => {
            indicator.classList.remove('active');
        }, CONFIG.ANIMATION_DURATION);
    }
}

// Funzione helper per elementi sicuri
function safeGetElement(id) {
    return document.getElementById(id);
}

function safeSetValue(id, value, isText = false) {
    const element = safeGetElement(id);
    if (element) {
        if (isText) {
            element.textContent = value;
        } else {
            element.value = value;
        }
    }
}

// ============= CALCOLI OTTIMIZZATI =============
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

    static calculateDeficit(deficit, sesso) {
        const deficitMap = {
            'F': { 0: 0, 1: 250, 2: 350 },
            'M': { 0: 0, 1: 350, 2: 500 }
        };
        return deficitMap[sesso]?.[deficit] || 0;
    }

    // 3.1 Calorie target dal goal
    static calcCaloriesTarget({ tdee, goal, variationPct }) {
      // variationPct è una percentuale decimale: es. -0.10, 0, +0.05
      if (goal === 'fat_loss') {
        return Math.round(tdee * (1 + variationPct)); // variationPct negativa
      }
      if (goal === 'muscle_gain') {
        return Math.round(tdee * (1 + variationPct)); // variationPct positiva
      }
      // maintenance / performance: niente variazione
      return Math.round(tdee);
    }

    // 3.2 Macro calculator (versione robusta con goal + activity)
    static calculateMacros({ calories, weightKg, goal, activity }) {
      const presets = {
        fat_loss:      { p: { mid: 2.0, min: 1.6 }, f: { mid: 0.8, min: 0.6 } },
        maintenance:   { p: { mid: 1.6, min: 1.2 }, f: { mid: 0.9, min: 0.7 } },
        muscle_gain:   { p: { mid: 1.8, min: 1.6 }, f: { mid: 1.0, min: 0.8 } },
        performance:   { p: { mid: 1.7, min: 1.5 }, f: { mid: 0.8, min: 0.6 } },
      };

      const carbFloorPerActivity = {
        sedentary: 2.0, light: 3.0, moderate: 4.0, high: 5.0, athlete: 6.0,
      };

      const P = presets[goal] ?? presets.maintenance;
      const F = presets[goal] ?? presets.maintenance;
      const carbFloor = Math.round((carbFloorPerActivity[activity] ?? 3.0) * weightKg);

      let proteine = Math.round(P.p.mid * weightKg);
      let grassi   = Math.round(F.f.mid * weightKg);
      let carboidrati = Math.round((calories - (proteine * 4 + grassi * 9)) / 4);

      // rispetta un minimo di carbo in base all'attività
      const meta = { adjustedForCarbFloor: false, caloriesTooLow: false };
      if (carboidrati < carbFloor) {
        meta.adjustedForCarbFloor = true;

        const grassiMin = Math.round(F.f.min * weightKg);
        const proteineMin = Math.round(P.p.min * weightKg);

        // libera kcal togliendo grassi prima
        let kcalShort = (carbFloor - carboidrati) * 4;
        let cutFat = Math.min(grassi - grassiMin, Math.ceil(kcalShort / 9));
        if (cutFat > 0) {
          grassi -= cutFat;
          kcalShort -= cutFat * 9;
        }
        // poi proteine se serve
        if (kcalShort > 0) {
          let cutProt = Math.min(proteine - proteineMin, Math.ceil(kcalShort / 4));
          if (cutProt > 0) {
            proteine -= cutProt;
            kcalShort -= cutProt * 4;
          }
        }
        carboidrati = Math.round((calories - (proteine * 4 + grassi * 9)) / 4);
        if (carboidrati < carbFloor) meta.caloriesTooLow = true;
      }

      // clamp
      proteine = Math.max(0, proteine);
      grassi   = Math.max(0, grassi);
      carboidrati = Math.max(0, carboidrati);

      return { proteine, grassi, carboidrati, meta };
    }
}

// ============= GESTIONE FORM =============
class FormManager {
    constructor() {
        this.form = document.getElementById('personalInfoForm');
        if (!this.form) {
            console.warn('Form personalInfoForm non trovato');
            return;
        }
        this.initEventListeners();
        this.initTooltips();
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
        ['sesso', 'tdee', 'deficit_calorico', 'attivita_fisica', 'dieta'].forEach(id => {
            const element = this.form.elements[id];
            if (element) {
                element.addEventListener('change', () => {
                    this.validateField(element);
                    this.calculate();
                });
            }
        });

        // Slider peso obiettivo
        this.initWeightSlider();

        // Form submission
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });
    }

    recalc() {
        recalcAll(); // qui chiami la funzione che ti ho scritto
    }

    initTooltips() {
        // Verifica che Bootstrap sia caricato
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(
                document.querySelectorAll('[data-bs-toggle="tooltip"]')
            );
            tooltipTriggerList.map(tooltipTriggerEl =>
                new bootstrap.Tooltip(tooltipTriggerEl)
            );
        }
    }

    initWeightSlider() {
        const slider = safeGetElement('peso_target_slider');
        const altezzaInput = this.form?.elements['altezza'];

        if (!slider || !altezzaInput) return;

        const updateSlider = () => {
            const altezza = parseFloat(altezzaInput.value);
            if (!altezza) return;

            const { min, max } = this.getHealthyWeightRange(altezza);
            slider.min = min;
            slider.max = max;

            const pesoIdeale = NutritionCalculator.calculateIdealWeight(altezza);
            slider.value = pesoIdeale;

            safeSetValue('pesoMin', `${min} kg`, true);
            safeSetValue('pesoMax', `${max} kg`, true);
            safeSetValue('pesoObiettivoValue', `${pesoIdeale} kg`, true);
            safeSetValue('peso_target_hidden', pesoIdeale);

            this.updateWeightDifference();
        };

        altezzaInput.addEventListener('input', debounce(updateSlider, CONFIG.DEBOUNCE_DELAY));

        slider.addEventListener('input', () => {
            const value = parseFloat(slider.value);
            safeSetValue('pesoObiettivoValue', `${value.toFixed(1)} kg`, true);
            safeSetValue('peso_target', value.toFixed(1));
            this.updateWeightDifference();
            this.calculate();
        });

        // Aggiorna subito all'inizio se l'altezza ha già un valore
        updateSlider();
    }

    getHealthyWeightRange(altezza) {
        const h = altezza / 100;
        return {
            min: Math.round(18.5 * h * h),
            max: Math.round(24.9 * h * h)
        };
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

    calculate() {
        if (!this.form) return;

        showProgress();

        const formData = this.getFormData();
        if (!this.isDataComplete(formData)) {
            hideProgress();
            return;
        }

        // Controlla cache
        const cacheKey = JSON.stringify(formData);
        const cachedResults = cache.get(cacheKey);

        if (cachedResults) {
            this.updateUI(cachedResults);
            hideProgress();
            return;
        }

        // Esegui calcoli
        const results = this.performCalculations(formData);

        // Salva in cache
        cache.set(cacheKey, results);

        // Aggiorna UI
        this.updateUI(results);
        hideProgress();
    }

    getFormData() {
        if (!this.form) return {};

        const slider = safeGetElement('peso_target_slider');

        return {
            sesso: this.form.elements['sesso']?.value,
            eta: parseFloat(this.form.elements['eta']?.value),
            peso: parseFloat(this.form.elements['peso']?.value),
            altezza: parseFloat(this.form.elements['altezza']?.value),
            tdee: parseFloat(this.form.elements['tdee']?.value),
            deficit: parseFloat(this.form.elements['deficit_calorico']?.value),
            attivita_fisica: parseFloat(this.form.elements['attivita_fisica']?.value),
            dieta: parseFloat(this.form.elements['dieta']?.value),
            peso_target: parseFloat(slider?.value || 0)
        };
    }

    isDataComplete(data) {
        return data.sesso && !isNaN(data.eta) && !isNaN(data.peso) &&
               !isNaN(data.altezza) && !isNaN(data.tdee) &&
               !isNaN(data.deficit) && !isNaN(data.attivita_fisica);
    }

    performCalculations(data) {
        const bmi = NutritionCalculator.calculateBMI(data.peso, data.altezza);
        const bmiCategory = NutritionCalculator.getBMICategory(bmi);
        const idealWeight = NutritionCalculator.calculateIdealWeight(data.altezza);
        const bmr = NutritionCalculator.calculateBMR(data);
        const tdee = Math.round(bmr * data.tdee);
        const deficitCal = NutritionCalculator.calculateDeficit(data.deficit, data.sesso);
        const targetCalories = Math.round((tdee - deficitCal) / 50) * 50;

        // Calcolo settimane
        let weeks = 0;
        if (data.deficit > 0 && data.peso_target < data.peso) {
            const weightToLose = data.peso - data.peso_target;
            const dailyDeficit = tdee - targetCalories;
            if (dailyDeficit > 0) {
                weeks = Math.round((weightToLose * 7700) / (dailyDeficit * 7));
            }
        }

        const macros = NutritionCalculator.calculateMacros(
            targetCalories,
            idealWeight,
            data.dieta,
            data.attivita_fisica
        );

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
    }

    animateValue(elementId, value) {
        const element = safeGetElement(elementId);
        if (!element) return;

        const current = parseInt(element.textContent) || 0;
        const increment = (value - current) / 20;
        let step = 0;

        const timer = setInterval(() => {
            step++;
            const newValue = Math.round(current + increment * step);
            element.textContent = newValue;

            if (step >= 20) {
                element.textContent = value;
                clearInterval(timer);
            }
        }, 20);
    }

    addWeeksToDate(weeks) {
        const date = new Date();
        date.setDate(date.getDate() + weeks * 7);
        return date.toLocaleDateString('it-IT', {
            month: 'long',
            year: 'numeric'
        });
    }

    async handleSubmit() {
        if (!this.validateForm()) {
            this.showValidationError();
            return;
        }

        showProgress();

        try {
            await this.submitForm();
            this.showSuccessMessage();
        } catch (error) {
            this.showErrorMessage(error);
        } finally {
            hideProgress();
        }
    }

    async submitForm() {
        if (!this.form) throw new Error('Form non trovato');

        // Sincronizza campi nascosti prima dell'invio
        const hiddenFields = [
            'bmi', 'peso_ideale', 'meta_basale', 'meta_giornaliero',
            'calorie_giornaliere', 'settimane_dieta', 'carboidrati',
            'proteine', 'grassi', 'peso_target'
        ];

        hiddenFields.forEach(field => {
            const visible = safeGetElement(field);
            const hidden = safeGetElement(`${field}_hidden`);
            if (visible && hidden) {
                hidden.value = visible.textContent || visible.value || '';
            }
        });

        const formData = new FormData(this.form);

        const response = await fetch('/salva_dati', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Errore nel salvataggio');
        }

        return response.json();
    }

    showValidationError() {
        this.showToast('Completa tutti i campi obbligatori', 'warning');
    }

    showSuccessMessage() {
        this.showToast('Profilo salvato con successo!', 'success');
    }

    showErrorMessage(error) {
        this.showToast('Errore nel salvataggio. Riprova.', 'danger');
    }

    showToast(message, type = 'info') {
        // Se usi già showAlertModal dal tuo codice esistente
        if (typeof showAlertModal === 'function') {
            showAlertModal(message);
            return;
        }

        // Altrimenti usa console.log come fallback
        console.log(`[${type.toUpperCase()}]: ${message}`);
    }

    // Metodo per caricare dati esistenti
    loadUserData(data) {
        if (!this.form || !data) return;

        Object.keys(data).forEach(key => {
            const element = this.form.elements[key];
            if (element) {
                element.value = data[key];
            }
        });

        this.calculate();
    }
}

function recalcAll() {
    // 1. Recupero i valori dal form
    const peso = parseFloat(document.querySelector('[name="peso"]').value) || 0;
    const altezza = parseFloat(document.querySelector('[name="altezza"]').value) || 0;
    const eta = parseInt(document.querySelector('[name="eta"]').value) || 0;
    const sesso = document.querySelector('[name="sesso"]').value;
    const activity = document.getElementById('tdee').value;
    const goal = document.getElementById('dieta').value;
    const variationPct = parseFloat(document.getElementById('deficit_calorico').value || '0');

    // 2. Calcolo BMR (Mifflin-St Jeor)
    let bmr = (10 * peso) + (6.25 * altezza) - (5 * eta) + (sesso === 'M' ? 5 : -161);
    document.getElementById('meta_basale').textContent = Math.round(bmr);
    document.getElementById('meta_basale_hidden').value = Math.round(bmr);

    // 3. Calcolo TDEE (fattore in base allo stile di vita)
    const activityFactors = {
        sedentary: 1.2,
        light: 1.375,
        moderate: 1.55,
        high: 1.725,
        athlete: 1.9
    };
    const tdee = bmr * (activityFactors[activity] || 1.2);
    document.getElementById('meta_giornaliero').textContent = Math.round(tdee);
    document.getElementById('meta_giornaliero_hidden').value = Math.round(tdee);

    // 4. Calorie target in base al goal e alla variazione
    const calorieTarget = NutritionCalculator.calcCaloriesTarget({ tdee, goal, variationPct });
    document.getElementById('calorie_giornaliere').textContent = calorieTarget;
    document.getElementById('calorie_giornaliere_hidden').value = calorieTarget;

    // 5. Calcolo macro
    const macros = calculateMacros({ calories: calorieTarget, weightKg: peso, goal, activity });
    document.getElementById('carboidrati_input').textContent = macros.carboidrati;
    document.getElementById('carboidrati_hidden').value = macros.carboidrati;

    document.getElementById('proteine_input').textContent = macros.proteine;
    document.getElementById('proteine_hidden').value = macros.proteine;

    document.getElementById('grassi_input').textContent = macros.grassi;
    document.getElementById('grassi_hidden').value = macros.grassi;

    // 6. (Opzionale) mostra avvisi se meta.caloriesTooLow
    if (macros.meta.caloriesTooLow) {
        console.warn("Calorie troppo basse per l'attività scelta");
        // qui potresti aggiungere un badge visivo nella UI
    }
}

// ============= INIZIALIZZAZIONE =============
// Esporta per uso globale
window.FormManager = FormManager;
window.NutritionCalculator = NutritionCalculator;