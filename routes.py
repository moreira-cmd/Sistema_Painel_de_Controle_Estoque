import hashlib
import math

from flask import Blueprint, flash, redirect, render_template, request, url_for
import database
from pedidos import PedidoInvalido, extrair_texto, interpretar_pedido

main = Blueprint('main', __name__)


#-------------------------------------
#       PAINEL DE CONTROLE
#-------------------------------------

@main.route('/')
def dashboard():
    # Aqui você pode buscar dados do banco de dados usando a função get_metricas_dashboard()
    metricas = database.get_metricas_dashboard()
    criticos = database.get_produtos_estoque_baixo()[:5]  # Pega os 5 produtos com estoque baixo
    mensal = database.get_movimentacao_mensal(6)
    return render_template(
        'index.html',
        metricas = metricas,
        produtos_criticos = criticos,
        mensal = mensal,
        top = database.get_top_movimentados(5),
        valor_produtos = database.get_valor_por_produto(5),
        tem_movimentacao = any(mensal['entradas']) or any(mensal['saidas'])
    )
# ============================================================
# PRODUTOS
# ============================================================
@main.route('/produtos')
def lista_produtos():
    '''
    Lista Paginada de todos os produtos.
    
    parametros GET suportados:
        ?q=termo - filtro de busca por nome ou SKU
        ?pagina=N -numero da página (padrão: 1)
        '''
    #request.args le o parametros da URL (Query String)
    busca = request.args.get('q', '') # Pega o termo de busca da query string, padrão é ''
    pagina = request.args.get('pagina', 1, type=int) # Pega o número da página, padrão é 1
    por_pagina = 10 # Número de produtos por página

    produtos, total = database.get_todos_produtos(
        buscar=busca,
        pagina=pagina,
        por_pagina=por_pagina
    )
    #math.ceil arredonda para cima: 21 itens / 10 por página = 3 páginas
    total_paginas = math.ceil(total / por_pagina) if total > 0 else 1

    return render_template(
        'produtos/lista.html',
        produtos = produtos,
        busca = busca,
        pagina = pagina,
        total_paginas = total_paginas,
        total = total
    )
@main.route('/produtos/adicionar', methods=['GET', 'POST'])
def adicionar_produto():
    """GET - Exibe formulário de cadastro vazio
       POST - Valida os dados e cria o produto no banco de dados
       Padrão PRG (Post-Redirect-Get): após salva com sucesso, redirecionamos para
       evitar que o navegador reenvie o formulário ao recarregar a página.
    """
    if request.method == 'POST':
        
        # Coleta e Sanitiza os dados do formulário
        nome = request.form.get('nome', '').strip()
        #SKU sempre em maiúsculo para consistência
        sku = request.form.get('sku', '').strip().upper()
        descricao = request.form.get('descricao', '').strip()
        #Substitui vírgula por ponto para aceitar "1,99" e "1.99" como preço válido
        preco_str = request.form.get('preco', '0').replace(',', '.')
        quantidade_str = request.form.get('quantidade', '0')
        localizacao = request.form.get('localizacao', '').strip()
        custo_str = request.form.get('custo', '0').replace(',', '.') or '0'

        #---Validação dos dados---
        erros = []
        if not nome:
            erros.append('O Nome do produto é obrigatório.')
        if not sku:
            erros.append('O SKU do produto é obrigatório.')

        try:
            preco = float(preco_str)
            if preco < 0:
                erros.append('O preço não pode ser negativo.')
        except ValueError:
            erros.append("Formado de preço inválido. Use números (ex: 1.99 ou 1,99).")
            preco = 0.0
        try:
            custo = float(custo_str)
            if custo < 0:
                erros.append('O custo não pode ser negativo.')
        except ValueError:
            erros.append("Formato de custo inválido. Use números (ex: 1.99 ou 1,99).")
            custo = 0.0
        try:
            quantidade = int(quantidade_str)
            if quantidade < 0:
                erros.append('A quantidade não pode ser negativa.')
        except ValueError:
            erros.append("Formado de quantidade inválido. Use números inteiros.")
            quantidade = 0
        #---verifica unidade do SKU---
        if sku and database.get_produto_por_sku(sku):
            erros.append(
                f'Já existe um produto com o SKU "{sku}".'
            )
        if erros:
            for erro in erros:
                flash(erro, 'danger')
            # Reexibe o formulário com os dados preenchidos e mensagens de erro
            return render_template(
                'produtos/adicionar.html', form_data=request.form
            )

        

        #tudo validado - persiste no banco de dados
        database.criar_produto(nome, sku, descricao, preco, quantidade, localizacao, custo)
        flash(f'Produto "{nome}" adicionado com sucesso!', 'success')
        return redirect(url_for('main.lista_produtos'))

    return render_template('produtos/adicionar.html', form_data={})

