import tkinter as tk
from tkinter import ttk, messagebox
from db import connect_to_db
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Funzione per recuperare le ricette dal database
def recupera_ricette():
    try:
        # Connessione al database PostgreSQL
        conn = connect_to_db()
        with conn.cursor() as cursor:
            cursor.execute("select id, nome_ricetta from dieta.ricetta a order by nome_ricetta asc")
            ricette = cursor.fetchall()
        return ricette
    finally:
        if conn is not None:
            conn.close()

# Funzione per recuperare gli ingredienti di una ricetta
def recupera_ingredienti(ricetta_id):
    try:
        # Connessione al database PostgreSQL
        conn = connect_to_db()
        with conn.cursor() as cursor:
            cursor.execute("select a.id, a.nome, qta from dieta.ingredienti_ricetta ir join dieta.alimento a on (ir.id_alimento = a.id ) where id_ricetta = %s order by a.nome asc", (ricetta_id,))
            ingredienti = cursor.fetchall()
        return ingredienti
    finally:
        if conn is not None:
            conn.close()

# Funzione per mostrare gli ingredienti della ricetta selezionata
def mostra_ingredienti(event):
    selezione = tree.selection()
    if selezione:
        item = tree.item(selezione)
        ricetta_id = item['values'][1]
        ingredienti = recupera_ingredienti(ricetta_id)
        #ingredienti_listbox.delete(0, tk.END)
        for widget in ingredienti_frame.winfo_children():
            widget.destroy()
        for ingrediente in ingredienti:
            ingrediente_frame = tk.Frame(ingredienti_frame)
            ingrediente_frame.pack(fill=tk.X)
            tk.Label(ingrediente_frame, text=ingrediente['nome']).pack(side=tk.LEFT, padx=10, pady=5)
            quantita_var = tk.StringVar(value=ingrediente['qta'])
            tk.Entry(ingrediente_frame, textvariable=quantita_var).pack(side=tk.LEFT, padx=10, pady=5)
            salva_button = tk.Button(ingrediente_frame, text="Salva",
                                     command=lambda id=ingrediente['id'], var=quantita_var: aggiorna_quantita(id, ricetta_id,
                                                                                                           var.get()))
            salva_button.pack(side=tk.LEFT, padx=10, pady=5)
            delete_button = tk.Button(ingrediente_frame, text="Elimina",
                                      command=lambda id=ingrediente['id']: delete_ingredient_and_refresh(id,
                                                                                                      ricetta_id))
            delete_button.pack(side=tk.LEFT, padx=10, pady=5)

            # Aggiungi un pulsante per aggiungere un nuovo ingrediente
        add_button = tk.Button(ingredienti_frame, text="Aggiungi Ingrediente",
                               command=lambda: show_add_ingredient_dialog(ricetta_id))
        add_button.pack(side=tk.BOTTOM, padx=10, pady=10)

def delete_ingredient_and_refresh(ingrediente_id, ricetta_id):
    delete_ingredient(ingrediente_id, ricetta_id)
    mostra_ingredienti(ricetta_id)

def aggiorna_quantita(id_ingrediente, id_ricetta, nuova_quantita):
    try:
        # Connessione al database PostgreSQL
        conn = connect_to_db()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE dieta.ingredienti_ricetta ir SET qta = %s WHERE id_alimento = %s and id_ricetta = %s", (int(nuova_quantita), id_ingrediente, id_ricetta))
        conn.commit()
    finally:
        if conn is not None:
            conn.close()

# Funzione per recuperare l'elenco degli alimenti
def fetch_alimenti():
    try:
        # Connessione al database PostgreSQL
        conn = connect_to_db(False)
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, nome FROM dieta.alimento")
            alimenti = cursor.fetchall()
        return alimenti
    finally:
        if conn is not None:
            conn.close()

def show_add_ingredient_dialog(ricetta_id):
    add_dialog = tk.Toplevel(root)
    add_dialog.title("Aggiungi Ingrediente")

    tk.Label(add_dialog, text="Nome Ingrediente:").pack(padx=10, pady=5)

    # Recupera gli alimenti dal database
    alimenti = fetch_alimenti()
    #print(alimenti)
    alimento_dict = {nome: id for id, nome in alimenti}
    nome_var = tk.StringVar()
    nome_combobox = ttk.Combobox(add_dialog, textvariable=nome_var, values=list(alimento_dict.keys()))
    nome_combobox.pack(padx=10, pady=5)

    tk.Label(add_dialog, text="Quantità:").pack(padx=10, pady=5)
    quantita_var = tk.DoubleVar()
    tk.Entry(add_dialog, textvariable=quantita_var).pack(padx=10, pady=5)

    save_button = tk.Button(add_dialog, text="Salva", command=lambda: save_new_ingredient(add_dialog, ricetta_id, alimento_dict[nome_var.get()], quantita_var.get()))
    save_button.pack(padx=10, pady=10)


def save_new_ingredient(add_dialog, ricetta_id, nome, quantita):
        if not nome:
            messagebox.showerror("Errore", "Il nome dell'ingrediente non può essere vuoto.")
            return

        #print(f"{ricetta_id}-{nome}-{quantita}")
        add_ingredient(ricetta_id, nome, quantita)
        add_dialog.destroy()
        mostra_ingredienti(ricetta_id)

