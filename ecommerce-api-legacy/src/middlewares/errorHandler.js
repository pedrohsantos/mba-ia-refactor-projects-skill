const { AppError } = require('../utils/errors');

// Registrado por último: converte erros de domínio em status HTTP e esconde detalhes de erros inesperados.
function createErrorHandler({ logger }) {
    // eslint-disable-next-line no-unused-vars
    return (err, req, res, next) => {
        if (err instanceof AppError) {
            return res.status(err.statusCode).send(err.message);
        }
        if (err.type === 'entity.parse.failed') {
            return res.status(400).send('Bad Request');
        }
        logger.error(`Erro não tratado em ${req.method} ${req.originalUrl}`, err);
        return res.status(500).send('Erro interno');
    };
}

module.exports = { createErrorHandler };
