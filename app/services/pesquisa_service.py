"""Regras de negocio da Fase 1: filtragem, deduplicacao e persistencia."""
from datetime import date

from sqlalchemy.orm import Session

from app.models import Fonte, Item, Pesquisa, UsoApi
from app.services.anthropic_client import pesquisar_direito_imobiliario


def _normalizar_titulo(titulo: str) -> str:
    return " ".join(titulo.lower().split())


def _data_dentro_do_periodo(data_publicacao: str, data_inicio: date, data_fim: date) -> bool:
    """Retorna True se a data estiver dentro do periodo ou nao puder ser avaliada."""
    if not data_publicacao:
        return True  # sem data informada: mantido, mas sera marcado como nao verificado
    try:
        data_item = date.fromisoformat(data_publicacao)
    except ValueError:
        return True  # data em formato invalido: mantido e marcado como nao verificado
    return data_inicio <= data_item <= data_fim


def executar_pesquisa(
    db: Session,
    tema: str,
    data_inicio: date,
    data_fim: date,
    tipo: str,
    tribunal: str,
) -> Pesquisa:
    resultado = pesquisar_direito_imobiliario(
        tema=tema,
        data_inicio=data_inicio.isoformat(),
        data_fim=data_fim.isoformat(),
        tipo=tipo,
        tribunal=tribunal,
    )

    pesquisa = Pesquisa(
        tema=tema,
        data_inicio=data_inicio.isoformat(),
        data_fim=data_fim.isoformat(),
        tipo=tipo,
        tribunal=tribunal,
        custo_tokens_estimado=resultado["custo_estimado_usd"],
    )
    db.add(pesquisa)
    db.flush()  # garante pesquisa.id antes de criar os itens

    titulos_vistos: set[str] = set()

    for item_bruto in resultado["itens"]:
        titulo = (item_bruto.get("titulo") or "").strip()
        if not titulo:
            continue  # sem titulo, nao ha como exibir o item com confianca

        data_publicacao = (item_bruto.get("data_publicacao") or "").strip()

        # Descarta itens fora do periodo pedido (camada extra de seguranca).
        if not _data_dentro_do_periodo(data_publicacao, data_inicio, data_fim):
            continue

        # Deduplicacao por titulo normalizado dentro desta mesma pesquisa.
        chave = _normalizar_titulo(titulo)
        if chave in titulos_vistos:
            continue
        titulos_vistos.add(chave)

        fontes_brutas = item_bruto.get("fontes") or []
        fontes_validas = [f for f in fontes_brutas if (f.get("url") or "").strip()]
        if not fontes_validas:
            continue  # regra: todo item precisa ter URL de origem

        tem_fonte_oficial = any(f.get("oficial") for f in fontes_validas)
        data_confiavel = _data_valida(data_publicacao)

        item = Item(
            pesquisa_id=pesquisa.id,
            titulo=titulo,
            tipo=item_bruto.get("tipo") or "noticia",
            data_publicacao=data_publicacao,
            tribunal=(item_bruto.get("tribunal") or "").strip(),
            numero_processo=(item_bruto.get("numero_processo") or "").strip(),
            tese_resumo=(item_bruto.get("tese_resumo") or "").strip(),
            palavras_chave=", ".join(item_bruto.get("palavras_chave") or []),
            relevancia_pratica=(item_bruto.get("relevancia_pratica") or "").strip(),
            relevancia_score=_relevancia_valida(item_bruto.get("relevancia_score")),
            status="novo",
            nao_verificado=not (tem_fonte_oficial and data_confiavel),
        )
        db.add(item)
        db.flush()

        for fonte_bruta in fontes_validas:
            db.add(
                Fonte(
                    item_id=item.id,
                    nome_fonte=(fonte_bruta.get("nome_fonte") or "").strip(),
                    url=(fonte_bruta.get("url") or "").strip(),
                    oficial=bool(fonte_bruta.get("oficial")),
                )
            )

    db.add(
        UsoApi(
            tipo="pesquisa",
            referencia_id=pesquisa.id,
            tokens_entrada=resultado["tokens_entrada"],
            tokens_saida=resultado["tokens_saida"],
            custo_estimado_usd=resultado["custo_estimado_usd"],
        )
    )

    db.commit()
    db.refresh(pesquisa)
    return pesquisa


def _data_valida(data_publicacao: str) -> bool:
    if not data_publicacao:
        return False
    try:
        date.fromisoformat(data_publicacao)
        return True
    except ValueError:
        return False


def _relevancia_valida(valor) -> int:
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return 3
    return min(5, max(1, numero))
