# task-manager-api

API de Task Manager em Python/Flask — refatorada para MVC pela skill `refactor-arch` (ver `reports/audit-project-3.md` na raiz).

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env   # opcional: SECRET_KEY, SEED_USER_PASSWORD, SMTP_*
python seed.py
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` (configurável por `HOST`/`PORT`). O `seed.py` popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**. A senha dos usuários seed é `SEED_USER_PASSWORD`.

## Estrutura

```
app.py              # create_app() — composition root + entry point
config/             # settings via variáveis de ambiente
models/             # entidades, regras de entidade e consultas (SQLAlchemy)
controllers/        # fluxo e regras de negócio por domínio
routes/             # Blueprints finos (camada View)
middlewares/        # tratamento de erros centralizado
services/           # notificações por e-mail (injetado)
utils/              # exceções, validadores, utcnow
```
