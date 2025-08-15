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

// Modal helper
function showFeedbackModal(title, body, options = {}) {
  const titleEl = document.getElementById('feedbackModalLabel');
  const bodyEl  = document.getElementById('feedbackModalBody');
  if (titleEl) titleEl.textContent = title || '';
  if (bodyEl) {
    bodyEl.textContent = '';
    if (typeof body === 'string') bodyEl.textContent = body;
    else if (body && typeof body === 'object' && body.nodeType === 1) bodyEl.appendChild(body);
  }
  const modalEl = document.getElementById('feedbackModal');
  if (!modalEl || typeof bootstrap === 'undefined' || !bootstrap.Modal) {
    alert((title ? title + '\n\n' : '') + (typeof body === 'string' ? body : ''));
    return null;
  }
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl, { backdrop: 'static', keyboard: false });
  modal.show();
  if (options.onHidden) modalEl.addEventListener('hidden.bs.modal', options.onHidden, { once: true });
  return modal;
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

    static getLifestyleAdjustment({ dailySteps, trainingFrequency }) {
        // Normalizza input
        const steps = parseInt(dailySteps || 0, 10) || 0;

        // Moltiplicatore passi (NEAT)
        // ~5k passi ≈ neutro. Sotto riduce leggermente, sopra aumenta.
        let stepsMult = 1.0;
        if (steps < 3000) stepsMult = 0.97;
        else if (steps < 7000) stepsMult = 1.0;
        else if (steps < 10000) stepsMult = 1.03;
        else if (steps < 15000) stepsMult = 1.06;
        else stepsMult = 1.09;

        // Frequenza allenamento come lieve aggiustamento del NEAT (non sostituisce tdee/attivita)
        let freqAdj = 1.0;
        const freq = (trainingFrequency || '').toString().toLowerCase();
        if (['none'].includes(freq)) freqAdj = 1.0;
        else if (['light'].includes(freq)) freqAdj = 1.01;
        else if (['moderate'].includes(freq)) freqAdj = 1.02;
        else if (['high'].includes(freq)) freqAdj = 1.03;
        else if (['athlete'].includes(freq)) freqAdj = 1.04;

        // Moltiplicatore totale (clamp prudenziale)
        let total = stepsMult * freqAdj;
        total = Math.max(0.90, Math.min(1.15, total)); // +/-15% max

        return total;
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

    /**
     * Calcola i macronutrienti in base alle calorie target e al tipo di dieta.
     * Versione migliorata che assicura distribuzione precisa delle calorie.
     *
     * @param {number} calories - Calorie giornaliere target
     * @param {number} weightKg - Peso corporeo in kg
     * @param {string} goal - Obiettivo dieta ('fat_loss', 'maintenance', 'muscle_gain')
     * @param {string} activity - Livello di attività ('sedentary', 'light', 'moderate', 'high', 'athlete')
     * @returns {Object} - Oggetto contenente grammi di proteine, grassi e carboidrati
     */
    static calculateMacros(calories, weightKg, goal, activity, trainingType = 'mixed') {
      // ---- Preset dietetici ----
      const presets = {
        fat_loss:    { p: 2.0, f: 0.9,  name: "Dimagrimento" },
        maintenance: { p: 1.8, f: 0.9,  name: "Mantenimento" },
        muscle_gain: { p: 1.8, f: 0.9,  name: "Costruzione muscolare" }
      };
      const preset = presets[goal] || presets.maintenance;

      // ---- Minimi/sicurezze ----
      const FAT_MIN_G_PER_KG = 0.7;           // salute ormonale
      const PRO_MIN_G_PER_KG = 1.4;           // limite inferiore sicurezza
      const PRO_MAX_G_PER_KG = 2.5;           // tetto proteine
      const carbFloorPerActivity = { sedentary: 2.0, light: 3.0, moderate: 4.0, high: 5.0, athlete: 6.0 };

      // piccolo bump proteico in base al tipo di allenamento
      const proBumpByType = { none:0, cardio:0.1, endurance:0.2, strength:0.25, power:0.25, mixed:0.15 };
      const carbBumpByType = { none:0, cardio:20, endurance:40, strength:0, power:10, mixed:20 };

      // ---- Diete “libere” (g/kg + resto) ----
      const carbFloor = Math.round((carbFloorPerActivity[activity] || 3.0) * weightKg) + (carbBumpByType[trainingType] || 0);

      // Proteine iniziali
      const pPerKg = Math.min(PRO_MAX_G_PER_KG, Math.max(PRO_MIN_G_PER_KG, (preset.p || 1.6) + (proBumpByType[trainingType] || 0)));
      let proteine = Math.round(pPerKg * weightKg);

      // Grassi iniziali
      const fatMin = Math.round(FAT_MIN_G_PER_KG * weightKg);
      let grassi = Math.max(Math.round((preset.f || 0.9) * weightKg), fatMin);

      // Carbo come resto
      let remaining = calories - (proteine*4 + grassi*9);
      let carboidrati = Math.round(remaining / 4);

      // clamp finali
      proteine = Math.max(0, proteine);
      grassi   = Math.max(0, grassi);                 // mai sotto il minimo
      carboidrati = Math.max(0, carboidrati);

      const effective = proteine*4 + grassi*9 + carboidrati*4;
      const proteinPercentage = Math.round((proteine*4/effective)*100);
      const fatPercentage     = Math.round((grassi*9/effective)*100);
      const carbPercentage    = Math.round((carboidrati*4/effective)*100);

      return {
        proteine, grassi, carboidrati,
        proteinPercentage, fatPercentage, carbPercentage,
        proteinCalories: proteine*4, fatCalories: grassi*9, carbCalories: carboidrati*4
      };
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

        // Select con calcolo immediato - ora include anche sleep/steps e alias comuni
        ['sesso', 'tdee', 'training_frequency', 'training_type', 'deficit_calorico','daily_steps'].forEach(id => {
            const element = this.form.elements[id];
            if (element) {
                element.addEventListener('change', () => {
                    console.log(`Campo ${id} cambiato:`, element.value);
                    this.calculate();
                });
            }
        });

        const dietaSelect = this.form.elements['dieta'];
        const deficitSelect = this.form.elements['deficit_calorico'];

        if (!dietaSelect || !deficitSelect) return;

        dietaSelect.addEventListener('change', () => {
            const goal = dietaSelect.value;

            // Svuota le opzioni esistenti
            deficitSelect.innerHTML = '';
            // Mostra il selettore
            deficitSelect.parentNode.style.display = '';

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

        // Passi giornalieri in tempo reale se campo numerico
        const stepsEl = this.form.elements['daily_steps'] || this.form.elements['passi_giornalieri'] || this.form.elements['passi'];
        if (stepsEl) {
            const handler = debounce(() => {
                console.log('Passi giornalieri cambiati:', stepsEl.value);
                this.calculate();
            }, 200);
            stepsEl.addEventListener('input', handler);
            stepsEl.addEventListener('change', () => this.calculate());
        }
    }

    getFormData() {
        if (!this.form) return {};

        const slider = safeGetElement('peso_target_slider');

        // Nuovi campi opzionali per lifestyle adjustment
        const dailySteps = parseInt(this.form.elements['daily_steps']?.value || this.form.elements['passi_giornalieri']?.value || this.form.elements['passi']?.value || '0', 10) || 0;

        return {
            sesso: this.form.elements['sesso']?.value,
            eta: parseFloat(this.form.elements['eta']?.value),
            peso: parseFloat(this.form.elements['peso']?.value),
            altezza: parseFloat(this.form.elements['altezza']?.value),
            tdee: this.form.elements['tdee']?.value,
            deficit_calorico: parseFloat(this.form.elements['deficit_calorico']?.value),
            dieta: this.form.elements['dieta']?.value,
            peso_target: parseFloat(slider?.value || 0),
            training_frequency: this.form.elements['training_frequency']?.value,
            training_type: this.form.elements['training_type']?.value,
            daily_steps: dailySteps
        };
    }

    isDataComplete(data) {
        // Verifica solo i campi essenziali per il calcolo
        const isComplete = data.sesso &&
               !isNaN(data.eta) && data.eta > 0 &&
               !isNaN(data.peso) && data.peso > 0 &&
               !isNaN(data.altezza) && data.altezza > 0 &&
               data.tdee &&
               data.dieta &&
               !isNaN(data.deficit_calorico);

        return isComplete;
    }

    performCalculations(data) {
        //console.log('🧮 Performo calcoli con:', data);

        // 1. Calcolo BMI
        const bmi = NutritionCalculator.calculateBMI(data.peso, data.altezza);
        const bmiCategory = NutritionCalculator.getBMICategory(bmi);
        const idealWeight = NutritionCalculator.calculateIdealWeight(data.altezza);

        //console.log('BMI:', bmi, 'Categoria:', bmiCategory, 'Peso ideale:', idealWeight);

        // 2. Calcolo BMR
        const bmr = NutritionCalculator.calculateBMR(data);
        //console.log('BMR:', bmr);

        // 3. Calcolo TDEE
        const baseMult = NutritionCalculator.getTDEEMultiplier(data.tdee);
        const lifestyleAdj = NutritionCalculator.getLifestyleAdjustment({
            dailySteps: data.daily_steps,
            trainingFrequency: data.training_frequency
        });
        const tdeeMultiplier = +(baseMult * lifestyleAdj).toFixed(3);
        const tdee = Math.round(bmr * tdeeMultiplier);
        //console.log('TDEE:', tdee, '(BMR:', bmr, '× BaseMult:', baseMult, '× LifestyleAdj:', lifestyleAdj, '= Mult:', tdeeMultiplier, ')');

        // 4. Calcolo calorie target con variazione percentuale
        const targetCalories = NutritionCalculator.calcCaloriesTarget(tdee, data.dieta, data.deficit_calorico);
        //console.log('Calorie target:', targetCalories);

        // 5. Calcolo macronutrienti
        let activityForMacros = (data.training_frequency && data.training_frequency !== 'none')
          ? data.training_frequency
          : data.tdee;

        const macros = NutritionCalculator.calculateMacros(
            targetCalories,
            data.peso_target,
            data.dieta,
            activityForMacros,
            data.training_type || 'none'
        );
        //console.log('Macronutrienti:', macros);

        // 6. Calcolo settimane (se necessario)
        let weeks = 0;
        if (data.peso_target && data.peso_target !== data.peso) {
            const weightDiff = Math.abs(data.peso - data.peso_target);

            // Calcolo deficit/surplus calorico giornaliero
            const dailyCalorieChange = Math.abs(tdee - targetCalories);

            // 7700 kcal = 1 kg di grasso corporeo (approssimazione)
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

    /**
     * Aggiornamento della funzione updateUI nel FormManager
     * per mostrare le percentuali dei macronutrienti e altre informazioni aggiuntive
     */
    updateUI(results) {
        // Aggiornamenti esistenti
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

        // Macronutrienti - Aggiornati con animazioni
        this.animateValue('carboidrati_input', results.carboidrati);
        this.animateValue('proteine_input', results.proteine);
        this.animateValue('grassi_input', results.grassi);

        // Aggiorna i campi nascosti
        safeSetValue('carboidrati_hidden', results.carboidrati);
        safeSetValue('proteine_hidden', results.proteine);
        safeSetValue('grassi_hidden', results.grassi);

        // NUOVE FUNZIONALITÀ: Usa i valori calcolati direttamente dalla funzione calculateMacros
        // invece di ricalcolarli qui
        safeSetValue('carbo_kcal', results.carbCalories, true);
        safeSetValue('prot_kcal', results.proteinCalories, true);
        safeSetValue('grassi_kcal', results.fatCalories, true);

        // NUOVE FUNZIONALITÀ: Mostra le percentuali dei macronutrienti
        const carboPercentage = safeGetElement('carbo_percentage');
        const proteinPercentage = safeGetElement('protein_percentage');
        const fatPercentage = safeGetElement('fat_percentage');

        if (carboPercentage) carboPercentage.textContent = `${results.carbPercentage}%`;
        if (proteinPercentage) proteinPercentage.textContent = `${results.proteinPercentage}%`;
        if (fatPercentage) fatPercentage.textContent = `${results.fatPercentage}%`;

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

    updateMacroPercentages(protGrams, carbGrams, fatGrams, totalCalories) {
      // Calcola calorie per ogni macronutriente
      const protCals = protGrams * 4;
      const carbCals = carbGrams * 4;
      const fatCals = fatGrams * 9;

      // Calcola percentuali
      const protPerc = (protCals / totalCalories) * 100;
      const carbPerc = (carbCals / totalCalories) * 100;
      const fatPerc = (fatCals / totalCalories) * 100;

      // Aggiorna testo calorie
      document.getElementById('prot_kcal').textContent = Math.round(protCals);
      document.getElementById('carbo_kcal').textContent = Math.round(carbCals);
      document.getElementById('grassi_kcal').textContent = Math.round(fatCals);

      // Aggiorna percentuali nei badge
      document.getElementById('protein_percentage').textContent = Math.round(protPerc) + '%';
      document.getElementById('carbo_percentage').textContent = Math.round(carbPerc) + '%';
      document.getElementById('fat_percentage').textContent = Math.round(fatPerc) + '%';

      // Aggiorna barra di progresso
      const protProgress = document.getElementById('protein_progress');
      const carbProgress = document.getElementById('carb_progress');
      const fatProgress = document.getElementById('fat_progress');

      if (protProgress && carbProgress && fatProgress) {
        protProgress.style.width = protPerc + '%';
        carbProgress.style.width = carbPerc + '%';
        fatProgress.style.width = fatPerc + '%';

        // Aggiorna testi percentuali nella barra
        document.getElementById('protein_progress_perc').textContent = Math.round(protPerc) + '%';
        document.getElementById('carb_progress_perc').textContent = Math.round(carbPerc) + '%';
        document.getElementById('fat_progress_perc').textContent = Math.round(fatPerc) + '%';
      }
    }

    addWeeksToDate(weeks) {
        const date = new Date();
        date.setDate(date.getDate() + (weeks * 7));
        const months = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"];
        return `${months[date.getMonth()]} ${date.getFullYear()}`;
    }

    /**
     * Funzione per aggiornare la barra di progresso dei macronutrienti
     * Da aggiungere alla classe FormManager
     */
    updateMacroProgressBar(results) {
        // Recupera gli elementi della barra di progresso
        const carbProgress = safeGetElement('carb_progress');
        const proteinProgress = safeGetElement('protein_progress');
        const fatProgress = safeGetElement('fat_progress');

        // Recupera gli elementi di testo percentuale
        const carbProgressPerc = safeGetElement('carb_progress_perc');
        const proteinProgressPerc = safeGetElement('protein_progress_perc');
        const fatProgressPerc = safeGetElement('fat_progress_perc');

        // Recupera gli elementi di testo nella barra
        const carbProgressText = safeGetElement('carb_progress_text');
        const proteinProgressText = safeGetElement('protein_progress_text');
        const fatProgressText = safeGetElement('fat_progress_text');

        // Verifica che gli elementi esistano
        if (!carbProgress || !proteinProgress || !fatProgress) return;

        // Ottieni le percentuali dei macronutrienti
        const carbPerc = results.carbPercentage;
        const proteinPerc = results.proteinPercentage;
        const fatPerc = results.fatPercentage;

        // Aggiorna la larghezza delle barre di progresso con animazione
        this.animateProgressBar(carbProgress, carbPerc);
        this.animateProgressBar(proteinProgress, proteinPerc);
        this.animateProgressBar(fatProgress, fatPerc);

        // Aggiorna i testi percentuali
        if (carbProgressPerc) carbProgressPerc.textContent = `${carbPerc}%`;
        if (proteinProgressPerc) proteinProgressPerc.textContent = `${proteinPerc}%`;
        if (fatProgressPerc) fatProgressPerc.textContent = `${fatPerc}%`;

        // Aggiorna i testi nelle barre solo se c'è spazio sufficiente
        if (carbProgressText && carbPerc >= 10) {
            carbProgressText.textContent = `Carboidrati ${carbPerc}%`;
        } else if (carbProgressText) {
            carbProgressText.textContent = '';
        }

        if (proteinProgressText && proteinPerc >= 10) {
            proteinProgressText.textContent = `Proteine ${proteinPerc}%`;
        } else if (proteinProgressText) {
            proteinProgressText.textContent = '';
        }

        if (fatProgressText && fatPerc >= 10) {
            fatProgressText.textContent = `Grassi ${fatPerc}%`;
        } else if (fatProgressText) {
            fatProgressText.textContent = '';
        }
    }

    /**
     * Anima la barra di progresso
     * @param {HTMLElement} element - Elemento DOM della barra di progresso
     * @param {number} targetPercentage - Percentuale target
     */
    animateProgressBar(element, targetPercentage) {
        if (!element) return;

        const currentWidth = parseInt(element.style.width) || 0;
        const duration = 500;
        const startTime = Date.now();

        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const currentPercentage = currentWidth + (targetPercentage - currentWidth) * progress;

            element.style.width = `${currentPercentage}%`;
            element.setAttribute('aria-valuenow', currentPercentage);

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        animate();
    }

        /**
     * Aggiornamento al metodo calculate() della classe FormManager
     * per includere l'aggiornamento della barra di progresso
     */
    calculate() {
        if (!this.form) return;

        showProgress();

        const formData = this.getFormData();
        if (!this.isDataComplete(formData)) {
            hideProgress();
            return;
        }

        try {
            // Esegui i calcoli
            const results = this.performCalculations(formData);

            // Aggiorna l'interfaccia utente
            this.updateUI(results);

            // Aggiorna la barra di progresso dei macronutrienti
            this.updateMacroProgressBar(results);

            // Sincronizza i campi nascosti
            this.synchronizeFields();


            hideProgress();
        } catch (error) {
            console.error('Errore durante il calcolo:', error);
            hideProgress();
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

        const requiredFields = ['nome', 'cognome', 'sesso', 'eta', 'altezza', 'peso', 'tdee', 'deficit_calorico', 'dieta'];
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
        showFeedbackModal('Campi mancanti', 'Compila tutti i campi richiesti e riprova.');
        return;
      }

      // 1) Forza calcolo e attendi un frame per aggiornare hidden
      this.calculate();
      await new Promise(r => requestAnimationFrame(r));
      // Aggiungi un altro delay per sicurezza
      await new Promise(r => setTimeout(r, 100));

      const submitBtn = this.form.querySelector('[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;
      showProgress();

      try {
        const fd = new FormData(this.form);

        // Mappa visivo->hidden (prende i numeri reali)
        const mirrorPairs = [
          ['bmi',                 'bmi_hidden'],
          ['peso_ideale',         'peso_ideale_hidden'],
          ['peso_target',         'peso_target_hidden'],
          ['calorie_giornaliere', 'calorie_giornaliere_hidden'],
          ['settimane_dieta',     'settimane_dieta_hidden']
        ];

        // chiavi numeriche obbligatorie per cui usiamo fallback "0" se hidden vuoto
        const numericRequired = new Set([
          'eta', 'altezza', 'peso', 'deficit_calorico',
          'calorie_giornaliere', 'carboidrati', 'proteine', 'grassi',
          'settimane_dieta', 'peso_target', 'peso_ideale', 'bmi'
        ]);

        const pickHidden = (nameVisible, idHidden) => {
          const hiddenEl = document.getElementById(idHidden);
          if (!hiddenEl) return;
          let v = hiddenEl.value ?? hiddenEl.textContent ?? '';
          v = (v + '').replace(',', '.').trim();
          if (v === '' || v.toLowerCase() === 'undefined' || v.toLowerCase() === 'null' || isNaN(parseFloat(v))) {
            // non cancellare le chiavi richieste: metti fallback se numeriche
            if (numericRequired.has(nameVisible)) fd.set(nameVisible, '0');
            // altrimenti lascia com'è (potrebbe essere testo)
          } else {
            fd.set(nameVisible, v);
          }
        };

        // prima normalizza i required testuali vuoti, poi applica hidden
        mirrorPairs.forEach(([vis, hid]) => { pickHidden(vis, hid); });

        // 3) Normalizza numerici (stringhe -> numeri), senza eliminare le chiavi
        [
          'eta', 'altezza', 'peso', 'deficit_calorico',
          'calorie_giornaliere', 'carboidrati', 'proteine', 'grassi',
          'settimane_dieta', 'peso_target', 'peso_ideale', 'bmi'
        ].forEach(k => {
          if (fd.has(k)) fd.set(k, (fd.get(k)+'').replace(',', '.').trim() || '0');
        });

        // 6) Lifestyle opzionali: aggiungi se presenti nel form
        ['training_frequency','training_type', 'daily_steps'].forEach(k => {
          const el = this.form.elements[k];
          if (el && el.value !== '') fd.set(k, el.value);
        });

        // INVIO
        const response = await fetch('/salva_dati', { method: 'POST', body: fd });

        if (response.ok) {
          showFeedbackModal('Dati salvati', 'Dati salvati con successo! Verrai reindirizzato alla dashboard.', {
            onHidden: () => { window.location.href = '/dashboard'; }
          });
          setTimeout(() => { window.location.href = '/dashboard'; }, 2000);
        } else {
          let msg = 'Errore nel salvataggio. Verifica i dati e riprova.';
          try {
            const data = await response.json();
            if (data?.message) msg = data.message;
          } catch(_) {}
          showFeedbackModal('Errore', msg);
          console.error('Risposta errore:', msg);
        }
      } catch (err) {
        console.error('Errore:', err);
        showFeedbackModal('Errore di rete', 'Controlla la connessione e riprova.');
      } finally {
        if (submitBtn) submitBtn.disabled = false;
        hideProgress();
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

        //console.log('Caricamento dati utente:', data);

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
                } else {
                    element.value = data[key];
                }
                //console.log(`Campo ${key} impostato a:`, element.value);
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

    synchronizeFields() {
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

        const settimaneDietaVisible = document.getElementById('settimane_dieta');
        const settimaneDietaHidden = document.getElementById('settimane_dieta_hidden');
        settimaneDietaHidden.value = settimaneDietaVisible.value;

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


}

// ============= INIZIALIZZAZIONE =============
document.addEventListener('DOMContentLoaded', function() {
    //console.log('Inizializzazione FormManager...');

    // Crea istanza del FormManager
    const formManager = new FormManager();

    // Esporta per uso globale
    window.formManager = formManager;
    //window.FormManager = FormManager;
    window.NutritionCalculator = NutritionCalculator;

    // Se ci sono dati utente preesistenti, caricali
    if (typeof userData !== 'undefined' && userData) {
        //console.log('Caricamento dati utente esistenti...');
        formManager.loadUserData(userData);
    }

    //console.log('Inizializzazione completata!');
});

// Funzione globale per ricalcolo (retrocompatibilità)
window.calculateResults = function() {
    if (window.formManager) {
        window.formManager.calculate();
    }
};