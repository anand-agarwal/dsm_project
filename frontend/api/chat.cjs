/**
 * Vercel entry when Root Directory is `frontend`.
 * Must be .cjs: frontend/package.json has "type": "module".
 * `npm run build` writes the bundled agent to ./_handler.cjs.
 */
const bundled = require("./_handler.cjs");

module.exports = bundled.default || bundled;
module.exports.config = bundled.config || { maxDuration: 60 };
