import { describe, expect, it } from "vitest";
import { TABLE_CARDS } from "./catalog";
import {
  detectMetrics,
  detectSocialGroup,
  formatLookupSchemaForModel,
  lookupSchema,
} from "./lookupSchema";

describe("detectSocialGroup", () => {
  it("detects SC from several phrasings", () => {
    expect(detectSocialGroup("literacy in Odisha for SC girls")).toBe("sc");
    expect(detectSocialGroup("Scheduled Caste female literacy")).toBe("sc");
    expect(detectSocialGroup("dalit girls in Bihar")).toBe("sc");
  });

  it("detects ST and religion", () => {
    expect(detectSocialGroup("ST literacy in Odisha")).toBe("st");
    expect(detectSocialGroup("tribal girls currently married")).toBe("st");
    expect(detectSocialGroup("Hindu female literacy")).toBe("religion");
  });

  it("returns null when no group is named", () => {
    expect(detectSocialGroup("literacy in Odisha for girls")).toBeNull();
  });
});

describe("detectMetrics", () => {
  it("maps literacy paraphrases", () => {
    expect(detectMetrics("what is the literacy in Odisha for SC girls")).toContain(
      "literacy_rate",
    );
    expect(detectMetrics("can girls read in Bihar")).toContain("literacy_rate");
  });

  it("maps marital and attendance paraphrases", () => {
    expect(detectMetrics("currently married SC girls")).toContain(
      "currently_married_share",
    );
    expect(detectMetrics("child labour among ST boys")).toContain(
      "not_attending_worker_share",
    );
  });
});

describe("lookupSchema", () => {
  it("returns nothing for an empty query", () => {
    const result = lookupSchema({ query: "" });
    expect(result.cards).toEqual([]);
  });

  it("ranks raw_c_08_sc first for Odisha SC girls literacy", () => {
    const result = lookupSchema({
      query: "what is the literacy in Odisha for SC girls",
    });
    expect(result.detectedSocialGroup).toBe("sc");
    expect(result.detectedMetrics).toContain("literacy_rate");
    expect(result.cards.length).toBeGreaterThan(0);
    expect(result.cards[0].postgresTable).toBe("raw_c_08_sc");
    expect(result.cards[0].metrics.some((m) => m.id === "literacy_rate")).toBe(
      true,
    );
    const lit = result.cards[0].metrics.find((m) => m.id === "literacy_rate");
    expect(lit?.numerator.females).toBe("females_10");
    expect(lit?.denominator?.females).toBe("females_4");
  });

  it("does not pick a marital-status table for a literacy question", () => {
    const result = lookupSchema({
      query: "what is the literacy in Odisha for SC girls",
    });
    expect(result.cards[0].censusTable).toBe("C-08");
    expect(result.cards.some((c) => c.censusTable === "C-02")).toBe(false);
  });

  it("defaults to total C-08 when no social group is named", () => {
    const result = lookupSchema({ query: "can girls read in Bihar" });
    expect(result.detectedSocialGroup).toBeNull();
    expect(result.cards[0].postgresTable).toBe("raw_c_08");
    expect(result.cards[0].socialGroup).toBe("total");
  });

  it("routes religion literacy to C-09", () => {
    const result = lookupSchema({ query: "Hindu female literacy in Kerala" });
    expect(result.detectedSocialGroup).toBe("religion");
    expect(result.cards[0].postgresTable).toBe("raw_c_09");
  });

  it("routes currently-married SC questions to C-02 SC", () => {
    const result = lookupSchema({
      query: "currently married SC girls in Rajasthan",
    });
    expect(result.cards[0].postgresTable).toBe("raw_c_02_sc");
  });

  it("routes school attendance ST to C-12 ST", () => {
    const result = lookupSchema({
      query: "school attendance among ST children in Odisha",
    });
    expect(result.cards[0].postgresTable).toBe("raw_c_12_st");
  });

  it("routes age-at-marriage questions to C-04", () => {
    const result = lookupSchema({ query: "age at marriage in Bihar 2011" });
    expect(result.cards[0].censusTable).toBe("C-04");
  });

  it("honours an explicit socialGroup override", () => {
    const result = lookupSchema({ query: "literacy", socialGroup: "st" });
    expect(result.cards[0].postgresTable).toBe("raw_c_08_st");
  });

  it("honours limit", () => {
    const result = lookupSchema({ query: "literacy", limit: 1 });
    expect(result.cards).toHaveLength(1);
  });

  it("boosts an explicit census table id", () => {
    const result = lookupSchema({ query: "C-12 for Odisha" });
    expect(result.cards[0].censusTable).toBe("C-12");
  });

  it("exposes twins so the next tool can switch SC/ST", () => {
    const card = lookupSchema({ query: "literacy SC" }).cards[0];
    expect(card.twins.sc).toBe("raw_c_08_sc");
    expect(card.twins.total).toBe("raw_c_08");
  });

  it("formats a compact payload for the model", () => {
    const formatted = formatLookupSchemaForModel(
      lookupSchema({ query: "literacy in Odisha for SC girls" }),
    );
    expect(formatted.cards[0]).not.toHaveProperty("synonyms");
    expect(formatted.cards[0].postgresTable).toBe("raw_c_08_sc");
  });
});

describe("catalog", () => {
  it("has unique ids and postgres table names among primary cards", () => {
    const ids = TABLE_CARDS.map((c) => c.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
