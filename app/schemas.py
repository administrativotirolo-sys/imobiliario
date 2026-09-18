"""Schemas Pydantic usados nas rotas da API (Fase 1)."""
from datetime import date

from pydantic import BaseModel, Field


class PesquisaRequest(BaseModel):
    tema: str = Field(..., min_length=2, max_length=255)
    data_inicio: date
    data_fim: date
    tipo: str = Field(default="ambos", pattern="^(noticia|julgado|ambos)$")
    tribunal: str = Field(default="todos")


class FonteResponse(BaseModel):
    id: int
    nome_fonte: str
    url: str
    oficial: bool

    class Config:
        from_attributes = True


class ItemResponse(BaseModel):
    id: int
    titulo: str
    tipo: str
    data_publicacao: str
    tribunal: str
    numero_processo: str
    tese_resumo: str
    palavras_chave: str
    relevancia_pratica: str
    relevancia_score: int
    status: str
    nao_verificado: bool
    observacao_erro: str
    fontes: list[FonteResponse]

    class Config:
        from_attributes = True


class PesquisaResponse(BaseModel):
    id: int
    tema: str
    data_inicio: str
    data_fim: str
    tipo: str
    tribunal: str
    custo_tokens_estimado: float
    criado_em: str
    itens: list[ItemResponse]

    class Config:
        from_attributes = True


class PesquisaResumo(BaseModel):
    """Versao sem os itens, usada na listagem do historico."""

    id: int
    tema: str
    data_inicio: str
    data_fim: str
    tipo: str
    tribunal: str
    custo_tokens_estimado: float
    criado_em: str
    total_itens: int

    class Config:
        from_attributes = True


class ItemStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(salvo|descartado|erro)$")
    observacao_erro: str = Field(default="")
