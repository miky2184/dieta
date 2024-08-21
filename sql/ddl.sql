-- dieta.alimento definition

-- Drop table

-- DROP TABLE dieta.alimento;

CREATE TABLE dieta.alimento (
	id bigserial NOT NULL,
	nome varchar(200) NULL,
	carboidrati numeric NULL,
	proteine numeric NULL,
	grassi numeric NULL,
	kcal numeric GENERATED ALWAYS AS (carboidrati * 4::numeric + proteine * 4::numeric + grassi * 9::numeric) STORED NULL,
	macro varchar(1) GENERATED ALWAYS AS (
CASE
    WHEN (carboidrati * 4::numeric) >= (proteine * 4::numeric) AND (carboidrati * 4::numeric) >= (grassi * 9::numeric) THEN 'C'::text
    WHEN (proteine * 4::numeric) >= (carboidrati * 4::numeric) AND (proteine * 4::numeric) >= (grassi * 9::numeric) THEN 'P'::text
    WHEN (grassi * 9::numeric) >= (proteine * 4::numeric) AND (grassi * 9::numeric) >= (carboidrati * 4::numeric) THEN 'G'::text
    ELSE NULL::text
END) STORED NULL,
	frutta bool DEFAULT false NULL,
	carne_bianca bool DEFAULT false NULL,
	carne_rossa bool DEFAULT false NULL,
	pane bool DEFAULT false NULL,
	stagionalita _int8 NULL,
	verdura bool DEFAULT false NULL,
	confezionato bool DEFAULT false NULL,
	vegan bool DEFAULT false NULL,
	pesce bool DEFAULT false NULL,
	CONSTRAINT alimento_pkey PRIMARY KEY (id)
);

-- dieta.dieta definition

-- Drop table

-- DROP TABLE dieta.dieta;

CREATE TABLE dieta.dieta (
	alimento varchar(50) NULL,
	kcal varchar(50) NULL,
	carboidrati varchar(50) NULL,
	proteine varchar(50) NULL,
	grassi varchar(50) NULL,
	qta int4 NULL,
	ricetta bool NULL
);

-- dieta.ricetta definition

-- Drop table

-- DROP TABLE dieta.ricetta;

CREATE TABLE dieta.ricetta (
	id bigserial NOT NULL,
	nome_ricetta text NULL,
	colazione bool DEFAULT false NULL,
	spuntino bool DEFAULT false NULL,
	principale bool DEFAULT false NULL,
	contorno bool DEFAULT false NULL,
	enabled bool DEFAULT true NULL,
	colazione_sec bool DEFAULT false NULL,
	CONSTRAINT ricetta_pkey PRIMARY KEY (id)
);

-- dieta.ingredienti_ricetta definition

-- Drop table

-- DROP TABLE dieta.ingredienti_ricetta;

CREATE TABLE dieta.ingredienti_ricetta (
	id_ricetta int8 NOT NULL,
	id_alimento int8 NOT NULL,
	qta numeric NULL,
	CONSTRAINT ingredienti_ricetta_pk PRIMARY KEY (id_ricetta, id_alimento)
);


-- dieta.ingredienti_ricetta foreign keys

ALTER TABLE dieta.ingredienti_ricetta ADD CONSTRAINT id_alimento FOREIGN KEY (id_alimento) REFERENCES dieta.alimento(id);
ALTER TABLE dieta.ingredienti_ricetta ADD CONSTRAINT id_ricetta FOREIGN KEY (id_ricetta) REFERENCES dieta.ricetta(id);

-- dieta.menu_settimanale definition

-- Drop table

-- DROP TABLE dieta.menu_settimanale;

CREATE TABLE dieta.menu_settimanale (
	id serial4 NOT NULL,
	data_inizio date NOT NULL,
	data_fine date NOT NULL,
	menu jsonb NOT NULL,
	CONSTRAINT menu_settimanale_data_inizio_data_fine_key UNIQUE (data_inizio, data_fine),
	CONSTRAINT menu_settimanale_pkey PRIMARY KEY (id)
);

-- dieta.registro_peso definition

-- Drop table

-- DROP TABLE dieta.registro_peso;

CREATE TABLE dieta.registro_peso (
	data_rilevazione date NOT NULL,
	peso numeric NULL,
	CONSTRAINT registro_peso_pk PRIMARY KEY (data_rilevazione)
);


-- dieta.utenti definition

-- Drop table

-- DROP TABLE dieta.utenti;

CREATE TABLE dieta.utenti (
	id serial4 NOT NULL,
	nome varchar(255) NOT NULL,
	cognome varchar(255) NOT NULL,
	sesso bpchar(1) NULL,
	eta int4 NULL,
	altezza numeric(5, 2) NULL,
	peso numeric(5, 2) NULL,
	tdee numeric(4, 3) NULL,
	deficit_calorico numeric(5, 2) NULL,
	bmi numeric(5, 2) NULL,
	peso_ideale numeric(5, 2) NULL,
	meta_basale numeric(8, 2) NULL,
	meta_giornaliero numeric(8, 2) NULL,
	calorie_giornaliere numeric(8, 2) NULL,
	calorie_settimanali numeric(8, 2) NULL,
	carboidrati int4 NULL,
	proteine int4 NULL,
	grassi int4 NULL,
	CONSTRAINT utenti_pkey PRIMARY KEY (id),
	CONSTRAINT utenti_sesso_check CHECK ((sesso = ANY (ARRAY['M'::bpchar, 'F'::bpchar])))
);