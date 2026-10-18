// Configuração lida exclusivamente de variáveis de ambiente — nenhum segredo literal no código.
const config = Object.freeze({
    env: process.env.NODE_ENV || 'development',
    port: Number(process.env.PORT) || 3000,
    databaseFile: process.env.DATABASE_FILE || ':memory:',
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || null,
    adminToken: process.env.ADMIN_TOKEN || null,
    seedUserPassword: process.env.SEED_USER_PASSWORD || null,
});

module.exports = config;
