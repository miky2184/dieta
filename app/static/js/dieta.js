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

    static getLifestyleAdjustment({ sleepQuality, dailySteps, extraFactors = [], trainingFrequency }) {
        // Normalizza input
        const sleepVal = (sleepQuality || '').toString().toLowerCase();
        const steps = parseInt(dailySteps || 0, 10) || 0;
        const factors = Array.isArray(extraFactors) ? extraFactors.map(v => (v || '').toString().toLowerCase()) : [];

        // 1) Moltiplicatore passi (NEAT)
        // ~5k passi ≈ neutro. Sotto riduce leggermente, sopra aumenta.
        let stepsMult = 1.0;
        if (steps < 3000) stepsMult = 0.97;
        else if (steps < 7000) stepsMult = 1.0;
        else if (steps < 10000) stepsMult = 1.03;
        else if (steps < 15000) stepsMult = 1.06;
        else stepsMult = 1.09;

        // 2) Qualità del sonno
        // valori attesi: 'poor'/'scarso', 'fair'/'discreto', 'good'/'buono', 'excellent'/'ottimo'
        let sleepMult = 1.0;
        if (['poor', 'scarso', 'basso'].includes(sleepVal)) sleepMult = 0.95;
        else if (['fair', 'discreto', 'medio'].includes(sleepVal)) sleepMult = 1.0;
        else if (['good', 'buono'].includes(sleepVal)) sleepMult = 1.02;
        else if (['excellent', 'ottimo', 'alto'].includes(sleepVal)) sleepMult = 1.03;
        // supporta scala numerica 1..5
        if (/^[1-5]$/.test(sleepVal)) {
            const n = parseInt(sleepVal, 10);
            if (n <= 2) sleepMult = 0.96;
            else if (n === 3) sleepMult = 1.0;
            else if (n === 4) sleepMult = 1.02;
            else sleepMult = 1.03;
        }

        // 3) Fattori aggiuntivi (opzionali)
        // mapping semplice: riconosci alcune chiavi comuni; gli altri ignorati
        let extraMult = 1.0;
        const has = (k) => factors.some(f => f.includes(k));
        if (has('stress_alto') || has('stress-high') || has('stress_high')) extraMult *= 0.97;
        if (has('neat_alto') || has('camminate') || has('standing')) extraMult *= 1.02;
        if (has('metabolismo_lento')) extraMult *= 0.98;
        if (has('termogenesi') || has('tef_alto')) extraMult *= 1.01;

        // 4) Frequenza allenamento come lieve aggiustamento del NEAT (non sostituisce tdee/attivita)
        let freqAdj = 1.0;
        const freq = (trainingFrequency || '').toString().toLowerCase();
        if (['low', 'bassa', '1-2', '1x', '2x'].includes(freq)) freqAdj = 1.0;
        else if (['medium', 'media', '3-4', '3x', '4x', 'moderate'].includes(freq)) freqAdj = 1.01;
        else if (['high', 'alta', '5+', '5x', '6x', 'daily', 'quotidiana', 'athlete'].includes(freq)) freqAdj = 1.02;

        // Moltiplicatore totale (clamp prudenziale)
        let total = stepsMult * sleepMult * extraMult * freqAdj;
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
     * @param {string} goal - Obiettivo dieta ('fat_loss', 'maintenance', 'muscle_gain', 'performance')
     * @param {string} activity - Livello di attività ('sedentary', 'light', 'moderate', 'high', 'athlete')
     * @returns {Object} - Oggetto contenente grammi di proteine, grassi e carboidrati
     */
    static calculateMacros(calories, weightKg, goal, activity, trainingType = 'mixed') {
      // ---- Preset dietetici ----
      const presets = {
        fat_loss:    { p: 2.2, f: 0.8,  name: "Dimagrimento" },
        maintenance: { p: 1.6, f: 0.9,  name: "Mantenimento" },
        muscle_gain: { p: 2.0, f: 1.0,  name: "Costruzione muscolare" },
        performance: { p: 1.8, f: 0.9,  name: "Performance" },
        keto: {
          p: 1.6, f: 2.0, name: "Chetogenica",
          forcedRatios: { p: 0.20, f: 0.75, c: 0.05 }
        },
        low_carb: {
          p: 2.0, f: 1.2, name: "Low‑carb",
          forcedRatios: { p: 0.35, f: 0.40, c: 0.25 }
        },
        mediterranean: {
          p: 1.4, f: 1.0, name: "Mediterranea",
          forcedRatios: { p: 0.20, f: 0.30, c: 0.50 }
        },
        balanced: {
          p: 1.6, f: 0.8, name: "Bilanciata",
          forcedRatios: { p: 0.25, f: 0.20, c: 0.55 }
        }
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

      // ---- Diete con ratio forzati (kcal %) ----
      if (preset.forcedRatios) {
        const r = preset.forcedRatios;
        let proteine = Math.round((calories * r.p) / 4);
        let grassi   = Math.round((calories * r.f) / 9);
        let carboidrati = Math.round((calories * r.c) / 4);

        // safety: minimo grassi (sposta dai carbo se necessario)
        const fatMin = Math.round(FAT_MIN_G_PER_KG * weightKg);
        if (grassi < fatMin) {
          const need = fatMin - grassi;              // g di grasso da aggiungere
          const kcalNeed = need * 9;
          const takeFromCarbs = Math.ceil(kcalNeed / 4);
          carboidrati = Math.max(0, carboidrati - takeFromCarbs);
          grassi = fatMin;
        }

        // riallinea alle calorie precise (aggiusta sui carbo)
        const effective = proteine*4 + grassi*9 + carboidrati*4;
        const diff = calories - effective;
        carboidrati = Math.max(0, carboidrati + Math.round(diff/4));

        const eff2 = proteine*4 + grassi*9 + carboidrati*4;
        const proteinPercentage = Math.round((proteine*4/eff2)*100);
        const fatPercentage     = Math.round((grassi*9/eff2)*100);
        const carbPercentage    = Math.round((carboidrati*4/eff2)*100);
        return {
          proteine, grassi, carboidrati,
          proteinPercentage, fatPercentage, carbPercentage,
          proteinCalories: proteine*4, fatCalories: grassi*9, carbCalories: carboidrati*4
        };
      }

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

      // 1) rispetta il carb floor (riducendo eventuale grasso sopra il minimo)
      if (carboidrati < carbFloor) {
        const need = carbFloor - carboidrati;               // g carbo da aggiungere
        const kcalNeed = need * 4;

        // prova a prendere dai grassi sopra il minimo
        const fatAboveMinKcal = Math.max(0, (grassi - fatMin) * 9);
        const takeFromFatKcal = Math.min(fatAboveMinKcal, kcalNeed);
        grassi -= Math.round(takeFromFatKcal / 9);

        // ricalcola carbo
        remaining = calories - (proteine*4 + grassi*9);
        carboidrati = Math.round(remaining / 4);
      }

      // 2) se ancora non basta, riduci leggermente le proteine ma non sotto PRO_MIN_G_PER_KG
      if (carboidrati < carbFloor) {
        const targetP = Math.max(Math.round(PRO_MIN_G_PER_KG * weightKg), Math.round(proteine - Math.ceil(((carbFloor - carboidrati)*4)/4)));
        proteine = Math.max(targetP, Math.round(PRO_MIN_G_PER_KG * weightKg));
        remaining = calories - (proteine*4 + grassi*9);
        carboidrati = Math.round(remaining / 4);
      }

      // 3) ultima safety: se il totale supera le calorie o va negativo, ribilancia sui carbo
      const totalNow = proteine*4 + grassi*9 + carboidrati*4;
      if (totalNow !== calories) {
        const diff = calories - totalNow;
        carboidrati = Math.max(0, carboidrati + Math.round(diff/4));
      }

      // clamp finali
      proteine = Math.max(0, proteine);
      grassi   = Math.max(fatMin, grassi);                 // mai sotto il minimo
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

        // Select con calcolo immediato - ora include anche sleep/steps e alias comuni
        ['sesso', 'tdee', 'training_frequency', 'training_type', 'dieta', 'deficit_calorico', 'sleep_quality', 'qualita_sonno', 'daily_steps', 'passi', 'passi_giornalieri'].forEach(id => {
            const element = this.form.elements[id];
            if (element) {
                element.addEventListener('change', () => {
                    console.log(`Campo ${id} cambiato:`, element.value);
                    this.calculate();
                });
            }
        });

        // Aggiungi listener per attivita_fisica solo se esiste
        const attivitaElement = this.form.elements['attivita_fisica'];
        if (attivitaElement) {
            attivitaElement.addEventListener('change', () => {
                console.log('Attività fisica cambiata:', attivitaElement.value);
                this.calculate();
            });
        }

        // Gestione speciale per deficit_calorico
        const deficitElement = this.form.elements['deficit_calorico'];
        if (deficitElement) {
            deficitElement.addEventListener('change', () => {
                console.log('Deficit calorico cambiato:', deficitElement.value);
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

    /**
     * Miglioramento della funzione initDietaChangeListener nel FormManager
     * per supportare tutti i tipi di dieta e spiegazioni
     */
    initDietaChangeListener() {
        const dietaSelect = this.form.elements['dieta'];
        const deficitSelect = this.form.elements['deficit_calorico'];
        const dietaInfo = safeGetElement('dieta_info');

        if (!dietaSelect || !deficitSelect) return;

        // Definizione delle descrizioni per ogni tipo di dieta
        const dietaDescriptions = {
            fat_loss: "Una dieta progettata per la perdita di grasso, con proteine elevate per preservare la massa muscolare.",
            maintenance: "Una dieta bilanciata per mantenere il peso attuale.",
            muscle_gain: "Una dieta con surplus calorico per favorire la crescita muscolare.",
            performance: "Una dieta ottimizzata per le prestazioni atletiche, con maggiore apporto di carboidrati.",
            keto: "Una dieta a bassissimo contenuto di carboidrati (5%), alta in grassi (75%) e moderata in proteine (20%).",
            low_carb: "Una dieta a basso contenuto di carboidrati (25%), alta in proteine (35%) e grassi (40%).",
            balanced: "Una dieta bilanciata con distribuzione classica: 55% carboidrati, 25% proteine, 20% grassi.",
            mediterranean: "Una dieta mediterranea con 50% carboidrati, 20% proteine e 30% grassi di alta qualità."
        };

        // Aggiorna le opzioni del selettore dieta (se necessario)
        if (dietaSelect.options.length < Object.keys(dietaDescriptions).length) {
            dietaSelect.innerHTML = `
                <option value="fat_loss">Dimagrimento</option>
                <option value="maintenance">Mantenimento</option>
                <option value="muscle_gain">Aumento massa muscolare</option>
                <option value="performance">Performance atletica</option>
                <option value="keto">Chetogenica</option>
                <option value="low_carb">Low-Carb</option>
                <option value="balanced">Bilanciata</option>
                <option value="mediterranean">Mediterranea</option>
            `;
        }

        dietaSelect.addEventListener('change', () => {
            const goal = dietaSelect.value;

            // Aggiorna la descrizione della dieta
            if (dietaInfo) {
                dietaInfo.textContent = dietaDescriptions[goal] || '';
            }

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
            } else if (goal === 'keto' || goal === 'low_carb' || goal === 'balanced' || goal === 'mediterranean') {
                // Per le diete con rapporti fissi, l'unica opzione è il mantenimento
                deficitSelect.innerHTML = `
                    <option value="0" selected>Mantenimento (0%)</option>
                `;
                // Nascondi il selettore del deficit poiché c'è solo un'opzione
                deficitSelect.parentNode.style.display = 'none';
            } else {
                // maintenance o performance
                deficitSelect.innerHTML = `
                    <option value="0" selected>Mantenimento (0%)</option>
                `;
                // Mostra il selettore
                deficitSelect.parentNode.style.display = '';
            }

            // Ricalcola con il nuovo valore
            this.calculate();
        });
    }

    getFormData() {
        if (!this.form) return {};

        const slider = safeGetElement('peso_target_slider');

        // Gestione del campo attivita_fisica che potrebbe non esistere
        // Se non esiste, usa lo stesso valore di tdee come fallback
        const attivitaFisica = this.form.elements['attivita_fisica']?.value ||
                               this.form.elements['tdee']?.value;

        // Nuovi campi opzionali per lifestyle adjustment
        const sleepQuality = this.form.elements['sleep_quality']?.value || this.form.elements['qualita_sonno']?.value || '';
        const dailySteps = parseInt(this.form.elements['daily_steps']?.value || this.form.elements['passi_giornalieri']?.value || this.form.elements['passi']?.value || '0', 10) || 0;
        const extraFactors = Array.from(this.form.querySelectorAll('input[name="fattori_aggiuntivi[]"]:checked, input[name="fattori_aggiuntivi"]:checked'))
            .map(el => el.value);

        return {
            sesso: this.form.elements['sesso']?.value,
            eta: parseFloat(this.form.elements['eta']?.value),
            peso: parseFloat(this.form.elements['peso']?.value),
            altezza: parseFloat(this.form.elements['altezza']?.value),
            tdee: this.form.elements['tdee']?.value,
            deficit_calorico: parseFloat(this.form.elements['deficit_calorico']?.value),
            attivita_fisica: attivitaFisica,
            dieta: this.form.elements['dieta']?.value,
            peso_target: parseFloat(slider?.value || 0),
            training_frequency: this.form.elements['training_frequency']?.value,
            training_type: this.form.elements['training_type']?.value,
            sleep_quality: sleepQuality,
            daily_steps: dailySteps,
            extra_factors: extraFactors
        };
    }

    isDataComplete(data) {
        // Verifica solo i campi essenziali per il calcolo
        // Rimuoviamo attivita_fisica dalla verifica obbligatoria
        const isComplete = data.sesso &&
               !isNaN(data.eta) && data.eta > 0 &&
               !isNaN(data.peso) && data.peso > 0 &&
               !isNaN(data.altezza) && data.altezza > 0 &&
               data.tdee &&
               data.dieta &&
               !isNaN(data.deficit_calorico);

        console.log('Data completeness check:', {
            sesso: !!data.sesso,
            eta: !isNaN(data.eta) && data.eta > 0,
            peso: !isNaN(data.peso) && data.peso > 0,
            altezza: !isNaN(data.altezza) && data.altezza > 0,
            tdee: !!data.tdee,
            dieta: !!data.dieta,
            deficit_calorico: !isNaN(data.deficit_calorico),
            isComplete: isComplete
        });

        return isComplete;
    }

    performCalculations(data) {
        console.log('🧮 Performo calcoli con:', data);

        // 1. Calcolo BMI
        const bmi = NutritionCalculator.calculateBMI(data.peso, data.altezza);
        const bmiCategory = NutritionCalculator.getBMICategory(bmi);
        const idealWeight = NutritionCalculator.calculateIdealWeight(data.altezza);

        console.log('BMI:', bmi, 'Categoria:', bmiCategory, 'Peso ideale:', idealWeight);

        // 2. Calcolo BMR
        const bmr = NutritionCalculator.calculateBMR(data);
        console.log('BMR:', bmr);

        // 3. Calcolo TDEE
        const baseMult = NutritionCalculator.getTDEEMultiplier(data.tdee);
        const lifestyleAdj = NutritionCalculator.getLifestyleAdjustment({
            sleepQuality: data.sleep_quality,
            dailySteps: data.daily_steps,
            extraFactors: data.extra_factors,
            trainingFrequency: data.training_frequency
        });
        const tdeeMultiplier = +(baseMult * lifestyleAdj).toFixed(3);
        const tdee = Math.round(bmr * tdeeMultiplier);
        console.log('TDEE:', tdee, '(BMR:', bmr, '× BaseMult:', baseMult, '× LifestyleAdj:', lifestyleAdj, '= Mult:', tdeeMultiplier, ')');

        // 4. Calcolo calorie target con variazione percentuale
        const targetCalories = NutritionCalculator.calcCaloriesTarget(tdee, data.dieta, data.deficit_calorico);
        console.log('Calorie target:', targetCalories);

        // 5. Calcolo macronutrienti
        // Usa attivita_fisica se presente, altrimenti usa tdee come fallback
        // Priorità alla frequenza di allenamento; fallback su attivita_fisica/tdee
        let activityForMacros = (data.training_frequency && data.training_frequency !== 'none')
          ? data.training_frequency
          : (data.attivita_fisica || data.tdee);

        const macros = NutritionCalculator.calculateMacros(
            targetCalories,
            data.peso,
            data.dieta,
            activityForMacros,
            data.training_type || 'none'
        );
        console.log('Macronutrienti:', macros);

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

            // NUOVO: Aggiorna le informazioni sui macronutrienti
            this.updateMacroInfo(results, formData.dieta);

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
        showFeedbackModal('Campi mancanti', 'Compila tutti i campi richiesti e riprova.');
        return;
      }

      const submitBtn = this.form.querySelector('[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;
      showProgress();

      try {
        // Costruisco il FormData
        const fd = new FormData(this.form);

        // Rimuovi derivati che NON vogliamo più mandare
        ['bmi','peso_ideale','meta_basale','meta_giornaliero'].forEach(k => fd.delete(k));

        // Assicura sempre i "richiesti" dal BE
        const requiredKeys = [
          'nome','cognome','sesso','eta','altezza','peso','tdee','deficit_calorico','dieta','attivita_fisica',
          'calorie_giornaliere','carboidrati','proteine','grassi','settimane_dieta'
        ];
        requiredKeys.forEach(k => {
          if (!fd.has(k)) fd.set(k, '');
        });

        // Normalizza numerici principali
        ['eta','altezza','peso','deficit_calorico','calorie_giornaliere','carboidrati','proteine','grassi']
          .forEach(k => { if (fd.has(k)) fd.set(k, (fd.get(k)+'').replace(',', '.').trim()); });

        // Aggiungi lifestyle se presenti (non obbligatori)
        ['training_frequency','training_type','sleep_quality','daily_steps','extra_factors'].forEach(k => {
          const el = this.form.elements[k];
          if (el && el.value !== '') fd.set(k, el.value);
        });

                // 1) Mappa di campi "visivi" -> "hidden" che contengono i numeri reali
        const mirrorPairs = [
          ['bmi', 'bmi_hidden'],
          ['peso_ideale', 'peso_ideale_hidden'],
          ['meta_basale', 'meta_basale_hidden'],
          ['meta_giornaliero', 'meta_giornaliero_hidden'],
          ['calorie_giornaliere', 'calorie_giornaliere_hidden'],
          ['settimane_dieta', 'settimane_dieta_hidden'],
          ['carboidrati', 'carboidrati_hidden'],
          ['proteine', 'proteine_hidden'],
          ['grassi', 'grassi_hidden']
        ];

        // helper: prendi valore numerico dall’hidden, se valido sostituisci
        const pickHidden = (nameVisible, idHidden) => {
          const hiddenEl = document.getElementById(idHidden);
          if (!hiddenEl) return;
          let v = hiddenEl.value ?? hiddenEl.textContent ?? '';
          v = (v + '').replace(',', '.').trim(); // normalizza decimali
          if (v !== '' && v !== 'undefined' && !isNaN(parseFloat(v))) {
            fd.set(nameVisible, v);
          } else {
            // se è spazzatura, non inviare quel campo
            fd.delete(nameVisible);
          }
        };

        mirrorPairs.forEach(([vis, hid]) => {
          // se il form ha quel name, prova a rimpiazzarlo
          if (fd.has(vis)) pickHidden(vis, hid);
        });

        // invio
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

    /**
     * Funzione per aggiornare le informazioni sui macronutrienti
     * Da aggiungere alla classe FormManager
     */
    updateMacroInfo(results, dietaType) {
        const macroDistributionInfo = safeGetElement('macro_distribution_info');
        const macroDistributionText = safeGetElement('macro_distribution_text');
        const proteinInfo = safeGetElement('protein_info');
        const carbInfo = safeGetElement('carb_info');
        const fatInfo = safeGetElement('fat_info');

        if (!macroDistributionInfo || !macroDistributionText) return;

        // Rendi visibile il pannello informativo
        macroDistributionInfo.style.display = 'block';

        // Definizione dei testi informativi per tipo di dieta
        const dietaTexts = {
            fat_loss: "Questa dieta per dimagrimento prevede un alto apporto proteico per preservare la massa muscolare durante il deficit calorico.",
            maintenance: "Questa dieta di mantenimento prevede una distribuzione bilanciata dei macronutrienti per mantenere il peso attuale.",
            muscle_gain: "Questa dieta per aumento massa prevede un surplus calorico con alto apporto proteico per favorire la crescita muscolare.",
            performance: "Questa dieta per performance atletica è ottimizzata con carboidrati adeguati per l'energia e proteine per il recupero muscolare.",
            keto: "La dieta chetogenica prevede un bassissimo apporto di carboidrati per indurre la chetosi, con alta percentuale di grassi e moderata di proteine.",
            low_carb: "La dieta low-carb riduce significativamente i carboidrati a favore di proteine e grassi, utile per controllo glicemico e peso.",
            balanced: "La dieta bilanciata segue le linee guida nutrizionali standard con una distribuzione equilibrata tra carboidrati, proteine e grassi.",
            mediterranean: "La dieta mediterranea privilegia carboidrati complessi, grassi salutari (olio d'oliva) e proteine magre, con benefici per la salute."
        };

        // Aggiorna il testo principale
        macroDistributionText.textContent = dietaTexts[dietaType] || dietaTexts.balanced;

        // Aggiorna le informazioni specifiche sui macronutrienti
        if (proteinInfo) {
            proteinInfo.textContent = `${results.proteinPercentage}% (${results.proteine}g - ${results.proteinCalories} kcal)`;
        }

        if (carbInfo) {
            carbInfo.textContent = `${results.carbPercentage}% (${results.carboidrati}g - ${results.carbCalories} kcal)`;
        }

        if (fatInfo) {
            fatInfo.textContent = `${results.fatPercentage}% (${results.grassi}g - ${results.fatCalories} kcal)`;
        }

        // Aggiungi il testo sulla densità calorica per ogni macronutriente
        const macroCalorieInfo = safeGetElement('macro_calorie_info');
        if (macroCalorieInfo) {
            macroCalorieInfo.textContent = "Proteine: 4 kcal/g • Carboidrati: 4 kcal/g • Grassi: 9 kcal/g";
        }
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