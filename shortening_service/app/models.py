from sqlalchemy import Column, Integer, String, Index
from pydantic import BaseModel, HttpUrl, Field
from .database import Base


# --- SQLAlchemy Model ---
class URLMap(Base):
    __tablename__ = 'url_mappings'
    # Se usando schema:
    # __table_args__ = {'schema': 'ushort'}

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String, unique=True, index=True, nullable=False)
    long_url = Column(String, nullable=False)  # String normal, validação Pydantic garante ser URL


# Adiciona um índice explícito no short_code, além do unique constraint
# Index('ix_url_mappings_short_code', URLMap.short_code)

# --- Pydantic Models ---
# Modelo para o corpo da requisição POST /shorten
class URLBase(BaseModel):
    long_url: HttpUrl  # Valida se é uma URL válida


# Modelo para a resposta da API (usado pelo Gateway)
class URLShortResponse(BaseModel):
    short_url: HttpUrl  # URL curta completa, ex: http://localhost:8000/abcdef


# Modelo interno usado pelo serviço de encurtamento ao criar
class URLCreate(URLBase):
    short_code: str
