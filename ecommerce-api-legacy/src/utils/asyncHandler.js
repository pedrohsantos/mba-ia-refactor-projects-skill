// Encaminha rejeições de handlers async para o middleware de erro do Express.
module.exports = (handler) => (req, res, next) => Promise.resolve(handler(req, res, next)).catch(next);
