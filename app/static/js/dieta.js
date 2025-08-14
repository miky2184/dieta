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

    // Calcolo TDEE più preciso combinando attività quotidiana e allenamento
    static calculateTDEE(bmr, dailyActivity, trainingFrequency, trainingType, dailySteps) {
        // Moltiplicatori base per attività quotidiana
        const activityMultipliers = {
            'sedentary': 1.2,   // Lavoro sedentario
            'light': 1.3,       // Lavoro in piedi
            'moderate': 1.4,    // Lavoro attivo
            'high': 1.5         // Lavoro fisico pesante
        };

        // Bonus per allenamento (aggiuntivo)
        const trainingBonus = {
            'none': 0,
            'light': 0.1,       // 1-2 volte/settimana
            'moderate': 0.2,    // 3-4 volte/settimana
            'high': 0.3,        // 5-6 volte/settimana
            'athlete': 0.45     // Tutti i giorni
        };

        // Aggiustamento per tipo di allenamento
        const trainingTypeMultiplier = {
            'none': 1.0,
            'cardio': 0.9,      // Cardio brucia meno post-allenamento
            'strength': 1.1,    // Pesi aumentano EPOC
            'mixed': 1.0,
            'endurance': 0.95,
            'power': 1.15       // Crossfit/sport combat hanno alto EPOC
        };

        // Bonus per passi giornalieri (NEAT)
        const stepBonus = {
            'very_low': 0,      // < 3.000 passi
            'low': 0.05,        // 3.000-5.000
            'moderate': 0.1,    // 5.000-8.000
            'high': 0.15,       // 8.000-12.000
            'very_high': 0.2    // > 12.000
        };

        let baseMultiplier = activityMultipliers[dailyActivity] || 1.2;
        let training = trainingBonus[trainingFrequency] || 0;
        let typeAdjust = trainingTypeMultiplier[trainingType] || 1.0;
        let steps = stepBonus[dailySteps] || 0.1;

        // Formula combinata
        const totalMultiplier = (baseMultiplier + training + steps) * typeAdjust;

        return Math.round(bmr * totalMultiplier);
    }

    // Calcolo macronutrienti ottimizzato per tipo di allenamento
    static calculateOptimizedMacros(calories, weightKg, goal, trainingType, trainingFrequency, stressLevel, sleepHours) {
        // Aggiustamenti per stress e sonno
        const stressAdjustment = {
            'low': 1.0,
            'medium': 0.95,  // Stress medio riduce leggermente il metabolismo
            'high': 0.9      // Alto stress può ridurre significativamente
        };

        const sleepAdjustment = sleepHours < 6 ? 0.95 :
                               sleepHours < 7 ? 0.98 :
                               1.0;

        // Calorie effettive considerando stress e sonno
        const adjustedCalories = Math.round(calories * stressAdjustment[stressLevel] * sleepAdjustment);

        // Proteine base per obiettivo e tipo allenamento
        let proteinMultiplier = this.getProteinMultiplier(goal, trainingType, trainingFrequency);
        let proteine = Math.round(proteinMultiplier * weightKg);

        // Grassi ottimizzati per tipo di allenamento
        let fatPercentage = this.getFatPercentage(goal, trainingType);
        let grassi = Math.round((adjustedCalories * fatPercentage) / 9);

        // Minimo grassi per salute ormonale
        const minFat = stressLevel === 'high' ? Math.round(0.9 * weightKg) : Math.round(0.7 * weightKg);
        grassi = Math.max(grassi, minFat);

        // Carboidrati: il resto delle calorie
        const proteinCals = proteine * 4;
        const fatCals = grassi * 9;
        let carboidrati = Math.round((adjustedCalories - proteinCals - fatCals) / 4);

        // Minimi carboidrati per tipo di allenamento
        const minCarbs = this.getMinCarbs(trainingType, trainingFrequency);

        if (carboidrati < minCarbs) {
            carboidrati = minCarbs;
            // Riaggiusta grassi se necessario
            const remainingCals = adjustedCalories - (proteine * 4) - (carboidrati * 4);
            grassi = Math.round(remainingCals / 9);
            grassi = Math.max(grassi, minFat);
        }

        return {
            proteine: Math.max(0, proteine),
            grassi: Math.max(0, grassi),
            carboidrati: Math.max(0, carboidrati),
            calorieAdjusted: adjustedCalories,
            notes: this.generateNotes(stressLevel, sleepHours, trainingType)
        };
    }

    // Helper: moltiplicatore proteine
    static getProteinMultiplier(goal, trainingType, trainingFrequency) {
        const baseProtein = {
            'fat_loss': 2.2,
            'maintenance': 1.6,
            'muscle_gain': 2.0,
            'performance': 1.8,
            'recomp': 2.4  // Ricomposizione richiede più proteine
        };

        const trainingAdjust = {
            'none': 0.9,
            'cardio': 0.95,
            'strength': 1.1,
            'mixed': 1.05,
            'endurance': 1.0,
            'power': 1.15
        };

        const frequencyAdjust = {
            'none': 0.9,
            'light': 0.95,
            'moderate': 1.0,
            'high': 1.05,
            'athlete': 1.1
        };

        const base = baseProtein[goal] || 1.6;
        const training = trainingAdjust[trainingType] || 1.0;
        const frequency = frequencyAdjust[trainingFrequency] || 1.0;

        return base * training * frequency;
    }

    // Helper: percentuale grassi
    static getFatPercentage(goal, trainingType) {
        const baseFat = {
            'fat_loss': 0.25,
            'maintenance': 0.30,
            'muscle_gain': 0.25,
            'performance': 0.30,
            'recomp': 0.28
        };

        // Aggiustamenti per tipo allenamento
        const trainingAdjust = {
            'none': 0,
            'cardio': -0.05,      // Meno grassi per cardio
            'strength': 0.05,      // Più grassi per forza
            'mixed': 0,
            'endurance': -0.05,    // Endurance usa più carbo
            'power': 0.05          // Power training beneficia da più grassi
        };

        const base = baseFat[goal] || 0.30;
        const adjust = trainingAdjust[trainingType] || 0;

        return Math.max(0.20, Math.min(0.35, base + adjust));
    }

    // Helper: carboidrati minimi
    static getMinCarbs(trainingType, trainingFrequency) {
        const baseCarbs = {
            'none': 100,
            'cardio': 180,
            'strength': 130,
            'mixed': 150,
            'endurance': 200,
            'power': 160
        };

        const frequencyMultiplier = {
            'none': 0.8,
            'light': 0.9,
            'moderate': 1.0,
            'high': 1.2,
            'athlete': 1.4
        };

        const base = baseCarbs[trainingType] || 130;
        const mult = frequencyMultiplier[trainingFrequency] || 1.0;

        return Math.round(base * mult);
    }

    // Genera note e suggerimenti
    static generateNotes(stressLevel, sleepHours, trainingType) {
        const notes = [];

        if (stressLevel === 'high') {
            notes.push("⚠️ Stress alto: considera di aumentare i grassi per supportare gli ormoni");
        }

        if (sleepHours < 6) {
            notes.push("😴 Sonno insufficiente: potrebbe influenzare il recupero e il metabolismo");
        } else if (sleepHours < 7) {
            notes.push("💤 Cerca di dormire almeno 7-8 ore per ottimizzare i risultati");
        }

        if (trainingType === 'endurance') {
            notes.push("🏃 Endurance: assicurati di consumare carboidrati durante allenamenti lunghi");
        } else if (trainingType === 'strength') {
            notes.push("💪 Forza: timing delle proteine importante per il recupero");
        }

        return notes;
    }

    // Calcolo velocità ottimale per l'obiettivo
    static getGoalOptions(goal, currentWeight, targetWeight) {
        const weightDiff = targetWeight - currentWeight;
        const isLosing = weightDiff < 0;

        const options = {
            'fat_loss': [
                { value: -0.05, label: "Molto lenta (-5%, -0.25kg/sett)", safe: true },
                { value: -0.10, label: "Lenta (-10%, -0.5kg/sett)", safe: true },
                { value: -0.15, label: "Moderata (-15%, -0.75kg/sett)", safe: true },
                { value: -0.20, label: "Veloce (-20%, -1kg/sett)", safe: false },
                { value: -0.25, label: "Aggressiva (-25%, -1.25kg/sett)", safe: false }
            ],
            'muscle_gain': [
                { value: 0.05, label: "Lean bulk (+5%, +0.1kg/sett)", safe: true },
                { value: 0.10, label: "Slow bulk (+10%, +0.2kg/sett)", safe: true },
                { value: 0.15, label: "Moderate bulk (+15%, +0.3kg/sett)", safe: true },
                { value: 0.20, label: "Fast bulk (+20%, +0.4kg/sett)", safe: false }
            ],
            'maintenance': [
                { value: 0, label: "Mantenimento (0%)", safe: true }
            ],
            'performance': [
                { value: 0, label: "Mantenimento per performance", safe: true },
                { value: 0.05, label: "Leggero surplus (+5%)", safe: true }
            ],
            'recomp': [
                { value: -0.05, label: "Mini-cut (-5%)", safe: true },
                { value: 0, label: "Mantenimento", safe: true },
                { value: 0.05, label: "Mini-bulk (+5%)", safe: true }
            ]
        };

        return options[goal] || options['maintenance'];
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

                    // Inizializza lo slider solo quando cambiano peso o altezza
                    if (id === 'peso' || id === 'altezza') {
                        const slider = safeGetElement('peso_target_slider');
                        if (slider && !slider.hasAttribute('data-user-modified')) {
                            this.initWeightSlider();
                        }
                    }

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
                // Marca lo slider come modificato dall'utente
                slider.setAttribute('data-user-modified', 'true');

                const value = parseFloat(slider.value);
                safeSetValue('pesoObiettivoValue', `${value} kg`, true);
                safeSetValue('peso_target_hidden', value);
                this.updateWeightDifference();
                this.calculate();
            }, 50));

            // Reset del flag quando l'utente rilascia lo slider
            slider.addEventListener('change', () => {
                setTimeout(() => {
                    slider.removeAttribute('data-user-modified');
                }, 1000);
            });
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

            // Calcolo deficit/surplus calorico giornaliero
            const dailyCalorieChange = Math.abs(tdee - targetCalories);

            // 7700 kcal = 1 kg di grasso corporeo (approssimazione)
            // Calcolo più realistico considerando il deficit/surplus effettivo
            if (dailyCalorieChange > 0) {
                const daysNeeded = (weightDiff * 7700) / dailyCalorieChange;
                weeks = Math.round(daysNeeded / 7);
            } else {
                // Se non c'è deficit/surplus, usa una stima conservativa
                const weeklyChange = data.dieta === 'fat_loss' ? 0.5 :
                                    data.dieta === 'muscle_gain' ? 0.25 : 0;
                weeks = weeklyChange > 0 ? Math.round(weightDiff / weeklyChange) : 0;
            }
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

        // Inizializza slider peso SOLO se necessario (non ad ogni update)
        const slider = safeGetElement('peso_target_slider');
        if (slider && !slider.hasAttribute('data-initialized')) {
            this.initWeightSlider();
        }
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

        // Salva il valore corrente dello slider se esiste
        const currentSliderValue = slider.value ? parseFloat(slider.value) : null;

        // Aggiorna i limiti dello slider
        slider.min = minWeight;
        slider.max = maxWeight;
        slider.step = 0.5;

        // Se lo slider non è mai stato inizializzato O se non ha un valore valido, usa il peso ideale
        // Altrimenti mantieni il valore corrente (entro i nuovi limiti)
        if (!slider.hasAttribute('data-initialized') || !currentSliderValue) {
            slider.value = Math.min(Math.max(idealWeight, minWeight), maxWeight);
            slider.setAttribute('data-initialized', 'true');
        } else {
            // Mantieni il valore corrente ma assicurati che sia entro i nuovi limiti
            slider.value = Math.min(Math.max(currentSliderValue, minWeight), maxWeight);
        }

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
                // Gestione speciale per alcuni campi
                if (key === 'tdee' && typeof data[key] === 'number') {
                    // Converti valore numerico in stringa per il select
                    const tdeeMap = {
                        1.2: 'sedentary',
                        1.375: 'light',
                        1.55: 'moderate',
                        1.725: 'high',
                        1.9: 'athlete'
                    };
                    element.value = tdeeMap[data[key]] || 'sedentary';
                } else if (key === 'attivita_fisica' && typeof data[key] === 'number') {
                    // Converti valore numerico in stringa per il select
                    const activityMap = {
                        1.2: 'sedentary',
                        1.5: 'light',
                        1.8: 'moderate',
                        2.0: 'high',
                        2.2: 'athlete'
                    };
                    element.value = activityMap[data[key]] || 'sedentary';
                } else {
                    element.value = data[key];
                }
                console.log(`Campo ${key} impostato a:`, element.value);
            }
        });

        // Gestione del peso target slider
        const slider = safeGetElement('peso_target_slider');
        if (slider) {
            // Se c'è un peso_target nei dati, usalo
            // Altrimenti usa peso_ideale come default
            const targetWeight = data.peso_target || data.peso_ideale || data.peso;

            // Inizializza lo slider con i range corretti
            const minWeight = Math.max(30, data.peso - 30);
            const maxWeight = Math.min(data.peso + 30, 200);

            slider.min = minWeight;
            slider.max = maxWeight;
            slider.value = Math.min(Math.max(targetWeight, minWeight), maxWeight);
            slider.setAttribute('data-initialized', 'true');

            safeSetValue('pesoMin', `${minWeight} kg`, true);
            safeSetValue('pesoMax', `${maxWeight} kg`, true);
            safeSetValue('pesoObiettivoValue', `${slider.value} kg`, true);
            safeSetValue('peso_target_hidden', slider.value);
        }

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