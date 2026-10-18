const { ValidationError, NotFoundError, AppError } = require('../utils/errors');
const { hashPassword } = require('../utils/password');
const { PAYMENT_STATUS } = require('../models/paymentModel');

function createCheckoutController({ db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentGateway, cache }) {
    async function findOrPrepareUser({ name, email, password }) {
        const existing = await userModel.findByEmail(email);
        if (existing) return { userId: existing.id };
        if (!password) throw new ValidationError('Bad Request');
        return { userId: null, newUser: { name, email, passwordHash: hashPassword(password) } };
    }

    return {
        async checkout({ name, email, password, courseId, cardNumber }) {
            if (!name || !email || !courseId || !cardNumber) throw new ValidationError('Bad Request');

            const course = await courseModel.findActiveById(courseId);
            if (!course) throw new NotFoundError('Curso não encontrado');

            const user = await findOrPrepareUser({ name, email, password });

            const paymentStatus = await paymentGateway.charge({ cardNumber, amount: course.price });
            if (paymentStatus === PAYMENT_STATUS.DENIED) throw new AppError('Pagamento recusado', 400);

            const { userId, enrollmentId } = await db.transaction(async () => {
                const id = user.userId || (await userModel.create(user.newUser));
                const newEnrollmentId = await enrollmentModel.create({ userId: id, courseId });
                await paymentModel.create({ enrollmentId: newEnrollmentId, amount: course.price, status: paymentStatus });
                await auditLogModel.record(`Checkout curso ${courseId} por ${id}`);
                return { userId: id, enrollmentId: newEnrollmentId };
            });

            cache.set(`last_checkout_${userId}`, course.title);
            return { enrollmentId };
        },
    };
}

module.exports = { createCheckoutController };
