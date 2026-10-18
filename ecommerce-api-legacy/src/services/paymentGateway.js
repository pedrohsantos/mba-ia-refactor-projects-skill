const { PAYMENT_STATUS } = require('../models/paymentModel');

// Gateway simulado: cartões iniciados por este prefixo são aprovados (mesma regra do sistema legado).
const APPROVED_CARD_PREFIX = '4';
const VISIBLE_CARD_DIGITS = 4;

function maskCard(cardNumber) {
    return `****${String(cardNumber).slice(-VISIBLE_CARD_DIGITS)}`;
}

function createPaymentGateway({ apiKey, logger }) {
    return {
        async charge({ cardNumber, amount }) {
            // Nunca registrar o número completo do cartão nem a chave do gateway.
            logger.info(`Processando pagamento de ${amount} no cartão ${maskCard(cardNumber)} (gateway ${apiKey ? 'configurado' : 'simulado'})`);
            return String(cardNumber).startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
        },
    };
}

module.exports = { createPaymentGateway };