def add_ingredient(ricetta_id, nome, quantita):
    try:
        # Connessione al database PostgreSQL
        conn = connect_to_db()
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO dieta.ingredienti_ricetta (id_ricetta, id_alimento, qta) VALUES (%s, %s, %s)", (ricetta_id, nome, quantita))

        conn.commit()
    finally:
        if conn is not None:
            conn.close()

def delete_ingredient(ingrediente_id, ricetta_id):
    try:
        # Connessione al database PostgreSQL
        conn = connect_to_db()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM dieta.ingredienti_ricetta WHERE id_alimento = %s and id_ricetta = %s", (ingrediente_id, ricetta_id,))

        conn.commit()
    finally:
        if conn is not None:
            conn.close()

def show_add_recipe_dialog():
    add_dialog = tk.Toplevel(root)
    add_dialog.title("Aggiungi Ricetta")

    tk.Label(add_dialog, text="Nome Ricetta:").pack(padx=10, pady=5)
    nome_var = tk.StringVar()
    tk.Entry(add_dialog, textvariable=nome_var).pack(padx=10, pady=5)

    colazione_var = tk.BooleanVar()
    spuntino_var = tk.BooleanVar()
    principale_var = tk.BooleanVar()
    contorno_var = tk.BooleanVar()
    colazione_sec_var = tk.BooleanVar()

    tk.Checkbutton(add_dialog, text="Colazione", variable=colazione_var).pack(padx=10, pady=5)
    tk.Checkbutton(add_dialog, text="Colazione Secondaria", variable=colazione_sec_var).pack(padx=10, pady=5)
    tk.Checkbutton(add_dialog, text="Principale", variable=principale_var).pack(padx=10, pady=5)
    tk.Checkbutton(add_dialog, text="Spuntino", variable=spuntino_var).pack(padx=10, pady=5)
    tk.Checkbutton(add_dialog, text="Contorno", variable=contorno_var).pack(padx=10, pady=5)

    save_button = tk.Button(add_dialog, text="Salva", command=lambda: save_new_recipe(add_dialog, nome_var.get(), colazione_var.get(), spuntino_var.get(), principale_var.get(), contorno_var.get(), colazione_sec_var.get()))
    save_button.pack(padx=10, pady=10)

# Funzione per salvare la nuova ricetta nel database
def save_new_recipe(add_dialog, nome, colazione, spuntino, principale, contorno, colazione_sec):
    if not nome:
        messagebox.showerror("Errore", "Il nome della ricetta non può essere vuoto.")
        return

    ricetta_id = add_recipe(nome, colazione, spuntino, principale, contorno, colazione_sec)
    if ricetta_id:
        add_dialog.destroy()
        refresh_recipes()

def refresh_recipes():
    for row in tree.get_children():
        tree.delete(row)
    recipes = recupera_ricette()
    for recipe in recipes:
        tree.insert('', 'end', values=(recipe[1], recipe[0]))

def add_recipe(nome, colazione, spuntino, principale, contorno, colazione_sec):
    conn = None
    try:
        # Connessione al database PostgreSQL
        conn = connect_to_db(False)
        with conn.cursor() as cursor:
            res = cursor.execute("""INSERT INTO dieta.ricetta (nome_ricetta, colazione, spuntino, principale, contorno, colazione_sec)
    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""", (nome, colazione, spuntino, principale, contorno, colazione_sec))

        conn.commit()

        return res[0][0] if res else None
    finally:
        if conn is not None:
            conn.close()


# Creazione della finestra principale
root = tk.Tk()
root.title("GESTIONE RICETTE")
root.geometry("1024x768")

# Creazione del frame sinistro per la tabella delle ricette
frame_sinistro = tk.Frame(root)
frame_sinistro.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Creazione del frame destro per gli ingredienti
frame_destro = tk.Frame(root)
frame_destro.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# Creazione della tabella delle ricette
tree = ttk.Treeview(frame_sinistro, columns=('Nome', 'ID'), show='headings')
tree.heading('Nome', text='Ricetta')
tree.heading('ID', text='ID')
tree.column('ID', width=0, stretch=tk.NO)
tree.pack(fill=tk.BOTH, expand=True)

# Inserimento delle ricette nella tabella
ricette = recupera_ricette()
for ricetta in ricette:
    tree.insert('', tk.END, values=(ricetta['nome_ricetta'], ricetta['id']))

# Associazione della funzione mostra_ingredienti all'evento di selezione
tree.bind('<<TreeviewSelect>>', mostra_ingredienti)

# Creazione dell'etichetta e del frame per gli ingredienti
label_ingredienti = tk.Label(frame_destro, text="LISTA INGREDIENTI RICETTA")
label_ingredienti.pack()
ingredienti_frame = tk.Frame(frame_destro)
ingredienti_frame.pack(fill=tk.BOTH, expand=True)

# Creazione del pulsante per aggiungere una nuova ricetta
add_recipe_button = tk.Button(frame_sinistro, text="Aggiungi Ricetta", command=show_add_recipe_dialog)
add_recipe_button.pack(pady=10)

# Avvio del loop principale di Tkinter
root.mainloop()
