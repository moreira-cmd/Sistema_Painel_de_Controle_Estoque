CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome   TEXT NOT NULL,
    sku  TEXT UNIQUE NOT NULL,
    descricao TEXT,
    preco  REAL NOT NULL CHECK (preco >= 0),
    quantidade INT NOT NULL DEFAULT 0 CHECK (quantidade >= 0),
    localizacao TEXT,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    custo REAL NOT NULL DEFAULT 0 CHECK (custo >= 0)
);

-- Histórico de entradas e saídas (base dos gráficos e do lucro).
-- preco_unitario e custo_unitario guardam o valor NO MOMENTO da movimentação,
-- assim o lucro de meses antigos não muda se o preço do produto mudar depois.
CREATE TABLE IF NOT EXISTS movimentacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unitario REAL NOT NULL DEFAULT 0,
    custo_unitario REAL NOT NULL DEFAULT 0,
    origem TEXT NOT NULL DEFAULT 'manual',
    data TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- PDFs de pedidos já importados (evita baixar o mesmo pedido duas vezes).
CREATE TABLE IF NOT EXISTS pedidos_importados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT UNIQUE NOT NULL,
    arquivo TEXT,
    data TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
