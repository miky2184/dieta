// ============= VERSIONE DEBUG CON LOGGING =============
console.log('🚀 dieta.js caricato');

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
        console.warn(`⚠️ Elemento con ID '${id}' non trovato`);
    }
    return element;
}

function safeSetValue(id, value, asText = false) {
    const element = safeGetElement(id);
    if (element) {
        if (asText) {
            element.textContent = value;
            console.log(`✅ Aggiornato testo ${id}: ${value}`);
        } else {
            element.value = value;
            console.log(`✅ Aggiornato valore ${id}: ${value}`);
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
        console.log(`📊 Calcolo BMI: peso=${peso}, altezza=${altezza}`);
        if (!peso || !altezza) return 0;
        const bmi = peso / Math.pow(altezza / 100, 2);
        console.log(`📊 BMI calcolato: ${bmi}`);
        return bmi;
    }

    static getBMICategory(bmi) {
        if (bmi < 18.5) return { category: "Sottopeso", class: "warning" };
        if (bmi < 25) return { category: "Normopeso", class: "healthy" };
        if (bmi < 30) return { category: "Sovrappeso", class: "warning" };
        return { category: "Obeso", class: "danger" };
    }

    static calculateIdealWeight(altezza) {
        if (!altezza) return 0;
        const ideal = Math.round(21.7 * Math.pow(altezza / 100, 2));
        console.log(`⚖️ Peso ideale calcolato: ${ideal} kg`);
        return ideal;
    }

    static calculateBMR(data) {
        const { sesso, eta, peso, altezza } = data;
        console.log(`🔥 Calcolo BMR:`, data);
        if (!sesso || !eta || !peso || !altezza) {
            console.warn('⚠️ Dati incompleti per BMR');
            return 0;
        }

        let bmr;
        if (sesso === 'M') {
            bmr = Math.round((10 * peso) + (6.25 * altezza) - (5 * eta) + 5);
        } else {
            bmr = Math.round((10 * peso) + (6.25 * altezza) - (5 * eta) - 161);
        }
        console.log(`🔥 BMR calcolato: ${bmr} kcal`);
        return bmr;
    }

    static getTDEEMultiplier(activity) {
        const multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'high': 1.725,
            'athlete': 1.9
        };
        const mult = multipliers[activity] || 1.2;
        console.log(`🏃 Moltiplicatore TDEE per ${activity}: ${mult}`);
        return mult;
    }

    static calcCaloriesTarget(tdee, goal, variationPct) {
        console.log(`🎯 Calcolo calorie target: TDEE=${tdee}, goal=${goal}, variazione=${variationPct}`);
        let target;
        if (goal === 'fat_loss') {
            target = Math.round(tdee * (1 + variationPct));
        } else if (goal === 'muscle_gain') {
            target = Math.round(tdee * (1 + variationPct));
        } else {
            target = Math.round(tdee);
        }
        console.log(`🎯 Calorie target: ${target} kcal`);
        return target;
    }

    static calculateMacros(calories, weightKg, goal, activity) {
        console.log(`🥗 Calcolo macro: cal=${calories}, peso=${weightKg}, goal=${goal}, activity=${activity}`);

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

        console.log(`🥗 Macro calcolati: P=${proteine}g, C=${carboidrati}g, F=${grassi}g`);
        return { proteine, grassi, carboidrati };
    }
}

// ============= GESTIONE FORM =============
class FormManager {
    constructor() {
        console.log('🔧 Inizializzazione FormManager...');
        this.form = document.getElementById('personalInfoForm');

        if (!this.form) {
            console.error('❌ Form personalInfoForm non trovato!');
            return;
        }

        console.log('✅ Form trovato');
        this.initEventListeners();
        this.initDietaChangeListener();

        // Calcolo iniziale dopo breve delay
        setTimeout(() => {
            console.log('⏱️ Esecuzione calcolo iniziale...');
            this.calculate();
        }, 100);
    }

