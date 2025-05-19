import os
import httpx
import sys # Adicionado para sys.stderr
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

# Modelos Pydantic
class URLToShortenRequest(BaseModel):
    long_url: HttpUrl

class ShortenedURLResponse(BaseModel):
    short_url: HttpUrl

# Variáveis de ambiente
SHORTENING_SERVICE_URL = os.getenv("SHORTENING_SERVICE_URL")
REDIRECTION_SERVICE_URL = os.getenv("REDIRECTION_SERVICE_URL")
BASE_URL_GATEWAY = os.getenv("BASE_URL")

print(f"INFO [API Gateway Startup]: SHORTENING_SERVICE_URL = {SHORTENING_SERVICE_URL}", file=sys.stderr)
print(f"INFO [API Gateway Startup]: REDIRECTION_SERVICE_URL = {REDIRECTION_SERVICE_URL}", file=sys.stderr)
print(f"INFO [API Gateway Startup]: BASE_URL_GATEWAY = {BASE_URL_GATEWAY}", file=sys.stderr)

if not SHORTENING_SERVICE_URL or not REDIRECTION_SERVICE_URL or not BASE_URL_GATEWAY:
    print("ERRO CRÍTICO [API Gateway Startup]: URLs de serviço ou BASE_URL não configuradas!", file=sys.stderr)
    # Em produção, você pode querer lançar um erro para impedir a inicialização:
    # raise ValueError("Variáveis de ambiente essenciais não configuradas para API Gateway")

# Lifespan manager para o cliente HTTPX
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("INFO [API Gateway Lifespan]: Criando cliente HTTPX...", file=sys.stderr)
    app.state.http_client = httpx.AsyncClient()
    print("INFO [API Gateway Lifespan]: Cliente HTTPX criado.", file=sys.stderr)
    yield
    print("INFO [API Gateway Lifespan]: Fechando cliente HTTPX...", file=sys.stderr)
    await app.state.http_client.aclose()
    print("INFO [API Gateway Lifespan]: Cliente HTTPX fechado.", file=sys.stderr)

# Criação da Instância FastAPI
print("INFO [API Gateway Startup]: Criando instância FastAPI...", file=sys.stderr)
app = FastAPI(
    title="µShort - API Gateway",
    description="Ponto de entrada único para o serviço µShort.",
    version="0.1.0",
    lifespan=lifespan
)
print("INFO [API Gateway Startup]: Instância FastAPI criada.", file=sys.stderr)

# Configuração CORS
print("INFO [API Gateway Startup]: Configurando CORSMiddleware...", file=sys.stderr)
origins = [
    "https://storage.googleapis.com",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:63342",
    "http://127.0.0.1:63342",
]
print(f"INFO [API Gateway Startup]: Origens CORS permitidas: {origins}", file=sys.stderr)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("INFO [API Gateway Startup]: CORSMiddleware adicionado.", file=sys.stderr)


# Rotas da API
@app.post(
    "/api/shorten",
    response_model=ShortenedURLResponse,
    status_code=status.HTTP_201_CREATED
)
async def shorten_url_endpoint(
    request: Request,
    url_item: URLToShortenRequest
):
    client: httpx.AsyncClient = request.app.state.http_client
    target_url = f"{SHORTENING_SERVICE_URL}/shorten"
    print(f"INFO [API Gateway /api/shorten]: Encaminhando POST para: {target_url}", file=sys.stderr)

    try:
        response = await client.post(
            target_url,
            json={"long_url": str(url_item.long_url)}
        )
        print(f"INFO [API Gateway /api/shorten]: Resposta do Shortening Service status: {response.status_code}", file=sys.stderr)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as exc:
        print(f"ERRO [API Gateway /api/shorten]: Falha na requisição para Shortening Service: {exc}", file=sys.stderr)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Shortening service is unavailable: {exc}"
        )
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        detail = f"Error from shortening service (status {status_code})"
        try:
             service_detail = exc.response.json().get("detail")
             if service_detail:
                 detail = f"Shortening Service Error: {service_detail}"
        except Exception:
             pass
        print(f"ERRO [API Gateway /api/shorten]: Shortening Service retornou status {status_code}: {detail}", file=sys.stderr)
        raise HTTPException(status_code=status_code, detail=detail)


@app.get("/{short_code}")
async def redirect_endpoint(
    request: Request,
    short_code: str
):
    client: httpx.AsyncClient = request.app.state.http_client
    target_url = f"{REDIRECTION_SERVICE_URL}/lookup/{short_code}"
    print(f"INFO [API Gateway /{short_code}]: Encaminhando GET para: {target_url}", file=sys.stderr)

    try:
        response_lookup = await client.get(target_url)
        print(f"INFO [API Gateway /{short_code}]: Resposta do Redirection Service status: {response_lookup.status_code}", file=sys.stderr)
        response_lookup.raise_for_status()
        data = response_lookup.json()
        long_url = data.get("long_url")

        if not long_url:
             print(f"ERRO [API Gateway /{short_code}]: Redirection Service não retornou URL longa válida.", file=sys.stderr)
             raise HTTPException(status_code=500, detail="Redirection service did not return a valid URL")

        print(f"INFO [API Gateway /{short_code}]: Redirecionando para {long_url}", file=sys.stderr)
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=long_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    except httpx.RequestError as exc:
        print(f"ERRO [API Gateway /{short_code}]: Falha na requisição para Redirection Service: {exc}", file=sys.stderr)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redirection service is unavailable: {exc}"
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            print(f"INFO [API Gateway /{short_code}]: Código não encontrado pelo Redirection Service.", file=sys.stderr)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
        else:
            status_code = exc.response.status_code
            detail = f"Error from redirection service (status {status_code})"
            try:
                service_detail = exc.response.json().get("detail")
                if service_detail:
                    detail = f"Redirection Service Error: {service_detail}"
            except Exception:
                pass
            print(f"ERRO [API Gateway /{short_code}]: Redirection Service retornou status {status_code}: {detail}", file=sys.stderr)
            raise HTTPException(status_code=status_code, detail=detail)

@app.get("/")
async def root():
    print("INFO [API Gateway /]: Rota raiz acessada.", file=sys.stderr)
    return {"message": "Welcome to µShort API Gateway!"}

print("INFO [API Gateway Startup]: Módulo main.py carregado e rotas definidas.", file=sys.stderr)