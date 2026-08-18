/**
 * Vercel function entry (must be .js/.ts - Vercel does not treat .cjs as a
 * Serverless Function, so `functions["api/chat.cjs"]` fails the pattern check).
 *
 * api/package.json sets "type": "commonjs" so this file can require() even when
 * frontend/package.json is "type": "module".
 *
 * The agent is bundled to _handler.cjs: Node always evaluates .cjs as CommonJS,
 * so @vercel/oidc's require("path") works.
 */
const bundled = require("./_handler.cjs");

module.exports = bundled.default || bundled;
module.exports.config = bundled.config || { maxDuration: 60 };
