import math

altezza = 166
peso = 77
sesso = 'M'
eta = 37

peso_ideale = altezza - 100 if sesso == 'M' else altezza - 104
metabolismo_basale = math.ceil(
    (655.095 + (9.563 * peso_ideale) + (1.8496 * altezza) - (4.6756 * eta)) if sesso == 'F' else (
            66.473 + ((13.7516 * peso_ideale) + (5.0033 * altezza) - (6.755 * eta))))
calorie = (peso_ideale * 30) if sesso == 'M' else (peso_ideale * 28)
kcal_giorn = (calorie - (calorie * 0.25)) if sesso == 'M' else (calorie - (calorie * 0.15))
print(f"metabolismo_basale::{metabolismo_basale}")
print(f"peso ideale::{peso_ideale}")
print(f"calorie giornaliere::{calorie}")
print(f"fabbisogno::{kcal_giorn}")
fabbisogno_proteine = math.ceil(peso_ideale * 1.125)
fabbisogno_grassi = math.ceil(((kcal_giorn * 0.25) / 9) if sesso == 'M' else ((kcal_giorn * 0.30) / 9))
kcal_proteine = fabbisogno_proteine * 4
kcal_grassi = fabbisogno_grassi * 9
kcal_carbo = kcal_giorn - kcal_proteine - kcal_grassi
fabbisogno_carboidrati = math.ceil(kcal_carbo / 4)
print(f"fabbisogno carboidrati::{fabbisogno_carboidrati}")
print(f"kcal carboidrati::{kcal_carbo}")
print(f"kcal proteine::{kcal_proteine}")
print(f"kcal grassi::{kcal_grassi}")
fabbisogno_calorico = 22 * peso * 1.3
print(f"fabbisogno iron manager::{fabbisogno_calorico}")
print(f"proteine im::{1.8*peso*4}")
print(f"grassi im::{0.8*peso*9}")
print(f"carbo im::{(fabbisogno_calorico-((1.8*peso*4)+(0.8*peso*9)))/4}")