import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Carrega .env para desenvolvimento local (ignorado no Cloud Run se não presente)
load_dotenv()

# --- Construção Dinâmica da DATABASE_URL ---

# Lê as variáveis de ambiente individuais
DB_USER = os.getenv("POSTGRES_USER", "ushort_user")  # Default para dev local
DB_PASSWORD = os.getenv("DB_PASSWORD")  # Essencial: Virá do Secret Manager no Cloud Run
DB_HOST_LOCAL = os.getenv("DATABASE_HOSTNAME", "postgres")  # Para dev local (Docker)
DB_PORT_LOCAL = os.getenv("DATABASE_PORT", "5432")  # Para dev local (Docker)
DB_NAME = os.getenv("POSTGRES_DB", "ushort_db")  # Default para dev local
INSTANCE_CONNECTION_NAME = os.getenv("CLOUD_SQL_CONNECTION_NAME")  # Virá do Cloud Run

DATABASE_URL = None

# Verifica se está rodando no Cloud Run e se o nome da conexão SQL foi fornecido
if os.getenv('K_SERVICE') and INSTANCE_CONNECTION_NAME:
    # Formato para Socket Unix no Cloud Run
    socket_dir = "/cloudsql"
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_NAME}?host={socket_dir}/{INSTANCE_CONNECTION_NAME}"
    print(f"INFO: Configurando conexão via Cloud Run Socket Unix.", file=sys.stderr)

else:
    # Formato padrão para desenvolvimento local (Docker Compose) ou outra conexão TCP
    if not DB_PASSWORD:
        print("AVISO: Senha do DB (DB_PASSWORD) não encontrada no ambiente local!", file=sys.stderr)
        # A conexão provavelmente falhará sem senha localmente
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST_LOCAL}:{DB_PORT_LOCAL}/{DB_NAME}"
    print(f"INFO: Configurando conexão padrão (local/TCP).", file=sys.stderr)

# Validação final
if not DATABASE_URL:
    print("ERRO CRÍTICO: Não foi possível determinar a DATABASE_URL!", file=sys.stderr)
    raise ValueError("DATABASE_URL não pôde ser construída.")

if not DB_PASSWORD and not os.getenv('K_SERVICE'):  # Checa senha faltando localmente
    print("AVISO SEVERO: DB_PASSWORD não definida no ambiente local. A conexão falhará.", file=sys.stderr)

# --- Configuração SQLAlchemy ---

Base = declarative_base()

# Cria a engine com a URL construída
try:
    # echo=True pode ser útil para debug, mas removido para prod
    engine = create_async_engine(DATABASE_URL, echo=False, pool_recycle=1800)  # pool_recycle é bom para conexões longas
except Exception as e:
    print(f"ERRO CRÍTICO: Falha ao criar SQLAlchemy engine com URL calculada: {e}", file=sys.stderr)
    # Imprime a URL (sem senha) para debug SE falhar
    safe_url = DATABASE_URL.replace(f":{DB_PASSWORD}@", ":***@") if DB_PASSWORD else DATABASE_URL
    print(f"URL utilizada (senha omitida): {safe_url}", file=sys.stderr)
    raise e

# Fábrica de Sessões Assíncronas
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# --- Funções de Sessão ---

# Dependency para injeção de sessão nas rotas FastAPI
async def get_db() -> AsyncSession:
    """Fornece uma sessão de banco de dados assíncrona para uma rota FastAPI."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()  # Commit automático se a rota for bem-sucedida
        except Exception:
            await session.rollback()  # Rollback em caso de erro na rota
            raise
        finally:
            await session.close()


# Context Manager para uso fora das rotas (ex: scripts, testes iniciais)
@asynccontextmanager
async def get_session() -> AsyncSession:
    """Fornece uma sessão de banco de dados assíncrona como context manager."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# --- Adicionar a função init_db de volta ---
async def init_db():
    """Cria as tabelas no banco de dados se não existirem."""
    print("INFO: Running init_db() - attempting to create tables...", file=sys.stderr)
    async with engine.begin() as conn:
        try:
            # run_sync executa Base.metadata.create_all de forma síncrona
            # dentro do contexto assíncrono da conexão.
            # checkfirst=True (padrão) evita erro se tabela já existir.
            await conn.run_sync(Base.metadata.create_all)
            print("INFO: Base.metadata.create_all executed.", file=sys.stderr)
        except Exception as e:
            print(f"ERROR during metadata.create_all: {e}", file=sys.stderr)
            # Decide se quer relançar o erro ou apenas logar
            # raise e
# --- Fim da adição ---
