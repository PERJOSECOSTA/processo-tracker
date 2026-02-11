from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class Processo(Base):
    __tablename__ = "processos"
    id = Column(Integer, primary_key=True)
    numero_cnj = Column(String(30), nullable=False, index=True)
    tribunal_alias = Column(String(80), nullable=False)
    email_destino = Column(String(255), nullable=False)
    ultimo_hash = Column(String(64), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    movimentacoes = relationship("Movimentacao", back_populates="processo", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("numero_cnj", "tribunal_alias", name="uq_processo"),)

class Movimentacao(Base):
    __tablename__ = "movimentacoes"
    id = Column(Integer, primary_key=True)
    processo_id = Column(Integer, ForeignKey("processos.id"), nullable=False, index=True)
    data = Column(DateTime, nullable=True)
    titulo = Column(String(500), nullable=True)
    descricao = Column(Text, nullable=True)
    origem_hash = Column(String(64), nullable=False)

    processo = relationship("Processo", back_populates="movimentacoes")
