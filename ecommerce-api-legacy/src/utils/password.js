const crypto = require('crypto');

const KEY_LENGTH = 64;
const SALT_BYTES = 16;

function hashPassword(plain) {
    const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
    const hash = crypto.scryptSync(plain, salt, KEY_LENGTH).toString('hex');
    return `scrypt:${salt}:${hash}`;
}

function verifyPassword(plain, stored) {
    const [scheme, salt, hash] = String(stored).split(':');
    if (scheme !== 'scrypt' || !salt || !hash) return false;
    const expected = Buffer.from(hash, 'hex');
    const actual = crypto.scryptSync(plain, salt, expected.length);
    return crypto.timingSafeEqual(expected, actual);
}

module.exports = { hashPassword, verifyPassword };
