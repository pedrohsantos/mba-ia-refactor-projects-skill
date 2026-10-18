# code-smells-project

API de E-commerce em Python/Flask — refatorada para MVC pela skill `refactor-arch` (ver `reports/audit-project-1.md` na raiz).

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env   # opcional: defina ADMIN_TOKEN, SECRET_KEY, SEED_USER_PASSWORD
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` (configurável por `HOST`/`PORT`). O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (senha dos usuários seed = `SEED_USER_PASSWORD`).

## Estrutura

```
app.py                 # entry point
src/app.py             # create_app() — composition root
src/config/            # settings via variáveis de ambiente
src/models/            # persistência (SQL parametrizado)
src/controllers/       # regras de negócio e fluxo
src/views/             # Blueprints (rotas HTTP)
src/middlewares/       # erros centralizados + auth admin
src/services/          # notificações
src/utils/             # exceções e validadores
```

Rotas `/admin/*` exigem o header `X-Admin-Token` igual a `ADMIN_TOKEN`; sem a variável elas respondem 403.
