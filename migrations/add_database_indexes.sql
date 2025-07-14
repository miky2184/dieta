-- Database performance optimization indexes
-- Add indexes for frequently queried fields

-- Index for Utente table - email lookups
CREATE INDEX IF NOT EXISTS idx_utente_email ON dieta.utente(email);

-- Index for UtenteAuth table - username lookups  
CREATE INDEX IF NOT EXISTS idx_utente_auth_username ON dieta.utente_auth(username);

-- Index for MenuSettimanale table - user_id and date range queries
CREATE INDEX IF NOT EXISTS idx_menu_settimanale_user_id ON dieta.menu_settimanale(user_id);
CREATE INDEX IF NOT EXISTS idx_menu_settimanale_date_range ON dieta.menu_settimanale(data_inizio, data_fine);
CREATE INDEX IF NOT EXISTS idx_menu_settimanale_user_date ON dieta.menu_settimanale(user_id, data_inizio, data_fine);

-- Index for RegistroPeso table - user_id and date queries
CREATE INDEX IF NOT EXISTS idx_registro_peso_user_id ON dieta.registro_peso(user_id);
CREATE INDEX IF NOT EXISTS idx_registro_peso_date ON dieta.registro_peso(data_rilevazione);
CREATE INDEX IF NOT EXISTS idx_registro_peso_user_date ON dieta.registro_peso(user_id, data_rilevazione);

-- Index for IngredientiRicetta table - composite primary key queries
CREATE INDEX IF NOT EXISTS idx_ingredienti_ricetta_ricetta_base ON dieta.ingredienti_ricetta(id_ricetta_base);
CREATE INDEX IF NOT EXISTS idx_ingredienti_ricetta_alimento_base ON dieta.ingredienti_ricetta(id_alimento_base);
CREATE INDEX IF NOT EXISTS idx_ingredienti_ricetta_user_id ON dieta.ingredienti_ricetta(user_id);

-- Index for frequently used view queries (VRicetta, VAlimento, VIngredientiRicetta)
-- Note: These are views, but we can index the underlying tables

-- Index for ricetta_base table
--CREATE INDEX IF NOT EXISTS idx_ricetta_base_enabled ON dieta.ricetta_base(enabled);
CREATE INDEX IF NOT EXISTS idx_ricetta_base_complemento ON dieta.ricetta_base(complemento);
CREATE INDEX IF NOT EXISTS idx_ricetta_base_contorno ON dieta.ricetta_base(contorno);

-- Index for alimento_base table
CREATE INDEX IF NOT EXISTS idx_alimento_base_nome ON dieta.alimento_base(nome);
CREATE INDEX IF NOT EXISTS idx_alimento_base_id_gruppo ON dieta.alimento_base(id_gruppo);

-- Index for ingredienti_ricetta_base table
CREATE INDEX IF NOT EXISTS idx_ingredienti_ricetta_base_ricetta ON dieta.ingredienti_ricetta_base(id_ricetta);
CREATE INDEX IF NOT EXISTS idx_ingredienti_ricetta_base_alimento ON dieta.ingredienti_ricetta_base(id_alimento);

-- Index for ricetta table (user customizations)
CREATE INDEX IF NOT EXISTS idx_ricetta_user_id ON dieta.ricetta(user_id);
--CREATE INDEX IF NOT EXISTS idx_ricetta_id_ricetta_base ON dieta.ricetta(id_ricetta_base);

-- Index for alimento table (user customizations)
CREATE INDEX IF NOT EXISTS idx_alimento_user_id ON dieta.alimento(user_id);
--CREATE INDEX IF NOT EXISTS idx_alimento_id_alimento_base ON dieta.alimento(id_alimento_base);

-- Composite indexes for complex queries
--CREATE INDEX IF NOT EXISTS idx_menu_settimanale_current_week ON dieta.menu_settimanale(user_id, data_fine) WHERE data_fine >= CURRENT_DATE;

-- Partial indexes for performance
--CREATE INDEX IF NOT EXISTS idx_ricetta_base_active_recipes ON dieta.ricetta_base(id, nome) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_ingredienti_ricetta_not_removed ON dieta.ingredienti_ricetta(id_ricetta_base, id_alimento_base) WHERE removed = false OR removed IS NULL;

-- Analyze tables after index creation for better query planning
ANALYZE dieta.utente;
ANALYZE dieta.utente_auth;
ANALYZE dieta.menu_settimanale;
ANALYZE dieta.registro_peso;
ANALYZE dieta.ingredienti_ricetta;
ANALYZE dieta.ricetta_base;
ANALYZE dieta.alimento_base;
ANALYZE dieta.ingredienti_ricetta_base;
ANALYZE dieta.ricetta;
ANALYZE dieta.alimento;