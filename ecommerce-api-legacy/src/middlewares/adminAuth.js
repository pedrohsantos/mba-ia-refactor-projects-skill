const crypto = require('crypto');
const { ForbiddenError, UnauthorizedError } = require('../utils/errors');

function tokensMatch(provided, expected) {
    const a = Buffer.from(String(provided));
    const b = Buffer.from(String(expected));
    return a.length === b.length && crypto.timingSafeEqual(a, b);
}

// Rotas administrativas exigem X-Admin-Token; sem ADMIN_TOKEN configurado ficam desabilitadas.
function createAdminAuth({ adminToken }) {
    return (req, res, next) => {
        if (!adminToken) return next(new ForbiddenError('Rotas administrativas desabilitadas'));
        if (!tokensMatch(req.get('X-Admin-Token') || '', adminToken)) return next(new UnauthorizedError('Não autorizado'));
        return next();
    };
}

module.exports = { createAdminAuth };
