from sqlalchemy import Column, Integer, String, Index
from pydantic import BaseModel, HttpUrl
from .database import Base


# --- SQLAlchemy Model ---
# Exatamente o mesmo modelo do shortening_service, pois acessam a mesma tabela
class URLMap(Base):
    __tablename__ = 'url_mappings'
    # __table_args__ = {'schema': 'ushort'} # Se usando schema

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String, unique=True, index=True, nullable=False)
    long_url = Column(String, nullable=False)


# Index('ix_url_mappings_short_code', URLMap.short_code)

# --- Pydantic Models ---
# Modelo usado na resposta do endpoint /lookup/{short_code}
class OriginalURL(BaseModel):
    long_url: HttpUrl