@main.route('/produtos/editar/<int:id>', methods = ['GET', 'POST'])
def editar_produto(id):
    produto = database.get_produto_por_id(id)

    if not produto:
        flash(f'Produto com ID {id} não encontrado.', 'danger')
        return redirect(url_for('main.lista_produtos'))
    if request.method == 'POST':
        # Coleta e Sanitiza os dados do formulário
        nome = request.form.get('nome', '').strip()
        sku = request.form.get('sku', '').strip().upper()
        descricao = request.form.get('descricao', '').strip()
        preco_str = request.form.get('preco', '0').replace(',', '.')
        quantidade_str = request.form.get('quantidade', '0')
        localizacao = request.form.get('localizacao', '').strip()
        custo_str = request.form.get('custo', '0').replace(',', '.') or '0'

        erros = []

        if not nome:
            erros.append("O nome do produto é obrigatório.")
        if not sku:
            erros.append("O SKU é obrigatório.")

        try:
            preco = float(preco_str)
            if preco < 0:
                erros.append("O preço não pode ser negativo.")
        except ValueError:
            erros.append("Formato de preço inválido.")
            preco = 0.0

        try:
            custo = float(custo_str)
            if custo < 0:
                erros.append("O custo não pode ser negativo.")
        except ValueError:
            erros.append("Formato de custo inválido.")
            custo = 0.0

        try:
            quantidade = int(quantidade_str)
            if quantidade < 0:
                erros.append("A quantidade não pode ser negativa.")
        except ValueError:
            erros.append("A quantidade deve ser um número inteiro.")
            quantidade = 0
         # Na edição, excluímos o próprio produto da verificação de SKU
        if sku and database.get_produto_por_sku(sku, excluir_id=id):
            erros.append(f"O SKU '{sku}' já pertence a outro produto.")
        if erros:
            for erro in erros:
                flash(erro, 'danger')
            return render_template(
                'produtos/editar.html',
                produto=produto,
                form_data=request.form
            )

        database.atualizar_produto(id, nome, sku, descricao, preco, quantidade, localizacao, custo)
        flash(f"Produto '{nome}' atualizado com sucesso!", 'success')
        return redirect(url_for('main.lista_produtos'))
     # GET → preenche o formulário com os dados atuais
    return render_template(
        'produtos/editar.html',
        produto=produto,
        form_data=produto  # sqlite3.Row se comporta como dict no template
    )

@main.route('/produtos/deletar/<int:id>', methods=['POST'])
def deletar_produto(id):
    produto = database.get_produto_por_id(id)
    if produto:
        nome = produto['nome']
        database.get_deletar_produto(id)
        flash(f"Produto '{nome}' excluído com sucesso.", 'success')
    else:
        flash("Produto não encontrado.", 'danger')

    return redirect(url_for('main.lista_produtos'))


#--------------------------------------------------
#          Relatório: Estoque Baixo
#--------------------------------------------------
@main.route('/relatorios/estoque-baixo')
def relatorio_estoque_baixo():
    produtos = database.get_produtos_estoque_baixo()
    return render_template(
        'relatorios/estoque_baixo.html',
        produtos = produtos,
        limiar=database.LIMIAR_ESTOQUE_BAIXO
    )

# ============================================================
# TRANSAÇÃO DE ESTOQUE
# ============================================================

