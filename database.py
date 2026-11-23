import sqlite3
from datetime import date

Database = "estoque.db" # define o nome do arquivo do banco de dados SQLite.
LIMIAR_ESTOQUE_BAIXO = 200 # define o limiar de estoque baixo para alertas de estoque baixos. 

def get_db_connection():                    #essa função cria uma conexão com o banco de dados SQLite e define a fábrica de linhas para sqlite3.Row, 
                                            #permitindo acessar os resultados das consultas como dicionários.
    conn = sqlite3.connect(Database)
    conn.row_factory = sqlite3.Row
    return conn

def _migrar(conn):
    # Bancos criados antes desta versão não têm a coluna "custo" (usada para calcular o lucro).
    # CREATE TABLE IF NOT EXISTS não altera uma tabela que já existe, então adicionamos a coluna aqui.
    colunas = [c['name'] for c in conn.execute('PRAGMA table_info(produtos)')]
    if 'custo' not in colunas:
        conn.execute('ALTER TABLE produtos ADD COLUMN custo REAL NOT NULL DEFAULT 0')

def init_db():                                              #essa função inicializa o banco de dados executando o script SQL contido no arquivo 'schema.sql', 
    conn = get_db_connection()                              #essa função "init_db" é responsável por criar as tabelas e estruturas necessárias no banco de dados.
    with open('schema.sql', 'r', encoding='utf-8') as f:    
#essa função abre o arquivo 'schema.sql' em modo de leitura e com codificação UTF-8, lê o conteúdo do arquivo e executa o script SQL contido nele no banco de dados.
        conn.executescript(f.read())
    _migrar(conn)
    conn.commit()
    conn.close()
    print("Banco de Dados inicializado.")

#----------------------------------------------------------
#                        PRODUTOS
#----------------------------------------------------------

