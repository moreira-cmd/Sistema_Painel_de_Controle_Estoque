import re
from io import BytesIO

from pypdf import PdfReader


class PedidoInvalido(Exception):
    '''Erro ao ler o PDF (arquivo corrompido, protegido, etc.).'''


# Formas comuns de escrever a quantidade numa linha de pedido: "3 un", "qtd: 3", "3x", "x3"
PADROES_QTD = [
    r'(\d+)\s*(?:un|und|unid|unidades?|pcs|p[cç]s?)\b',
    r'(?:qtd|qtde|quant\w*|qt)\.?\s*[:=]?\s*(\d+)',
    r'\b(\d+)\s*x\b',
    r'\bx\s*(\d+)\b',
]


def extrair_texto(conteudo_pdf):
    '''Recebe os bytes de um PDF e devolve o texto de todas as páginas.'''
    try:
        leitor = PdfReader(BytesIO(conteudo_pdf))
        return "\n".join((pagina.extract_text() or "") for pagina in leitor.pages)
    except Exception as erro:
        raise PedidoInvalido("Não consegui ler esse arquivo como PDF.") from erro


def _achar_quantidade(texto):
    '''Procura a quantidade numa linha (já sem o SKU). Retorna int ou None.'''
    texto = re.sub(r'R\$\s*[\d.,]+', ' ', texto)  # tira preços para não confundir com quantidade
    for padrao in PADROES_QTD:
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            return int(m.group(1))
    # Sem pista nenhuma: usa o primeiro número inteiro "solto" (sem casas decimais)
    m = re.search(r'(?<![\d.,])(\d+)(?![\d.,]\d)', texto)
    return int(m.group(1)) if m else None


def interpretar_pedido(texto, produtos):
    '''
    Procura, linha por linha, os SKUs cadastrados e a quantidade pedida de cada um.

    :param produtos: dicionário {SKU_MAIÚSCULO: produto} (veja database.get_mapa_de_skus).
    :return: (itens, ignoradas) - itens com a situação de cada um e as linhas sem SKU reconhecido.
    '''
    skus = sorted(produtos, key=len, reverse=True)  # SKUs maiores primeiro
    acumulado = {}   # sku -> quantidade somada (o mesmo SKU pode aparecer em várias linhas)
    ignoradas = []

    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue

        achou = None
        for sku in skus:
            padrao = rf'(?<![A-Za-z0-9_-]){re.escape(sku)}(?![A-Za-z0-9_-])'
            m = re.search(padrao, linha, re.IGNORECASE)
            if m:
                achou = sku
                resto = linha[:m.start()] + ' ' + linha[m.end():]  # linha sem o SKU
                break

        if not achou:
            ignoradas.append(linha)
            continue

        qtd = _achar_quantidade(resto)
        item = acumulado.setdefault(achou, {'qtd': None, 'linhas': []})
        item['linhas'].append(linha)
        if qtd and qtd > 0:
            item['qtd'] = (item['qtd'] or 0) + qtd

    itens = []
    for sku, dados in acumulado.items():
        produto = produtos[sku]
        qtd = dados['qtd']
        if qtd is None:
            situacao = 'sem_qtd'
        elif qtd > produto['quantidade']:
            situacao = 'sem_estoque'
        else:
            situacao = 'ok'
        itens.append({
            'sku': produto['sku'], 'nome': produto['nome'], 'qtd': qtd,
            'estoque': produto['quantidade'], 'situacao': situacao,
            'linhas': dados['linhas'],
        })
    return itens, ignoradas
