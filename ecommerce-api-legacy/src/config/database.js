const sqlite3 = require('sqlite3');

// Envolve a API de callbacks do sqlite3 em Promises e oferece transações serializadas.
function createDatabase({ filename, verbose = false }) {
    const driver = verbose ? sqlite3.verbose() : sqlite3;
    const connection = new driver.Database(filename);
    let transactionQueue = Promise.resolve();

    function run(sql, params = []) {
        return new Promise((resolve, reject) => {
            connection.run(sql, params, function onRun(err) {
                if (err) return reject(err);
                resolve({ lastID: this.lastID, changes: this.changes });
            });
        });
    }

    function get(sql, params = []) {
        return new Promise((resolve, reject) => {
            connection.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
        });
    }

    function all(sql, params = []) {
        return new Promise((resolve, reject) => {
            connection.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
        });
    }

    function exec(sql) {
        return new Promise((resolve, reject) => {
            connection.exec(sql, (err) => (err ? reject(err) : resolve()));
        });
    }

    // A conexão é única: enfileira transações para que uma não intercale com outra.
    function transaction(work) {
        const result = transactionQueue.then(async () => {
            await run('BEGIN');
            try {
                const value = await work();
                await run('COMMIT');
                return value;
            } catch (err) {
                await run('ROLLBACK');
                throw err;
            }
        });
        transactionQueue = result.catch(() => {});
        return result;
    }

    function close() {
        return new Promise((resolve, reject) => connection.close((err) => (err ? reject(err) : resolve())));
    }

    return { run, get, all, exec, transaction, close };
}

module.exports = { createDatabase };
