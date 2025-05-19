import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import asyncio
import random
import sys

# Importa módulos locais do serviço
from . import crud, models, utils, database

# Carrega variáveis de ambiente do .env
from dotenv import load_dotenv

load_dotenv()

# --- Leitura e Verificação do BASE_URL ---
BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    print("ERRO CRÍTICO: Variável de ambiente BASE_URL não definida!", file=sys.stderr)
    # Em um cenário real, seria melhor lançar um erro aqui:
    # raise ValueError("BASE_URL environment variable not set")
    # Para este exemplo, usamos um fallback com aviso:
    BASE_URL = "http://localhost:8000"
    print(f"AVISO: BASE_URL não definida, usando fallback: {BASE_URL}", file=sys.stderr)
else:
    print(f"INFO: BASE_URL definida como: {BASE_URL}", file=sys.stderr)


# --- Fim da Leitura do BASE_URL ---


# --- Definição do Context Manager lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager para ações de inicialização e finalização da aplicação.
    Inclui um delay aleatório para mitigar race conditions na criação do DB.
    """
    # Obter o título da aplicação para logs mais claros
    app_title = app.title if hasattr(app, 'title') else "FastAPI App"

    # --- ADICIONAR SLEEP ALEATÓRIO ---
    startup_delay = random.uniform(0.1, 1.5)  # Espera entre 0.1 e 1.5 segundos
    print(f"{app_title}: Waiting {startup_delay:.2f}s before DB init...", file=sys.stderr)
    await asyncio.sleep(startup_delay)
    # --- FIM DO SLEEP ---

    print(f"{app_title}: Initializing database...", file=sys.stderr)
    try:
        await database.init_db()
        print(f"{app_title}: Database initialized.", file=sys.stderr)
    except Exception as e:
        print(f"ERROR during {app_title} DB initialization: {e}", file=sys.stderr)
        # Considerar relançar o erro em produção: raise e

    yield  # Aplicação roda aqui

    # Código a ser executado APÓS a aplicação finalizar (shutdown)
    print(f"{app_title}: Closing down...", file=sys.stderr)
    # Código de limpeza (ex: fechar pool de conexão) iria aqui se necessário


# --- Fim da Definição do lifespan ---


# --- Criação da Instância do FastAPI ---
# Agora 'lifespan' já está definido e pode ser passado
app = FastAPI(
    title="µShort - Shortening Service",
    description="Serviço responsável por gerar e salvar URLs curtas.",
    version="0.1.0",
    lifespan=lifespan  # Passa a função lifespan definida acima
)


# --- Fim da Criação do FastAPI ---


# --- Definição das Rotas da API ---
@app.post("/shorten", response_model=models.URLShortResponse, status_code=201)
async def create_short_url(
        url_item: models.URLBase,
        db: AsyncSession = Depends(database.get_db)
):
    """
    Recebe uma URL longa e retorna a URL curta correspondente.
    Gera um código único, salva no banco e retorna a URL completa.
    """
    # 1. Gerar código único
    try:
        short_code = await utils.generate_unique_short_code(db)
    except Exception as e:
        # Captura a exceção de generate_unique_short_code
        print(f"ERROR generating unique code: {e}", file=sys.stderr)  # Adiciona log
        raise HTTPException(status_code=500, detail=f"Failed to generate unique code: {e}")

    # 2. Preparar dados para criação no DB
    url_create_data = models.URLCreate(
        long_url=url_item.long_url,
        short_code=short_code
    )

    # 3. Tentar criar o mapeamento no DB
    try:
        db_url_map = await crud.create_url_mapping(db, url_create_data)
    except HTTPException as http_exc:
        # Repassa exceções HTTP conhecidas do CRUD (ex: 409, 500)
        raise http_exc
    except Exception as e:
        # Captura outras exceções inesperadas do CRUD
        print(f"ERROR creating URL mapping: {e}", file=sys.stderr)  # Adiciona log
        raise HTTPException(status_code=500, detail=f"Failed to save URL mapping: {e}")

    # 4. Construir a URL curta completa (BASE_URL é definida no nível do módulo)
    full_short_url = f"{BASE_URL}/{db_url_map.short_code}"
    print(f"INFO: Created short URL: {full_short_url} for {url_item.long_url}", file=sys.stderr)  # Adiciona log

    # 5. Retornar a resposta
    return models.URLShortResponse(short_url=full_short_url)


# Endpoint de health check (opcional, mas útil)
@app.get("/health", status_code=200)
async def health_check():
    """Verifica a saúde básica do serviço."""
    return {"status": "ok"}
# --- Fim da Definição das Rotas ---

# ... (final do arquivo, depois de todas as definições) ...
print("INFO: main.py module loaded successfully.", file=sys.stderr)