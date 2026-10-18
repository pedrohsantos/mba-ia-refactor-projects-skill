# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express — refatorada para MVC pela skill `refactor-arch` (ver `reports/audit-project-2.md` na raiz).

## Como rodar

```bash
npm install
ADMIN_TOKEN=dev-admin-token npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e carrega seeds no boot. Variáveis disponíveis em `.env.example`.
As rotas administrativas (`/api/admin/*` e `DELETE /api/users/:id`) exigem o header `X-Admin-Token`.

Exemplos de requisições estão em `api.http`.

## Estrutura

```
src/app.js           # composition root + servidor
src/config/          # env, conexão (promises + transações) e schema/seed
src/models/          # SQL por entidade
src/controllers/     # checkout, relatório financeiro, usuários
src/routes/          # Routers Express (camada View)
src/middlewares/     # erros centralizados + auth admin
src/services/        # gateway de pagamento
src/utils/           # erros, hash de senha, asyncHandler, logger
```
