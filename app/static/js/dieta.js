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

      // ---- Diete "libere" (g/kg + resto) ----
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
        console.log('Inizializzazione FormManager avanzato...');
        this.form = document.getElementById('personalInfoForm');

        if (!this.form) {
            console.error('Form personalInfoForm non trovato!');
            return;
        }

        // Inizializza gli event listeners
        this.initFormListeners();
        this.initWeightSlider();
        this.initDietaChangeListener();

        // Inizializza il pannello informativo sui macronutrienti
        this.initMacroInfoPanel();

        // Inizializza le animazioni per i valori
        this.setupAnimations();

        // Aggiungi listener per i pulsanti di esportazione
        this.initExportButtons();

        // Esegui un calcolo iniziale se sono disponibili dati sufficienti
        this.calculate();
    }

    initFormListeners() {
        if (!this.form) return;

        // Aggiungi event listeners per i campi
        const inputFields = this.form.querySelectorAll('input, select');
        inputFields.forEach(field => {
            if (field.type === 'submit') return;

            field.addEventListener('change', debounce(() => {
                this.calculate();
            }, CONFIG.DEBOUNCE_DELAY));
        });

        // Event listener per il form submit
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveData();
        });

        // Inizializza lo slider del peso obiettivo
        const pesoInput = this.form.elements['peso'];
        const altezzaInput = this.form.elements['altezza'];

        if (pesoInput && altezzaInput) {
            pesoInput.addEventListener('change', () => {
                this.initWeightSlider();
            });

            altezzaInput.addEventListener('change', () => {
                this.initWeightSlider();
            });
        }

        // Inizializza lo slider con change listener
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

    initMacroInfoPanel() {
        const macroDistributionInfo = safeGetElement('macro_distribution_info');
        const helpButton = safeGetElement('macro_help_button');

        if (macroDistributionInfo) {
            // Inizialmente nascondi il pannello informativo
            macroDistributionInfo.style.display = 'none';
        }

        if (helpButton) {
            helpButton.addEventListener('click', () => {
                if (macroDistributionInfo) {
                    const isVisible = macroDistributionInfo.style.display !== 'none';
                    macroDistributionInfo.style.display = isVisible ? 'none' : 'block';

                    // Cambia l'icona del pulsante
                    helpButton.innerHTML = isVisible
                        ? '<i class="fas fa-question-circle"></i> Info'
                        : '<i class="fas fa-times-circle"></i> Chiudi';
                }
            });
        }
    }

    initExportButtons() {
        const exportPDFBtn = safeGetElement('export_pdf_button');
        const exportDataBtn = safeGetElement('export_data_button');

        if (exportPDFBtn) {
            exportPDFBtn.addEventListener('click', () => this.exportAsPDF());
        }

        if (exportDataBtn) {
            exportDataBtn.addEventListener('click', () => this.exportAsJSON());
        }
    }

    exportAsPDF() {
        // Qui andrebbe implementata la logica per generare un PDF
        // Usando librerie come jsPDF o sfruttando un endpoint server-side
        alert('Funzionalità di esportazione PDF da implementare');
    }

    exportAsJSON() {
        try {
            const formData = this.getFormData();
            if (!this.isDataComplete(formData)) {
                alert('Compilare tutti i dati richiesti prima di esportare');
                return;
            }

            const results = this.performCalculations(formData);

            // Crea un oggetto con tutti i dati rilevanti
            const exportData = {
                personData: {
                    sesso: formData.sesso,
                    eta: formData.eta,
                    peso: formData.peso,
                    altezza: formData.altezza,
                    pesoTarget: formData.peso_target
                },
                calculatedData: {
                    bmi: results.bmi,
                    bmiCategory: results.bmiCategory.category,
                    idealWeight: results.idealWeight,
                    bmr: results.bmr,
                    tdee: results.tdee,
                    targetCalories: results.targetCalories
                },
                macronutrients: {
                    carboidrati: {
                        grams: results.carboidrati,
                        calories: results.carbCalories,
                        percentage: results.carbPercentage
                    },
                    proteine: {
                        grams: results.proteine,
                        calories: results.proteinCalories,
                        percentage: results.proteinPercentage
                    },
                    grassi: {
                        grams: results.grassi,
                        calories: results.fatCalories,
                        percentage: results.fatPercentage
                    }
                },
                dietSettings: {
                    type: formData.dieta,
                    activityLevel: formData.attivita_fisica,
                    calorieAdjustment: formData.deficit_calorico,
                    estimatedWeeks: results.weeks || 0
                },
                exportDate: new Date().toISOString()
            };

            // Crea un file JSON scaricabile
            const dataStr = JSON.stringify(exportData, null, 2);
            const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);

            const exportFileDefaultName = 'piano_nutrizionale.json';

            // Crea un elemento anchor nascosto e simula il clic
            const linkElement = document.createElement('a');
            linkElement.setAttribute('href', dataUri);
            linkElement.setAttribute('download', exportFileDefaultName);
            linkElement.style.display = 'none';
            document.body.appendChild(linkElement);
            linkElement.click();
            document.body.removeChild(linkElement);

        } catch (error) {
            console.error('Errore durante l\'esportazione dei dati:', error);
            alert('Si è verificato un errore durante l\'esportazione dei dati');
        }
    }

    setupAnimations() {
        // Aggiungi animazioni per hover sulle card dei macronutrienti
        const macroCards = document.querySelectorAll('.macro-card');

        macroCards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-5px)';
                this.style.boxShadow = '0 10px 20px rgba(0,0,0,0.1)';
            });

            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '0 5px 15px rgba(0,0,0,0.05)';
            });
        });
    }

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

    updateMacroChart(results) {
        const chartCanvas = document.getElementById('macroChart');
        if (!chartCanvas) return;

        // Rimuovi il grafico precedente se esiste
        if (this.macroChart) {
            this.macroChart.destroy();
        }

        // Dati per il grafico
        const data = {
            labels: ['Carboidrati', 'Proteine', 'Grassi'],
            datasets: [{
                label: 'Calorie per macronutriente',
                data: [results.carbCalories, results.proteinCalories, results.fatCalories],
                backgroundColor: [
                    'rgba(255, 165, 0, 0.7)',  // Arancione per carboidrati
                    'rgba(220, 53, 69, 0.7)',  // Rosso per proteine
                    'rgba(40, 167, 69, 0.7)'   // Verde per grassi
                ],
                borderColor: [
                    'rgba(255, 165, 0, 1)',
                    'rgba(220, 53, 69, 1)',
                    'rgba(40, 167, 69, 1)'
                ],
                borderWidth: 1
            }]
        };

        // Opzioni per il grafico
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        generateLabels: function(chart) {
                            const datasets = chart.data.datasets;
                            return chart.data.labels.map(function(label, i) {
                                const meta = chart.getDatasetMeta(0);
                                const style = meta.controller.getStyle(i);
                                const percentage = results[label.toLowerCase() === 'carboidrati' ? 'carbPercentage' :
                                                  label.toLowerCase() === 'proteine' ? 'proteinPercentage' : 'fatPercentage'];

                                return {
                                    text: `${label}: ${percentage}%`,
                                    fillStyle: style.backgroundColor,
                                    strokeStyle: style.borderColor,
                                    lineWidth: style.borderWidth,
                                    hidden: false,
                                    index: i
                                };
                            });
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const totalCal = results.targetCalories;
                            const percentage = Math.round((value / totalCal) * 100);

                            // Ottieni i grammi del macronutriente
                            let grams;
                            if (label === 'Carboidrati') {
                                grams = results.carboidrati;
                            } else if (label === 'Proteine') {
                                grams = results.proteine;
                            } else {
                                grams = results.grassi;
                            }

                            return `${label}: ${value} kcal (${percentage}%) - ${grams}g`;
                        }
                    }
                }
            }
        };

        // Crea il grafico
        this.macroChart = new Chart(chartCanvas, {
            type: 'doughnut',
            data: data,
            options: options
        });
    }

    async saveData() {
        try {
            showProgress();

            const formData = new FormData(this.form);
            const response = await fetch('/save_dieta', {
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
        } finally {
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
                data.tdee,
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

            // Macronutrienti - Aggiornati con animazioni
            this.animateValue('carboidrati_input', results.carboidrati);
            this.animateValue('proteine_input', results.proteine);
            this.animateValue('grassi_input', results.grassi);

            // Aggiorna i campi nascosti
            safeSetValue('carboidrati_hidden', results.carboidrati);
            safeSetValue('proteine_hidden', results.proteine);
            safeSetValue('grassi_hidden', results.grassi);

            // Usa i valori calcolati direttamente dalla funzione calculateMacros
            safeSetValue('carbo_kcal', results.carbCalories, true);
            safeSetValue('prot_kcal', results.proteinCalories, true);
            safeSetValue('grassi_kcal', results.fatCalories, true);

            // Mostra le percentuali dei macronutrienti
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

                // Aggiorna le informazioni sui macronutrienti
                this.updateMacroInfo(results, formData.dieta);

                // Aggiorna il grafico dei macronutrienti
                this.updateMacroChart(results);

                // Sincronizza i campi nascosti
                if (typeof synchronizeFields === 'function') {
                    synchronizeFields();
                }

                hideProgress();
            } catch (error) {
                console.error('Errore durante il calcolo:', error);
                hideProgress();
            }
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

    // Funzione globale per sincronizzare campi (retrocompatibilità)
    function synchronizeFields() {
        // Copia i valori dai campi visibili/disabilitati ai campi nascosti
        const bmiVisible = document.getElementById('bmi');
        const bmiHidden = document.getElementById('bmi_hidden');
        if (bmiVisible && bmiHidden) bmiHidden.value = bmiVisible.textContent;

        const pesoIdealeVisible = document.getElementById('peso_ideale');
        const pesoIdealeHidden = document.getElementById('peso_ideale_hidden');
        if (pesoIdealeVisible && pesoIdealeHidden) pesoIdealeHidden.value = pesoIdealeVisible.textContent;

        // Aggiungi altre sincronizzazioni qui
        const metaBasaleVisible = document.getElementById('meta_basale');
        const metaBasaleHidden = document.getElementById('meta_basale_hidden');
        if (metaBasaleVisible && metaBasaleHidden) metaBasaleHidden.value = metaBasaleVisible.textContent;

        const metaGiornalieroVisible = document.getElementById('meta_giornaliero');
        const metaGiornalieroHidden = document.getElementById('meta_giornaliero_hidden');
        if (metaGiornalieroVisible && metaGiornalieroHidden) metaGiornalieroHidden.value = metaGiornalieroVisible.textContent;

        const calorieGiornaliereVisible = document.getElementById('calorie_giornaliere');
        const calorieGiornaliereHidden = document.getElementById('calorie_giornaliere_hidden');
        if (calorieGiornaliereVisible && calorieGiornaliereHidden) calorieGiornaliereHidden.value = calorieGiornaliereVisible.textContent;

        const settimaneDietaVisible = document.getElementById('settimane_dieta');
        const settimaneDietaHidden = document.getElementById('settimane_dieta_hidden');
        if (settimaneDietaVisible && settimaneDietaHidden) settimaneDietaHidden.value = settimaneDietaVisible.textContent;

        const carboidratiVisible = document.getElementById('carboidrati_input');
        const carboidratiHidden = document.getElementById('carboidrati_hidden');
        if (carboidratiVisible && carboidratiHidden) carboidratiHidden.value = carboidratiVisible.textContent;

        const proteineVisible = document.getElementById('proteine_input');
        const proteineHidden = document.getElementById('proteine_hidden');
        if (proteineVisible && proteineHidden) proteineHidden.value = proteineVisible.textContent;

        const grassiVisible = document.getElementById('grassi_input');
        const grassiHidden = document.getElementById('grassi_hidden');
        if (grassiVisible && grassiHidden) grassiHidden.value = grassiVisible.textContent;
    }