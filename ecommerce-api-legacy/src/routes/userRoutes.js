const express = require('express');
const asyncHandler = require('../utils/asyncHandler');

function createUserRoutes({ userController, requireAdmin }) {
    const router = express.Router();

    router.delete('/api/users/:id', requireAdmin, asyncHandler(async (req, res) => {
        await userController.deleteUser(req.params.id);
        res.send('Usuário deletado');
    }));

    return router;
}

module.exports = { createUserRoutes };
