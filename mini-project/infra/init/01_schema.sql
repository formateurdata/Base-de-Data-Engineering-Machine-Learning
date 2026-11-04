-- Table source du projet. Les contraintes font de la base la dernière ligne de défense de la qualité des données.
-- clock_timestamp() et non now() : now() donnerait la même heure à toutes les lignes d'un lot.
CREATE TABLE commandes (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_id  INTEGER NOT NULL CHECK (client_id > 0),
    produit    TEXT NOT NULL CHECK (produit <> ''),
    quantite   INTEGER NOT NULL CHECK (quantite > 0),
    montant    NUMERIC(10, 2) NOT NULL CHECK (montant >= 0),
    statut     TEXT NOT NULL CHECK (statut IN ('payee', 'expediee', 'annulee', 'remboursee')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- L'extraction incrémentale filtrera sur updated_at
CREATE INDEX commandes_updated_at_idx ON commandes (updated_at, id);

-- Toute modification avance updated_at : sans cela, l'extraction incrémentale manquerait les lignes modifiées
CREATE FUNCTION maj_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := clock_timestamp();
    RETURN NEW;
END;
$$;

CREATE TRIGGER commandes_updated_at BEFORE UPDATE ON commandes
    FOR EACH ROW EXECUTE FUNCTION maj_updated_at();
