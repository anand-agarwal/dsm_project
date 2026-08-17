import type { IncomingMessage, ServerResponse } from "node:http";
import type { Plugin } from "vite";
import { handleCensusChatNode } from "./src/agent/chatHandler";

export function censusChatApiPlugin(): Plugin {
  return {
    name: "census-chat-api",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url?.split("?")[0] ?? "";
        if (url !== "/api/chat") {
          next();
          return;
        }
        void handleCensusChatNode(req as IncomingMessage, res as ServerResponse).catch((err: unknown) => {
          if (!res.headersSent) {
            res.statusCode = 500;
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ error: err instanceof Error ? err.message : "Chat handler failed" }));
          }
        });
      });
    },
  };
}
