/**
 * Vercel entry when Root Directory is `frontend`.
 * .cjs so Node uses CommonJS even though frontend/package.json is "type": "module".
 */
const bundled = require("./_handler.cjs");

module.exports = bundled.default || bundled;
module.exports.config = bundled.config || { maxDuration: 60 };
