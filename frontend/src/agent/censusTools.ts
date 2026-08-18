import { z } from "zod";
import { tool } from "ai";
import { METRIC_IDS } from "./types";
import { formatLookupSchemaForModel, lookupSchema } from "./lookupSchema";
import { formatCensusQueryForModel, runCensusQuery } from "./runCensusQuery";
import { formatSearchResearchForModel, searchResearch } from "./searchResearch";

const socialGroupSchema = z.enum(["total", "sc", "st", "religion"]);

export const censusAgentTools = {
  lookup_schema: tool({
    description:
      "Find which Census of India C-table and columns answer a question. Call this before run_census_query when you are unsure of the table, metric, or SC/ST twin.",
    inputSchema: z.object({
      query: z
        .string()
        .min(1)
        .describe("The user question or a short schema hint, e.g. 'SC female literacy'"),
      socialGroup: socialGroupSchema.optional(),
      metricId: z.enum(METRIC_IDS).optional(),
    }),
    execute: async ({ query, socialGroup, metricId }) =>
      formatLookupSchemaForModel(lookupSchema({ query, socialGroup, metricId })),
  }),

  run_census_query: tool({
    description:
      "Run a typed Census of India C-series query against Postgres. Never invent SQL. Rates are computed in code. Queryable years are currently 2001 or 2011 only.",
    inputSchema: z.object({
      cardId: z
        .string()
        .optional()
        .describe("Catalog id from lookup_schema, e.g. c08_sc. Optional if metric + socialGroup are set."),
      year: z.union([z.literal(2001), z.literal(2011), z.literal("2001"), z.literal("2011")]),
      state: z
        .string()
        .min(1)
        .describe("A single state or UT name only, e.g. Rajasthan or Odisha. Not 'State - RAJASTHAN'."),
      area: z.enum(["Total", "Rural", "Urban"]).optional(),
      sex: z.enum(["persons", "male", "female"]).optional(),
      socialGroup: socialGroupSchema.optional(),
      metric: z.enum(METRIC_IDS),
      ageBand: z
        .string()
        .optional()
        .describe("Omit unless the user named an age. Use all, age_14_17, 15-19, or a raw Census age label."),
      religion: z.string().optional().describe("Required for religion tables, e.g. Hindu"),
    }),
    execute: async (input) => formatCensusQueryForModel(await runCensusQuery(input)),
  }),

  web_search: tool({
    description:
      "Live web search via Firecrawl (then DuckDuckGo / OpenAlex). Use for latest news, census operations after 2011, other surveys (NFHS), laws, schemes, definitions, and any question not answered by C-series tables. Always call this when the user asks to search or asks what is current. Never use this for Census C-table rates - those come from run_census_query.",
    inputSchema: z.object({
      query: z
        .string()
        .min(1)
        .describe("Search terms, e.g. 'Prohibition of Child Marriage Act 2006'"),
    }),
    execute: async ({ query }) => formatSearchResearchForModel(await searchResearch({ query })),
  }),
};
