// Logger mínimo com níveis; substituível por pino/winston sem alterar quem o usa.
function format(level, message) {
    return `${new Date().toISOString()} ${level.toUpperCase()} ${message}`;
}

const logger = {
    info: (message) => console.log(format('info', message)),
    warn: (message) => console.warn(format('warn', message)),
    error: (message, err) => console.error(format('error', message), err && err.stack ? err.stack : err || ''),
};

module.exports = logger;
