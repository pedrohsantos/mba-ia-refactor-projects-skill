const { PAYMENT_STATUS } = require('../models/paymentModel');

const UNKNOWN_STUDENT = 'Unknown';

function createReportController({ courseModel }) {
    return {
        async financialReport() {
            const rows = await courseModel.listEnrollmentsWithPayments();
            const reportByCourse = new Map();

            for (const row of rows) {
                if (!reportByCourse.has(row.course_id)) {
                    reportByCourse.set(row.course_id, { course: row.course_title, revenue: 0, students: [] });
                }
                if (row.enrollment_id === null) continue;

                const courseReport = reportByCourse.get(row.course_id);
                if (row.payment_status === PAYMENT_STATUS.PAID) {
                    courseReport.revenue += row.payment_amount;
                }
                courseReport.students.push({
                    student: row.student_name || UNKNOWN_STUDENT,
                    paid: row.payment_amount || 0,
                });
            }

            return [...reportByCourse.values()];
        },
    };
}

module.exports = { createReportController };
