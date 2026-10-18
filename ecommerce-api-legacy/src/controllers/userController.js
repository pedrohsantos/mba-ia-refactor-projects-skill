const { ValidationError, NotFoundError } = require('../utils/errors');

function createUserController({ db, userModel }) {
    return {
        async deleteUser(rawId) {
            const id = Number(rawId);
            if (!Number.isInteger(id) || id <= 0) throw new ValidationError('Bad Request');

            const deleted = await db.transaction(() => userModel.deleteById(id));
            if (!deleted) throw new NotFoundError('Usuário não encontrado');
        },
    };
}

module.exports = { createUserController };