def criar_produto(nome, sku, descricao, preco, quantidade, localizacao, custo=0.0):
    #---Cria um novo produto no banco de dados.---
    conn = get_db_connection()
    conn.execute('''INSERT INTO produtos 
    (nome, sku, descricao, preco, quantidade, localizacao, custo) 
    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (nome, sku, descricao, preco, quantidade, localizacao, custo))
    conn.commit()
    conn.close()

def atualizar_produto(id, nome, sku, descricao, preco, quantidade, localizacao, custo=0.0):       #essa função atualiza os detalhes de um produto 
    conn = get_db_connection()                                                         #existente no banco de dados com base no ID fornecido.
    conn.execute(
        '''UPDATE produtos 
            SET nome = ?, sku = ?, descricao = ?, preco = ?,
            quantidade = ?, localizacao = ?, custo = ?
            WHERE id = ?''',
        (nome, sku, descricao, preco, quantidade, localizacao, custo, id))
    conn.commit()
    conn.close()
def get_todos_produtos(buscar=None, pagina=1, por_pagina=10):
     #essa função retorna uma lista de produtos do banco de dados, com suporte a pesquisa e paginação.
    '''
    Lista de Produtos com suporte a pesquisa e paginação.
    
    Paginação funciona com LIMIT (quantos itens) e OFFSET (apartir de qual item). Por exemplo, se você quiser 10 itens por página e 
    estiver na página 2, o OFFSET será 10 (porque a primeira página tem os primeiros 10 itens):
    Página 2, 10 itens por página = LIMIT 10 OFFSET 10.
    Página 3, 10 itens por página = LIMIT 10 OFFSET 20...
    
    :param busca: Termo de pesquisa para filtrar produtos - String de filtro (nome ou SKU); None = sem filtro.
    :param pagina: Número da página a ser exibida (começa em 1).
    :param por_pagina: Número de itens por página.
    :return: Tupla (lista_produtos, total_produtos) contendo a lista de produtos e o total de produtos encontrados.
    '''
    conn = get_db_connection()
    offset = (pagina - 1) * por_pagina

    if buscar:
        #0% no LIKE é o curinga do SQL: "cam%" - começa com "cam", "%cam" - termina com "cam",
        #  "%cam%" - contém "cam" em qualquer lugar 
        filtro = f"%{buscar}%"
        produtos = conn.execute('''SELECT * FROM produtos 
                                   WHERE nome LIKE ? OR sku LIKE ? 
                                   ORDER BY nome ASC
                                   LIMIT ? OFFSET ?''',
                                    (filtro, filtro, por_pagina, offset)
        ).fetchall()
        total = conn.execute(
                    'SELECT COUNT(*) FROM produtos WHERE nome LIKE ? OR sku LIKE ?', 
                    (filtro, filtro)
                ).fetchone()[0]
    else:
        produtos = conn.execute(
            '''SELECT * FROM produtos
                ORDER BY nome ASC
                LIMIT ? OFFSET ?''',
            (por_pagina, offset)
        ).fetchall()
        
        total = conn.execute(
            'SELECT COUNT(*) FROM produtos'
            ).fetchone()[0]

    conn.close()
    return produtos, total

def get_produto_por_id(id):
    '''Retorna um produto pelo seu ID, retorna None se não encontrado.'''
    conn = get_db_connection()
    produto = conn.execute('SELECT * FROM produtos WHERE id = ?', (id,)
    ).fetchone()
    conn.close()
    return produto

def get_produto_por_sku(sku, excluir_id=None):
    '''
    Verifica se um SKU já existe no banco de dados.
    excluir_id é usado na edição: ignoramos o próprio produto ao checar duplicada de SKU.
    '''
    conn = get_db_connection()
    if excluir_id:
        produto = conn.execute(
            'SELECT * FROM produtos WHERE sku = ? AND id != ?', 
            (sku, excluir_id)
        ).fetchone()
    else:
        produto = conn.execute(
            'SELECT * FROM produtos WHERE sku = ?', 
            (sku,)
        ).fetchone()
    conn.close()
    return produto

def get_produtos_estoque_baixo():
    '''
    Retorna todos os produtos com quantidade abaixo do limiar_estoque_baixo,
    ordenados pelo mais critico (menor quantidade)para o menos critico (maior quantidade).
    '''
    conn = get_db_connection()
    produtos = conn.execute(
        '''SELECT * FROM produtos WHERE quantidade < ? 
        ORDER BY quantidade ASC''',
        (LIMIAR_ESTOQUE_BAIXO,)
    ).fetchall()
    conn.close()
    return produtos

def get_deletar_produto(produto_id):
    '''Remove PERMANENTEMENTE um produto do banco de dados usando o id do produto.'''
    conn = get_db_connection()
    conn.execute(
        'DELETE FROM produtos WHERE id = ?', (produto_id,))
    conn.commit()
    conn.close()

    #----------------------------------------------------------
    #                 DASHBOARD / MÉTRICAS
    #----------------------------------------------------------
def get_metricas_dashboard():
    '''
    Retorna métricas de um dicionario, incluindo:
    -Total de produtos
    -Total de produtos com estoque baixo
    -Valor total do estoque (soma de quantidade * preço)
    '''
    conn = get_db_connection()
    total_produtos = conn.execute(
        'SELECT COUNT(*) FROM produtos'
    ).fetchone()[0]

    total_estoque_baixo = conn.execute(
        'SELECT COUNT(*) FROM produtos WHERE quantidade < ?',
        (LIMIAR_ESTOQUE_BAIXO,)
    ).fetchone()[0]
#  SUM pode retorna None se não houver produtos, então usamos fetchall()[0] e tratamos None como 0.0
    valor_total_estoque = conn.execute(
        'SELECT SUM(quantidade * preco) FROM produtos'
    ).fetchone()[0] or 0.0

    # Faturamento e lucro do mês atual (só contam as SAÍDAS)
    faturamento_mes, lucro_mes = conn.execute(
        '''SELECT COALESCE(SUM(quantidade * preco_unitario), 0),
                  COALESCE(SUM(quantidade * (preco_unitario - custo_unitario)), 0)
           FROM movimentacoes
           WHERE tipo = 'saida'
             AND strftime('%Y-%m', data) = strftime('%Y-%m', 'now', 'localtime')'''
    ).fetchone()

    conn.close()
    return {
        'total_produtos': total_produtos,
        'total_estoque_baixo': total_estoque_baixo,
        'valor_total_estoque': valor_total_estoque,
        'faturamento_mes': faturamento_mes,
        'lucro_mes': lucro_mes
    }

#----------------------------------------------------------
#                 TRNASAÇÕES DE ESTOQUE
#----------------------------------------------------------
def registrar_transacao(produto_id, tipo, quantidade_transacao, origem='manual'):
    """Registra uma Movimentação de Estoque (entrada ou saída).
    valida se ha quantidade suficiente antes de subtrair a quantidade em caso de saída.
    
    :param tipo: 'entrada' (recebimento) ou 'saida' (venda/consumo).
    :param quantidade_transacao: Quantidade a se movimentar (sempre positiva).
    :return: Tupla (sucesso bool, mensagem str) indicando se a transação foi bem-sucedida e uma mensagem de status.
    """
    conn = get_db_connection()

    produto = conn.execute(
        'SELECT quantidade, nome, preco, custo FROM produtos WHERE id = ?', 
        (produto_id,)
    ).fetchone()

    if not produto:
        conn.close()
        return False, "produto não encontrado."

    estoque_atual = produto['quantidade']

    if tipo == 'entrada':
        novo_estoque = estoque_atual + quantidade_transacao
        msg_tipo = 'Entrada'
    elif tipo == 'saida':
        # Regra de negocio: não permitir estoque negativo
        if quantidade_transacao > estoque_atual:
            conn.close()
            return(False, f"Estoque insuficiente. Estoque atual: {estoque_atual} unidades.")
        novo_estoque = estoque_atual - quantidade_transacao
        msg_tipo = 'Saída'
    else:
        conn.close()
        return False, "Tipo de trnsação inválido."
    conn.execute(
        'UPDATE produtos SET quantidade = ? WHERE id = ?',
        (novo_estoque, produto_id)
    )
    # Guarda no histórico (alimenta gráficos, mais movimentados e lucro)
    conn.execute(
        '''INSERT INTO movimentacoes
           (produto_id, tipo, quantidade, preco_unitario, custo_unitario, origem)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (produto_id, tipo, quantidade_transacao, produto['preco'], produto['custo'], origem)
    )
    conn.commit()
    conn.close()

    return (
        True,
          f"{msg_tipo} de {quantidade_transacao} unidade(s) registrada(s)."
          f"Novo Estoque: {novo_estoque} Unidades."
    )


