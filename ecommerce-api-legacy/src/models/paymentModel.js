const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

function createPaymentModel(db) {
    return {
        async create({ enrollmentId, amount, status }) {
            const { lastID } = await db.run(
                'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
                [enrollmentId, amount, status],
            );
            return lastID;
        },
    };
}

module.exports = { createPaymentModel, PAYMENT_STATUS };
