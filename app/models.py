"""Modelos ORM do banco de dados.

O esquema ja contempla as 3 fases do projeto (pesquisa, roteiros e
teleprompter) para evitar migracoes estruturais mais adiante.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Pesquisa(Base):
    """Uma execucao de pesquisa (Fase 1), com os filtros usados."""

    __tablename__ = "pesquisas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tema: Mapped[str] = mapped_column(String(255))
    data_inicio: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    data_fim: Mapped[str] = mapped_column(String(10))
    tipo: Mapped[str] = mapped_column(String(20))  # noticia | julgado | ambos
    tribunal: Mapped[str] = mapped_column(String(50))  # STJ | STF | TJSP | outros | todos
    custo_tokens_estimado: Mapped[float] = mapped_column(Float, default=0.0)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    itens: Mapped[list["Item"]] = relationship(back_populates="pesquisa", cascade="all, delete-orphan")


class Item(Base):
    """Um resultado (noticia ou julgado) encontrado em uma pesquisa."""

    __tablename__ = "itens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pesquisa_id: Mapped[int] = mapped_column(ForeignKey("pesquisas.id"))

    titulo: Mapped[str] = mapped_column(String(500))
    tipo: Mapped[str] = mapped_column(String(20))  # noticia | julgado
    data_publicacao: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD, data da fonte
    tribunal: Mapped[str] = mapped_column(String(50), default="")
    numero_processo: Mapped[str] = mapped_column(String(100), default="")
    tese_resumo: Mapped[str] = mapped_column(Text, default="")
    palavras_chave: Mapped[str] = mapped_column(Text, default="")  # separadas por virgula
    relevancia_pratica: Mapped[str] = mapped_column(Text, default="")
    relevancia_score: Mapped[int] = mapped_column(Integer, default=3)  # 1 a 5, para ordenacao

    status: Mapped[str] = mapped_column(String(20), default="novo")  # novo|salvo|descartado|erro
    nao_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    observacao_erro: Mapped[str] = mapped_column(Text, default="")

    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pesquisa: Mapped["Pesquisa"] = relationship(back_populates="itens")
    fontes: Mapped[list["Fonte"]] = relationship(back_populates="item", cascade="all, delete-orphan")
    roteiro_itens: Mapped[list["RoteiroItem"]] = relationship(back_populates="item")


class Fonte(Base):
    """Uma fonte (URL) que noticiou um item. Um item pode ter varias (dedup)."""

    __tablename__ = "fontes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("itens.id"))
    nome_fonte: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(1000))
    oficial: Mapped[bool] = mapped_column(Boolean, default=False)

    item: Mapped["Item"] = relationship(back_populates="fontes")


class Roteiro(Base):
    """Um roteiro de video gerado a partir de itens salvos (Fase 2)."""

    __tablename__ = "roteiros"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(255), default="")
    formato: Mapped[str] = mapped_column(String(30), default="")  # reels60|reels90|youtube
    tom: Mapped[str] = mapped_column(String(30), default="")
    publico: Mapped[str] = mapped_column(String(30), default="")
    conteudo_json: Mapped[str] = mapped_column(Text, default="{}")
    duracao_estimada_seg: Mapped[int] = mapped_column(Integer, default=0)
    verificacao_etica_status: Mapped[str] = mapped_column(String(20), default="pendente")
    verificacao_etica_detalhes: Mapped[str] = mapped_column(Text, default="[]")
    versao: Mapped[int] = mapped_column(Integer, default=1)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    itens: Mapped[list["RoteiroItem"]] = relationship(back_populates="roteiro", cascade="all, delete-orphan")
    sessoes_teleprompter: Mapped[list["TeleprompterSessao"]] = relationship(back_populates="roteiro")


class RoteiroItem(Base):
    """Associacao N:N entre roteiros e os itens usados como base."""

    __tablename__ = "roteiro_itens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roteiro_id: Mapped[int] = mapped_column(ForeignKey("roteiros.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("itens.id"))

    roteiro: Mapped["Roteiro"] = relationship(back_populates="itens")
    item: Mapped["Item"] = relationship(back_populates="roteiro_itens")


class TeleprompterSessao(Base):
    """Estado de uma sessao de teleprompter (Fase 3)."""

    __tablename__ = "teleprompter_sessoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roteiro_id: Mapped[int | None] = mapped_column(ForeignKey("roteiros.id"), nullable=True)
    texto_limpo: Mapped[str] = mapped_column(Text, default="")
    estado_json: Mapped[str] = mapped_column(Text, default="{}")  # posicao, velocidade, tocando
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    roteiro: Mapped["Roteiro"] = relationship(back_populates="sessoes_teleprompter")


class UsoApi(Base):
    """Registro de uso da API da Anthropic, para relatorio de custos."""

    __tablename__ = "uso_api"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20))  # pesquisa | roteiro
    referencia_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_entrada: Mapped[int] = mapped_column(Integer, default=0)
    tokens_saida: Mapped[int] = mapped_column(Integer, default=0)
    custo_estimado_usd: Mapped[float] = mapped_column(Float, default=0.0)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
