function createUserModel(db) {
    return {
        findByEmail(email) {
            return db.get('SELECT id, name, email FROM users WHERE email = ?', [email]);
        },

        findById(id) {
            return db.get('SELECT id, name, email FROM users WHERE id = ?', [id]);
        },

        async create({ name, email, passwordHash }) {
            const { lastID } = await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [name, email, passwordHash]);
            return lastID;
        },

        // Matrículas e pagamentos são removidos em cascata (FOREIGN KEY ... ON DELETE CASCADE).
        async deleteById(id) {
            const { changes } = await db.run('DELETE FROM users WHERE id = ?', [id]);
            return changes > 0;
        },
    };
}

module.exports = { createUserModel };
