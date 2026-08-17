/**
 * Vercel entry for POST /api/chat.
 * `npm run build` writes the bundled agent to ./_handler.js (CJS).
 */
const bundled = require("./_handler.js");

module.exports = bundled.default || bundled;
module.exports.config = bundled.config || { maxDuration: 60 };
