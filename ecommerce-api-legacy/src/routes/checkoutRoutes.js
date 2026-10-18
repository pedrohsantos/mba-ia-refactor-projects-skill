const express = require('express');
const asyncHandler = require('../utils/asyncHandler');

function createCheckoutRoutes({ checkoutController }) {
    const router = express.Router();

    router.post('/api/checkout', asyncHandler(async (req, res) => {
        // Campos públicos do contrato (usr, eml, pwd, c_id, card) mapeados para nomes intencionais.
        const { usr: name, eml: email, pwd: password, c_id: courseId, card: cardNumber } = req.body || {};
        const { enrollmentId } = await checkoutController.checkout({ name, email, password, courseId, cardNumber });
        res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
    }));

    return router;
}

module.exports = { createCheckoutRoutes };
