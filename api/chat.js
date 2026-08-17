/**
 * Vercel function entry for POST /api/chat (repo root).
 * Must be .js — Vercel does not detect .cjs as a Serverless Function.
 * `npm run build` writes ./_handler.cjs (CommonJS bundle).
 */
const bundled = require("./_handler.cjs");

module.exports = bundled.default || bundled;
module.exports.config = bundled.config || { maxDuration: 60 };
