/**
 * Vercel entry when Root Directory is `frontend`.
 * This folder's package.json sets "type": "commonjs" so require() works
 * even though frontend/package.json is "type": "module".
 */
const bundled = require("./_handler.js");

module.exports = bundled.default || bundled;
module.exports.config = bundled.config || { maxDuration: 60 };