@main.route('/produtos/<int:id>/transacao', methods=['GET', 'POST'])
def transacao_estoque(id):
    """
    Permite registrar movimentações rápidas de estoque:
    - Entrada: produto chegou (compra/recebimento)
    - Saída: produto saiu (venda/consumo/perda)

    Mais prático que abrir o formulário de edição completo.
    """
    produto = database.get_produto_por_id(id)

    if not produto:
        flash("Produto não encontrado.", 'danger')
        return redirect(url_for('main.lista_produtos'))

    if request.method == 'POST':
        tipo = request.form.get('tipo')  # 'entrada' ou 'saida'
        quantidade_str = request.form.get('quantidade', '0')

        try:
            quantidade = int(quantidade_str)
            if quantidade <= 0:
                raise ValueError("Deve ser positivo")
        except ValueError:
            flash(
                "Informe uma quantidade válida (número inteiro maior que zero).",
                'danger'
            )
            return render_template('produtos/transacao.html', produto=produto)

        sucesso, mensagem = database.registrar_transacao(id, tipo, quantidade)

        if sucesso:
            flash(mensagem, 'success')
            return redirect(url_for('main.lista_produtos'))
        else:
            flash(mensagem, 'danger')

    return render_template('produtos/transacao.html', produto=produto)


# ============================================================
# PEDIDOS EM PDF
# ============================================================

@main.route('/pedidos/importar', methods=['GET', 'POST'])
def importar_pedido():
    """
    GET  - Tela para enviar o PDF do pedido.
    POST - Lê o PDF e MOSTRA o que seria baixado do estoque (nada é alterado ainda).
           A baixa só acontece em /pedidos/confirmar, depois que a pessoa conferir.
    """
    if request.method == 'GET':
        return render_template('pedidos/importar.html')

    arquivo = request.files.get('pdf')
    if not arquivo or not arquivo.filename:
        flash('Selecione um arquivo PDF.', 'danger')
        return redirect(url_for('main.importar_pedido'))
    if not arquivo.filename.lower().endswith('.pdf'):
        flash('O arquivo precisa ser um PDF (.pdf).', 'danger')
        return redirect(url_for('main.importar_pedido'))

    conteudo = arquivo.read()
    try:
        texto = extrair_texto(conteudo)
    except PedidoInvalido as erro:
        flash(str(erro), 'danger')
        return redirect(url_for('main.importar_pedido'))

    if not texto.strip():
        flash('Esse PDF não tem texto selecionável (parece escaneado/imagem). '
              'Use um PDF gerado pelo sistema de pedidos.', 'danger')
        return redirect(url_for('main.importar_pedido'))

    hash_pdf = hashlib.sha256(conteudo).hexdigest()
    itens, ignoradas = interpretar_pedido(texto, database.get_mapa_de_skus())

    return render_template(
        'pedidos/importar.html',
        itens=itens,
        ignoradas=ignoradas,
        arquivo_nome=arquivo.filename,
        arquivo_hash=hash_pdf,
        ja_importado=database.get_pedido_importado(hash_pdf)
    )


@main.route('/pedidos/confirmar', methods=['POST'])
def confirmar_pedido():
    """Aplica as saídas do pedido conferido. Cada item é validado de novo aqui (não confiamos no navegador)."""
    hash_pdf = request.form.get('hash', '')
    nome_arquivo = request.form.get('arquivo', '')

    if hash_pdf and database.get_pedido_importado(hash_pdf):
        flash('Esse PDF já foi importado antes. Nada foi alterado.', 'danger')
        return redirect(url_for('main.importar_pedido'))

    skus = request.form.getlist('sku')
    quantidades = request.form.getlist('qtd')
    baixados = 0
    falhas = []

    for sku, qtd_str in zip(skus, quantidades):
        produto = database.get_produto_por_sku(sku.strip().upper())
        try:
            qtd = int(qtd_str)
        except ValueError:
            qtd = 0
        if not produto or qtd <= 0:
            falhas.append(f'{sku}: item inválido.')
            continue
        sucesso, mensagem = database.registrar_transacao(produto['id'], 'saida', qtd, origem='pedido_pdf')
        if sucesso:
            baixados += 1
        else:
            falhas.append(f'{produto["nome"]} ({sku}): {mensagem}')

    if baixados:
        if hash_pdf:
            database.registrar_pedido_importado(hash_pdf, nome_arquivo)
        flash(f'Pedido importado: {baixados} produto(s) baixado(s) do estoque.', 'success')
    for falha in falhas:
        flash(falha, 'danger')

    return redirect(url_for('main.lista_produtos'))
