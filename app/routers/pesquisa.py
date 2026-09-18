"""Rotas da Fase 1: pesquisa juridica."""
from datetime import date
from typing import Optional

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Item, Pesquisa
from app.schemas import ItemStatusUpdate, PesquisaRequest, PesquisaResponse, PesquisaResumo
from app.services.pesquisa_service import executar_pesquisa

router = APIRouter(prefix="/api", tags=["pesquisa"])


def _pesquisa_para_resposta(pesquisa: Pesquisa, ordenar: str = "data") -> dict:
    itens = list(pesquisa.itens)
    if ordenar == "relevancia":
        itens.sort(key=lambda i: i.relevancia_score, reverse=True)
    else:
        itens.sort(key=lambda i: i.data_publicacao or "", reverse=True)

    return {
        "id": pesquisa.id,
        "tema": pesquisa.tema,
        "data_inicio": pesquisa.data_inicio,
        "data_fim": pesquisa.data_fim,
        "tipo": pesquisa.tipo,
        "tribunal": pesquisa.tribunal,
        "custo_tokens_estimado": pesquisa.custo_tokens_estimado,
        "criado_em": pesquisa.criado_em.isoformat(),
        "itens": itens,
    }


@router.post("/pesquisas", response_model=PesquisaResponse)
def criar_pesquisa(request: PesquisaRequest, db: Session = Depends(get_db)):
    if request.data_inicio > request.data_fim:
        raise HTTPException(status_code=400, detail="A data inicial nao pode ser posterior a data final.")

    try:
        pesquisa = executar_pesquisa(
            db=db,
            tema=request.tema,
            data_inicio=request.data_inicio,
            data_fim=request.data_fim,
            tipo=request.tipo,
            tribunal=request.tribunal,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except anthropic.AuthenticationError as exc:
        raise HTTPException(status_code=401, detail="Chave da API da Anthropic invalida.") from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=429, detail="Limite de uso da API da Anthropic atingido. Tente novamente em instantes."
        ) from exc
    except anthropic.APIConnectionError as exc:
        raise HTTPException(status_code=502, detail="Falha de conexao com a API da Anthropic.") from exc
    except anthropic.APIStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Erro na API da Anthropic: {exc.message}") from exc

    return _pesquisa_para_resposta(pesquisa)


@router.get("/pesquisas", response_model=list[PesquisaResumo])
def listar_pesquisas(
    tema: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Pesquisa)
    if tema:
        query = query.filter(Pesquisa.tema.ilike(f"%{tema}%"))
    if data_inicio:
        query = query.filter(Pesquisa.data_inicio >= data_inicio.isoformat())
    if data_fim:
        query = query.filter(Pesquisa.data_fim <= data_fim.isoformat())

    pesquisas = query.order_by(Pesquisa.criado_em.desc()).all()

    return [
        {
            "id": p.id,
            "tema": p.tema,
            "data_inicio": p.data_inicio,
            "data_fim": p.data_fim,
            "tipo": p.tipo,
            "tribunal": p.tribunal,
            "custo_tokens_estimado": p.custo_tokens_estimado,
            "criado_em": p.criado_em.isoformat(),
            "total_itens": len(p.itens),
        }
        for p in pesquisas
    ]


@router.get("/pesquisas/{pesquisa_id}", response_model=PesquisaResponse)
def obter_pesquisa(pesquisa_id: int, ordenar: str = Query(default="data", pattern="^(data|relevancia)$"), db: Session = Depends(get_db)):
    pesquisa = db.get(Pesquisa, pesquisa_id)
    if not pesquisa:
        raise HTTPException(status_code=404, detail="Pesquisa nao encontrada.")
    return _pesquisa_para_resposta(pesquisa, ordenar)


@router.post("/itens/{item_id}/status")
def atualizar_status_item(item_id: int, atualizacao: ItemStatusUpdate, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item nao encontrado.")

    if atualizacao.status == "erro" and not atualizacao.observacao_erro.strip():
        raise HTTPException(status_code=400, detail="Informe a observacao do erro encontrado.")

    item.status = atualizacao.status
    item.observacao_erro = atualizacao.observacao_erro if atualizacao.status == "erro" else ""
    db.commit()
    return {"ok": True}