    initEventListeners() {
        if (!this.form) return;
        console.log('🎧 Aggiunta event listeners...');

        // Input numerici
        ['eta', 'altezza', 'peso'].forEach(id => {
            const element = this.form.elements[id];
            if (element) {
                console.log(`✅ Listener aggiunto per ${id}`);
                element.addEventListener('input', debounce(() => {
                    console.log(`📝 Input cambiato: ${id} = ${element.value}`);
                    this.validateField(element);
                    this.calculate();
                }, CONFIG.DEBOUNCE_DELAY));
            } else {
                console.warn(`⚠️ Elemento ${id} non trovato`);
            }
        });

        // Select elements
        ['sesso', 'tdee', 'attivita_fisica'].forEach(id => {
            const element = this.form.elements[id];
            if (element) {
                console.log(`✅ Listener aggiunto per ${id}`);
                element.addEventListener('change', () => {
                    console.log(`📝 Select cambiato: ${id} = ${element.value}`);
                    this.calculate();
                });
            } else {
                console.warn(`⚠️ Elemento ${id} non trovato`);
            }
        });

        // Deficit calorico
        const deficitElement = this.form.elements['deficit_calorico'];
        if (deficitElement) {
            console.log('✅ Listener aggiunto per deficit_calorico');
            deficitElement.addEventListener('change', () => {
                console.log(`📝 Deficit cambiato: ${deficitElement.value}`);
                this.calculate();
            });
        } else {
            console.warn('⚠️ Elemento deficit_calorico non trovato');
        }

        // Submit form
        this.form.addEventListener('submit', (e) => {
            console.log('📤 Form submit intercettato');
            e.preventDefault();
            if (this.validateForm()) {
                this.submitForm();
            }
        });

        // Peso target slider
        const slider = safeGetElement('peso_target_slider');
        if (slider) {
            console.log('✅ Listener aggiunto per slider peso');
            slider.addEventListener('input', debounce(() => {
                const value = parseFloat(slider.value);
                console.log(`📝 Slider peso: ${value}`);
                safeSetValue('pesoObiettivoValue', `${value} kg`, true);
                safeSetValue('peso_target_hidden', value);
                this.updateWeightDifference();
                this.calculate();
            }, 50));
        } else {
            console.warn('⚠️ Slider peso non trovato');
        }
    }

