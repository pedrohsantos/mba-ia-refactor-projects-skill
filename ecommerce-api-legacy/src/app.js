// Composition root: cria as dependências, monta o app Express e sobe o servidor.
const express = require('express');

const config = require('./config');
const { createDatabase } = require('./config/database');
const { initSchema } = require('./config/schema');
const logger = require('./utils/logger');

const { createUserModel } = require('./models/userModel');
const { createCourseModel } = require('./models/courseModel');
const { createEnrollmentModel } = require('./models/enrollmentModel');
const { createPaymentModel } = require('./models/paymentModel');
const { createAuditLogModel } = require('./models/auditLogModel');

const { createPaymentGateway } = require('./services/paymentGateway');

const { createCheckoutController } = require('./controllers/checkoutController');
const { createReportController } = require('./controllers/reportController');
const { createUserController } = require('./controllers/userController');

const { createCheckoutRoutes } = require('./routes/checkoutRoutes');
const { createAdminRoutes } = require('./routes/adminRoutes');
const { createUserRoutes } = require('./routes/userRoutes');

const { createAdminAuth } = require('./middlewares/adminAuth');
const { createErrorHandler } = require('./middlewares/errorHandler');

function buildApp({ db, settings = config, cache = new Map() }) {
    const userModel = createUserModel(db);
    const courseModel = createCourseModel(db);
    const enrollmentModel = createEnrollmentModel(db);
    const paymentModel = createPaymentModel(db);
    const auditLogModel = createAuditLogModel(db);
    const paymentGateway = createPaymentGateway({ apiKey: settings.paymentGatewayKey, logger });

    const checkoutController = createCheckoutController({
        db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentGateway, cache,
    });
    const reportController = createReportController({ courseModel });
    const userController = createUserController({ db, userModel });
    const requireAdmin = createAdminAuth({ adminToken: settings.adminToken });

    const app = express();
    app.use(express.json());
    app.use(createCheckoutRoutes({ checkoutController }));
    app.use(createAdminRoutes({ reportController, requireAdmin }));
    app.use(createUserRoutes({ userController, requireAdmin }));
    app.use(createErrorHandler({ logger }));
    return app;
}

async function start() {
    const db = createDatabase({ filename: config.databaseFile, verbose: config.env !== 'production' });
    await initSchema(db, { seedUserPassword: config.seedUserPassword, logger });
    if (!config.adminToken) logger.warn('ADMIN_TOKEN não configurado — rotas administrativas desabilitadas');

    const app = buildApp({ db });
    app.listen(config.port, () => logger.info(`LMS API rodando na porta ${config.port}`));
}

if (require.main === module) {
    start().catch((err) => {
        logger.error('Falha ao iniciar a aplicação', err);
        process.exit(1);
    });
}

module.exports = { buildApp };
