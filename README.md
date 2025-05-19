# µShort (Micro URL Shortener)

Este é um serviço de encurtamento de URL simples, baseado em microsserviços,
construído com FastAPI, SQLAlchemy (AsyncPG) e Docker Compose para desenvolvimento local.

## Arquitetura

O sistema é composto por três microsserviços principais:

1.  **API Gateway (`api_gateway`)**: Ponto de entrada único para os clientes. Expõe os endpoints `/api/shorten` (POST) e `/{short_code}` (GET) e encaminha as requisições para os serviços apropriados.
2.  **Shortening Service (`shortening_service`)**: Responsável por gerar códigos curtos únicos, validar a URL longa e salvar o mapeamento no banco de dados. Expõe um endpoint interno `/shorten` (POST).
3.  **Redirection Service (`redirection_service`)**: Responsável por buscar a URL longa original com base no código curto fornecido. Expõe um endpoint interno `/lookup/{short_code}` (GET).
4.  **Database (`postgres`)**: Um container PostgreSQL para persistir os mapeamentos de URL.

## Como Executar Localmente

1.  **Pré-requisitos**:
    *   Docker: [https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/)
    *   Docker Compose: (geralmente incluído com o Docker Desktop)

2.  **Configuração**:
    *   Clone este repositório.
    *   Crie um arquivo chamado `.env` na raiz do projeto (`ushort/`).
    *   Copie o conteúdo de um `.env.example` (se existir) ou use o seguinte template, **substituindo `SUA_SENHA_SECRETA_AQUI` por uma senha forte**:

      ```dotenv
      # Configuração do Banco de Dados PostgreSQL
      POSTGRES_USER=ushort_user
      POSTGRES_PASSWORD=SUA_SENHA_SECRETA_AQUI
      POSTGRES_DB=ushort_db
      DATABASE_HOSTNAME=postgres
      DATABASE_PORT=5432
      DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DATABASE_HOSTNAME}:${DATABASE_PORT}/${POSTGRES_DB}

      # URLs dos Serviços (usadas pelo API Gateway)
      SHORTENING_SERVICE_URL=http://shortening_service:8000
      REDIRECTION_SERVICE_URL=http://redirection_service:8000

      # URL Base pública (como o usuário acessará)
      BASE_URL=http://localhost:8000
      ```

3.  **Iniciando os Serviços**:
    *   Abra um terminal na raiz do projeto (`ushort/`).
    *   Execute o comando:
        ```bash
        docker-compose up --build
        ```
    *   Este comando construirá as imagens Docker (se ainda não existirem) e iniciará todos os contêineres (API Gateway, Shortening Service, Redirection Service, PostgreSQL).
    *   Aguarde até que todos os serviços indiquem que estão prontos (você verá logs dos diferentes serviços no terminal).

4.  **Testando**:

    *   **Encurtar uma URL:**
        Use `curl` ou uma ferramenta como Postman/Insomnia:
        ```bash
        curl -X POST "http://localhost:8000/api/shorten" \
             -H "Content-Type: application/json" \
             -d '{"long_url": "https://www.google.com/search?q=sistemas+distribuidos"}'
        ```
        A resposta deve ser algo como:
        ```json
        {"short_url":"http://localhost:8000/abcdef"}
        ```
        (Onde `abcdef` é o código curto gerado).

    *   **Acessar a URL Curta:**
        Abra o `short_url` retornado (ex: `http://localhost:8000/abcdef`) no seu navegador. Você deve ser redirecionado para a URL longa original (`https://www.google.com/...`).
        Ou use `curl` para ver o redirecionamento:
        ```bash
        curl -i http://localhost:8000/abcdef
        ```
        Você verá uma resposta HTTP 307 com o cabeçalho `Location:` apontando para a URL original.

    *   **Documentação da API (Swagger UI):**
        Acesse `http://localhost:8000/docs` no seu navegador para ver a documentação interativa gerada pelo FastAPI para o API Gateway.

5.  **Parando os Serviços**:
    *   Pressione `Ctrl + C` no terminal onde o `docker-compose up` está rodando.
    *   Para remover os contêineres e a rede (mas manter o volume do banco de dados), execute:
        ```bash
        docker-compose down
        ```
    *   Para remover também o volume do banco de dados (CUIDADO: apaga todos os dados):
        ```bash
        docker-compose down -v
        ```

## Próximos Passos (Nuvem)

*   Escolher um provedor de nuvem (GCP, AWS, Azure).
*   Configurar um serviço de banco de dados PostgreSQL gerenciado (Cloud SQL, RDS, Azure DB for PostgreSQL).
*   Configurar um registro de contêiner (Artifact Registry, ECR, ACR).
*   Adaptar os `Dockerfile`s se necessário (remover `--reload` do `CMD`).
*   Criar scripts ou usar ferramentas de CI/CD para buildar as imagens, enviá-las para o registro e implantar os serviços em plataformas como Cloud Run, Fargate ou Azure Container Apps.
*   Configurar variáveis de ambiente na nuvem (URLs dos serviços, conexão com DB).
*   Configurar um balanceador de carga ou serviço de API Gateway na nuvem para expor o `api_gateway` publicamente com um DNS.