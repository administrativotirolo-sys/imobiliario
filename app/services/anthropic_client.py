"""Cliente da API da Anthropic para a pesquisa juridica (Fase 1).

Usa a ferramenta de web search nativa do Claude para buscar noticias e
julgados recentes de direito imobiliario, e pede ao modelo que devolva
os resultados em JSON estruturado, seguindo regras estritas de fidelidade
as fontes (nunca inventar dado que a fonte nao trouxer).
"""
import json
import re

import anthropic

from app.config import settings

# Precos aproximados por milhao de tokens (USD) do modelo usado.
# Cobre apenas tokens de entrada/saida; nao inclui eventual taxa por busca.
PRECOS_POR_MILHAO = {
    "claude-sonnet-5": {"entrada": 2.00, "saida": 10.00},
}

SYSTEM_PROMPT = """Voce e um assistente de pesquisa juridica especializado em direito \
imobiliario brasileiro, trabalhando para um advogado (OAB/SP) que produz conteudo \
educativo para redes sociais.

Sua tarefa e usar a ferramenta de busca na web para encontrar noticias e julgados \
RECENTES e REAIS sobre o tema pedido, e devolver os resultados em JSON.

Fontes prioritarias, nesta ordem: portais oficiais do STJ, STF e TJSP; depois \
Conjur, Migalhas e JOTA; e Diario Oficial ou sites do Congresso para mudancas \
legislativas. Outras fontes podem ser usadas, mas com menor prioridade.

REGRAS DE FIDELIDADE, OBRIGATORIAS:
1. Nunca invente numero de processo, relator, data ou ementa. Se a fonte nao trouxer \
o dado, deixe o campo como string vazia "".
2. Todo item precisa ter pelo menos uma URL real de origem, clicavel, que voce \
efetivamente encontrou na busca. Nunca invente URL.
3. A data de publicacao exibida deve ser a data em que a fonte publicou a noticia ou \
o julgado foi divulgado, nunca a data de hoje.
4. Descarte qualquer resultado publicado fora do periodo pedido.
5. O campo "oficial" de cada fonte so pode ser true se for um portal OFICIAL de \
tribunal, orgao publico, Diario Oficial ou site do Congresso (exemplos: stj.jus.br, \
stf.jus.br, tjsp.jus.br, in.gov.br, planalto.gov.br, camara.leg.br, senado.leg.br). \
Veiculos jornalisticos, mesmo prioritarios (Conjur, Migalhas, JOTA e similares), \
devem sempre ter "oficial": false.
6. Se o mesmo julgado ou noticia aparecer em mais de uma fonte, gere um UNICO item \
e liste todas as fontes encontradas no campo "fontes".
7. Nunca use travessao (em dash, o caractere "-" longo) em nenhum texto gerado.
8. Escreva em portugues do Brasil.

Responda APENAS com um JSON valido no seguinte formato, sem nenhum texto antes ou \
depois:

{
  "itens": [
    {
      "titulo": "string",
      "tipo": "noticia" ou "julgado",
      "data_publicacao": "AAAA-MM-DD ou vazio se nao encontrado",
      "tribunal": "STJ, STF, TJSP, outro ou vazio",
      "numero_processo": "string ou vazio",
      "tese_resumo": "resumo da tese em ate 5 linhas",
      "palavras_chave": ["palavra1", "palavra2"],
      "relevancia_pratica": "explicacao curta do impacto pratico para um cliente leigo",
      "relevancia_score": numero de 1 a 5,
      "oficial": true ou false,
      "fontes": [
        {"nome_fonte": "string", "url": "string", "oficial": true ou false}
      ]
    }
  ]
}

Se nenhum resultado real for encontrado dentro do periodo, responda {"itens": []}.
"""


def _montar_prompt_usuario(tema: str, data_inicio: str, data_fim: str, tipo: str, tribunal: str) -> str:
    tipo_texto = {
        "noticia": "apenas noticias",
        "julgado": "apenas julgados/decisoes",
        "ambos": "noticias e julgados",
    }.get(tipo, "noticias e julgados")

    tribunal_texto = "qualquer tribunal ou orgao" if tribunal in ("", "todos") else tribunal

    return (
        f"Pesquise {tipo_texto} de direito imobiliario sobre o tema \"{tema}\", "
        f"publicados entre {data_inicio} e {data_fim} (inclusive), priorizando "
        f"decisoes/noticias de {tribunal_texto}. Use a busca na web quantas vezes "
        f"forem necessarias para confirmar datas e fontes reais antes de responder."
    )


def _extrair_json(texto: str) -> dict:
    """Extrai o primeiro objeto JSON valido de um texto."""
    texto = texto.strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError("Nao foi possivel extrair um JSON valido da resposta do modelo.")


def _calcular_custo(modelo: str, tokens_entrada: int, tokens_saida: int) -> float:
    precos = PRECOS_POR_MILHAO.get(modelo)
    if not precos:
        return 0.0
    return (tokens_entrada / 1_000_000 * precos["entrada"]) + (tokens_saida / 1_000_000 * precos["saida"])


def pesquisar_direito_imobiliario(tema: str, data_inicio: str, data_fim: str, tipo: str, tribunal: str) -> dict:
    """Executa a pesquisa via API da Anthropic com web search.

    Retorna um dicionario com "itens" (lista bruta do modelo), "tokens_entrada",
    "tokens_saida" e "custo_estimado_usd".
    """
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY nao configurada. Copie .env.example para .env e "
            "preencha sua chave da API da Anthropic."
        )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    user_prompt = _montar_prompt_usuario(tema, data_inicio, data_fim, tipo, tribunal)
    messages = [{"role": "user", "content": user_prompt}]

    tokens_entrada_total = 0
    tokens_saida_total = 0

    max_rodadas = 4
    response = None
    for _ in range(max_rodadas):
        response = client.messages.create(
            model=settings.modelo_claude,
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}],
            messages=messages,
        )

        tokens_entrada_total += response.usage.input_tokens
        tokens_saida_total += response.usage.output_tokens

        if response.stop_reason != "pause_turn":
            break

        messages = [
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": response.content},
        ]

    texto_final = "".join(block.text for block in response.content if block.type == "text")

    try:
        dados = _extrair_json(texto_final)
    except ValueError as exc:
        raise RuntimeError(
            f"O modelo nao devolveu um JSON valido. Resposta bruta: {texto_final[:500]}"
        ) from exc

    custo = _calcular_custo(settings.modelo_claude, tokens_entrada_total, tokens_saida_total)

    return {
        "itens": dados.get("itens", []),
        "tokens_entrada": tokens_entrada_total,
        "tokens_saida": tokens_saida_total,
        "custo_estimado_usd": custo,
    }