    initDietaChangeListener() {
        const dietaSelect = this.form.elements['dieta'];
        const deficitSelect = this.form.elements['deficit_calorico'];

        if (dietaSelect && deficitSelect) {
            console.log('✅ Listener aggiunto per cambio dieta/obiettivo');
            dietaSelect.addEventListener('change', () => {
                const goal = dietaSelect.value;
                console.log(`🎯 Obiettivo cambiato: ${goal}`);

                deficitSelect.innerHTML = '';

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
                    deficitSelect.innerHTML = `
                        <option value="0" selected>Mantenimento (0%)</option>
                    `;
                }

                console.log(`📝 Opzioni deficit aggiornate per ${goal}`);
                this.calculate();
            });
        } else {
            console.warn('⚠️ Select dieta o deficit non trovati');
        }
    }

    getFormData() {
        if (!this.form) return {};

        const slider = safeGetElement('peso_target_slider');

        const data = {
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

        console.log('📋 Dati form raccolti:', data);
        return data;
    }

    isDataComplete(data) {
        const complete = data.sesso && !isNaN(data.eta) && !isNaN(data.peso) &&
               !isNaN(data.altezza) && data.tdee && data.attivita_fisica && data.dieta;

        if (!complete) {
            console.warn('⚠️ Dati incompleti:', {
                sesso: data.sesso,
                eta: !isNaN(data.eta),
                peso: !isNaN(data.peso),
                altezza: !isNaN(data.altezza),
                tdee: data.tdee,
                attivita_fisica: data.attivita_fisica,
                dieta: data.dieta
            });
        }

        return complete;
    }

    performCalculations(data) {
        console.log('🧮 Inizio calcoli con dati:', data);

        // 1. BMI
        const bmi = NutritionCalculator.calculateBMI(data.peso, data.altezza);
        const bmiCategory = NutritionCalculator.getBMICategory(bmi);
        const idealWeight = NutritionCalculator.calculateIdealWeight(data.altezza);

        // 2. BMR
        const bmr = NutritionCalculator.calculateBMR(data);

        // 3. TDEE
        const tdeeMultiplier = NutritionCalculator.getTDEEMultiplier(data.tdee);
        const tdee = Math.round(bmr * tdeeMultiplier);
        console.log(`💪 TDEE: ${bmr} × ${tdeeMultiplier} = ${tdee}`);

        // 4. Calorie target
        const targetCalories = NutritionCalculator.calcCaloriesTarget(tdee, data.dieta, data.deficit_calorico);

        // 5. Macronutrienti
        const macros = NutritionCalculator.calculateMacros(
            targetCalories,
            data.peso,
            data.dieta,
            data.attivita_fisica
        );

        // 6. Settimane
        let weeks = 0;
        if (data.peso_target && data.peso_target !== data.peso) {
            const weightDiff = Math.abs(data.peso - data.peso_target);
            const weeklyChange = data.dieta === 'fat_loss' ? 0.5 : 0.25;
            weeks = Math.round(weightDiff / weeklyChange);
        }

        const results = {
            bmi: bmi.toFixed(1),
            bmiCategory,
            idealWeight,
            bmr,
            tdee,
            targetCalories,
            weeks,
            ...macros
        };

        console.log('✅ Risultati calcolati:', results);
        return results;
    }

    updateUI(results) {
        console.log('🎨 Aggiornamento UI con risultati:', results);

        // BMI
        safeSetValue('bmi', results.bmi, true);
        safeSetValue('bmi_hidden', results.bmi);

        // BMI Indicator
        const bmiIndicator = safeGetElement('bmiIndicator');
        if (bmiIndicator) {
            bmiIndicator.textContent = results.bmiCategory.category;
            bmiIndicator.className = `bmi-indicator ${results.bmiCategory.class}`;
            bmiIndicator.style.display = 'inline-block';
        }

        // Altri valori
        safeSetValue('peso_ideale', results.idealWeight, true);
        safeSetValue('peso_ideale_hidden', results.idealWeight);

        safeSetValue('meta_basale', results.bmr, true);
        safeSetValue('meta_basale_hidden', results.bmr);

        safeSetValue('meta_giornaliero', results.tdee, true);
        safeSetValue('meta_giornaliero_hidden', results.tdee);

        safeSetValue('calorie_giornaliere', results.targetCalories, true);
        safeSetValue('calorie_giornaliere_hidden', results.targetCalories);

        // Macronutrienti
        safeSetValue('carboidrati_input', results.carboidrati, true);
        safeSetValue('carboidrati_hidden', results.carboidrati);

        safeSetValue('proteine_input', results.proteine, true);
        safeSetValue('proteine_hidden', results.proteine);

        safeSetValue('grassi_input', results.grassi, true);
        safeSetValue('grassi_hidden', results.grassi);

        // Calorie per macro (opzionale)
        safeSetValue('carbo_kcal', results.carboidrati * 4, true);
        safeSetValue('prot_kcal', results.proteine * 4, true);
        safeSetValue('grassi_kcal', results.grassi * 9, true);

        console.log('✅ UI aggiornata');
    }

    calculate() {
        console.log('🔄 Inizio calcolo...');
        if (!this.form) {
            console.error('❌ Form non disponibile');
            return;
        }

        showProgress();

        const formData = this.getFormData();
        if (!this.isDataComplete(formData)) {
            console.warn('⚠️ Calcolo interrotto - dati incompleti');
            hideProgress();
            return;
        }

        const results = this.performCalculations(formData);
        this.updateUI(results);

        hideProgress();
        console.log('✅ Calcolo completato');
    }

    validateField(element) {
        if (!element) return false;

        const value = element.value;
        const name = element.name;
        let isValid = true;

        if (element.type === 'number') {
            const numValue = parseFloat(value);
            const rules = CONFIG.VALIDATION_RULES[name];
            if (rules) {
                isValid = !isNaN(numValue) && numValue >= rules.min && numValue <= rules.max;
            }
        }

        if (element.tagName === 'SELECT') {
            isValid = value && value !== '';
        }

        element.classList.toggle('is-valid', isValid && value !== '');
        element.classList.toggle('is-invalid', !isValid && value !== '');

        return isValid;
    }

    validateForm() {
        if (!this.form) return false;
        console.log('🔍 Validazione form...');

        const requiredFields = ['nome', 'cognome', 'sesso', 'eta', 'altezza', 'peso', 'tdee', 'deficit_calorico', 'attivita_fisica', 'dieta'];
        let isValid = true;

        requiredFields.forEach(fieldName => {
            const element = this.form.elements[fieldName];
            if (element) {
                const fieldValid = this.validateField(element);
                if (!fieldValid) {
                    console.warn(`❌ Campo non valido: ${fieldName}`);
                }
                isValid = isValid && fieldValid;
            }
        });

        console.log(isValid ? '✅ Form valido' : '❌ Form non valido');
        return isValid;
    }

    async submitForm() {
        console.log('📤 Invio form...');
        if (!this.validateForm()) {
            console.error('❌ Form non valido, invio annullato');
            return;
        }

        try {
            const formData = new FormData(this.form);
            const response = await fetch('/salva_dati', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                console.log('✅ Dati salvati con successo');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 2000);
            } else {
                throw new Error('Errore nel salvataggio');
            }
        } catch (error) {
            console.error('❌ Errore:', error);
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
}

// ============= INIZIALIZZAZIONE =============
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM Caricato - Inizializzazione dieta.js...');

    // Verifica che il form esista
    const formElement = document.getElementById('personalInfoForm');
    if (!formElement) {
        console.error('❌ Form personalInfoForm non trovato nel DOM!');
        console.log('🔍 Elementi con class "tabcontent":', document.querySelectorAll('.tabcontent'));
        console.log('🔍 Div DietaForm:', document.getElementById('DietaForm'));
        return;
    }

    console.log('✅ Form trovato, creazione FormManager...');

    // Crea istanza del FormManager
    const formManager = new FormManager();

    // Esporta per uso globale
    window.formManager = formManager;
    window.FormManager = FormManager;
    window.NutritionCalculator = NutritionCalculator;

    // Se ci sono dati utente preesistenti, caricali
    if (typeof userData !== 'undefined' && userData) {
        console.log('📥 Caricamento dati utente esistenti...');
        formManager.loadUserData(userData);
    }

    console.log('🎉 Inizializzazione completata!');
});

// Funzione globale per ricalcolo (retrocompatibilità)
window.calculateResults = function() {
    console.log('🔄 calculateResults chiamato');
    if (window.formManager) {
        window.formManager.calculate();
    } else {
        console.error('❌ FormManager non inizializzato');
    }
};