const express = require('express');
const asyncHandler = require('../utils/asyncHandler');

function createAdminRoutes({ reportController, requireAdmin }) {
    const router = express.Router();

    router.get('/api/admin/financial-report', requireAdmin, asyncHandler(async (req, res) => {
        res.json(await reportController.financialReport());
    }));

    return router;
}

module.exports = { createAdminRoutes };