#----------------------------------------------------------
#                 GRÁFICOS / RELATÓRIOS
#----------------------------------------------------------
NOMES_MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
               'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

def _ultimos_meses(n):
    '''Retorna os últimos n meses como "AAAA-MM", do mais antigo ao atual.'''
    hoje = date.today()
    ano, mes = hoje.year, hoje.month
    meses = []
    for _ in range(n):
        meses.append(f"{ano:04d}-{mes:02d}")
        mes -= 1
        if mes == 0:
            mes, ano = 12, ano - 1
    return meses[::-1]

def get_movimentacao_mensal(meses=6):
    '''
    Entradas, saídas (unidades), faturamento e lucro (R$) por mês, nos últimos `meses` meses.
    Meses sem movimentação aparecem zerados, para o gráfico não "pular" meses.
    '''
    lista = _ultimos_meses(meses)
    conn = get_db_connection()
    linhas = conn.execute(
        '''SELECT strftime('%Y-%m', data) AS mes,
                  SUM(CASE WHEN tipo = 'entrada' THEN quantidade ELSE 0 END) AS entradas,
                  SUM(CASE WHEN tipo = 'saida'   THEN quantidade ELSE 0 END) AS saidas,
                  SUM(CASE WHEN tipo = 'saida' THEN quantidade * preco_unitario ELSE 0 END) AS faturamento,
                  SUM(CASE WHEN tipo = 'saida' THEN quantidade * (preco_unitario - custo_unitario) ELSE 0 END) AS lucro
           FROM movimentacoes
           WHERE strftime('%Y-%m', data) >= ?
           GROUP BY mes''',
        (lista[0],)
    ).fetchall()
    conn.close()

    por_mes = {l['mes']: l for l in linhas}
    resultado = {'meses': [], 'entradas': [], 'saidas': [], 'faturamento': [], 'lucro': []}
    for m in lista:
        l = por_mes.get(m)
        resultado['meses'].append(f"{NOMES_MESES[int(m[5:]) - 1]}/{m[:4]}")
        resultado['entradas'].append(l['entradas'] if l else 0)
        resultado['saidas'].append(l['saidas'] if l else 0)
        resultado['faturamento'].append(round(l['faturamento'], 2) if l else 0)
        resultado['lucro'].append(round(l['lucro'], 2) if l else 0)
    return resultado

def get_top_movimentados(limite=5):
    '''Produtos com mais unidades movimentadas (entradas + saídas).'''
    conn = get_db_connection()
    linhas = conn.execute(
        '''SELECT p.nome AS nome, SUM(m.quantidade) AS total
           FROM movimentacoes m
           JOIN produtos p ON p.id = m.produto_id
           GROUP BY m.produto_id
           ORDER BY total DESC
           LIMIT ?''',
        (limite,)
    ).fetchall()
    conn.close()
    return {'nomes': [l['nome'] for l in linhas], 'totais': [l['total'] for l in linhas]}

def get_valor_por_produto(limite=5):
    '''Valor em estoque (quantidade x preço) dos maiores produtos; o resto vira "Outros".'''
    conn = get_db_connection()
    linhas = conn.execute(
        '''SELECT nome, quantidade * preco AS valor FROM produtos
           WHERE quantidade * preco > 0
           ORDER BY valor DESC LIMIT ?''',
        (limite,)
    ).fetchall()
    total = conn.execute('SELECT COALESCE(SUM(quantidade * preco), 0) FROM produtos').fetchone()[0]
    conn.close()
    nomes = [l['nome'] for l in linhas]
    valores = [round(l['valor'], 2) for l in linhas]
    outros = round(total - sum(valores), 2)
    if outros > 0.01:
        nomes.append('Outros')
        valores.append(outros)
    return {'nomes': nomes, 'valores': valores}


#----------------------------------------------------------
#                 PEDIDOS EM PDF
#----------------------------------------------------------
def get_mapa_de_skus():
    '''Retorna {SKU_MAIÚSCULO: produto} de todos os produtos (usado para reconhecer itens no PDF).'''
    conn = get_db_connection()
    linhas = conn.execute('SELECT * FROM produtos').fetchall()
    conn.close()
    return {l['sku'].upper(): l for l in linhas}

def get_pedido_importado(hash_pdf):
    '''Retorna o registro se esse PDF já foi importado antes, senão None.'''
    conn = get_db_connection()
    pedido = conn.execute('SELECT * FROM pedidos_importados WHERE hash = ?', (hash_pdf,)).fetchone()
    conn.close()
    return pedido

def registrar_pedido_importado(hash_pdf, arquivo):
    conn = get_db_connection()
    conn.execute('INSERT OR IGNORE INTO pedidos_importados (hash, arquivo) VALUES (?, ?)',
                 (hash_pdf, arquivo))
    conn.commit()
    conn.close()
