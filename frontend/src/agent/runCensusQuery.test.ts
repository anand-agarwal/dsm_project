import { describe, expect, it } from "vitest";
import { resolveAgeLabels } from "./ageBrackets";
import {
  censusYearInputSchema,
  compileCensusQuery,
  computeMetricFromRows,
  computeRate,
  parseCensusNumber,
  resolveCard,
  resolveCensusState,
  runCensusQuery,
} from "./runCensusQuery";

describe("censusYearInputSchema", () => {
  it("accepts JSON number or string years", () => {
    expect(censusYearInputSchema.parse(2011)).toBe(2011);
    expect(censusYearInputSchema.parse("2011")).toBe("2011");
    expect(censusYearInputSchema.parse(2001)).toBe(2001);
    expect(censusYearInputSchema.parse("2001")).toBe("2001");
    expect(() => censusYearInputSchema.parse(2021)).toThrow();
  });
});

describe("resolveCensusState", () => {
  it("maps Orissa to ODISHA search token", () => {
    expect(resolveCensusState("Orissa")).toEqual({
      canonical: "Odisha",
      searchToken: "ODISHA",
    });
  });

  it("unwraps Census area_name labels and phrases", () => {
    expect(resolveCensusState("State - RAJASTHAN (08)")).toEqual({
      canonical: "Rajasthan",
      searchToken: "RAJASTHAN",
    });
    expect(resolveCensusState("ST females in Rajasthan")).toEqual({
      canonical: "Rajasthan",
      searchToken: "RAJASTHAN",
    });
  });

  it("accepts India", () => {
    expect(resolveCensusState("India").searchToken).toBe("INDIA");
  });
});

describe("resolveCard", () => {
  it("picks raw_c_08_sc for SC literacy", () => {
    const card = resolveCard({ metric: "literacy_rate", socialGroup: "sc" });
    expect(card.postgresTable).toBe("raw_c_08_sc");
  });

  it("switches twins when cardId is total but socialGroup is sc", () => {
    const card = resolveCard({
      cardId: "c08_total",
      metric: "literacy_rate",
      socialGroup: "sc",
    });
    expect(card.postgresTable).toBe("raw_c_08_sc");
  });

  it("rejects a metric the card cannot compute", () => {
    expect(() =>
      resolveCard({ cardId: "c08_sc", metric: "currently_married_share" }),
    ).toThrow(/cannot compute/);
  });
});

describe("compileCensusQuery", () => {
  it("compiles the Odisha SC girls literacy example", () => {
    const compiled = compileCensusQuery({
      year: 2011,
      state: "Odisha",
      sex: "female",
      socialGroup: "sc",
      metric: "literacy_rate",
      area: "Total",
      ageBand: "all",
    });
    expect(compiled.postgresTable).toBe("raw_c_08_sc");
    expect(compiled.select).toContain("females_4");
    expect(compiled.select).toContain("females_10");
    expect(compiled.select).not.toContain("*");
    expect(compiled.filters).toEqual(
      expect.arrayContaining([
        { op: "eq", column: "year", value: 2011 },
        { op: "eq", column: "total_rural_urban", value: "Total" },
        { op: "ilike", column: "area_name", value: "%ODISHA%" },
        { op: "in", column: "distt_code", values: ["000", "00", "0"] },
        { op: "eq", column: "age_group_1", value: "All ages" },
      ]),
    );
  });

  it("expands age_14_17 on C-08 to four single-year labels", () => {
    const compiled = compileCensusQuery({
      year: 2011,
      state: "Odisha",
      socialGroup: "sc",
      metric: "literacy_rate",
      ageBand: "age_14_17",
    });
    const age = compiled.filters.find((f) => f.column === "age_group_1");
    expect(age).toEqual({
      op: "in",
      column: "age_group_1",
      values: ["14", "15", "16", "17"],
    });
    expect(compiled.aggregateAgeLabels).toEqual(["14", "15", "16", "17"]);
  });

  it("maps C-02 age_14_17 to the 15-19 Census band", () => {
    expect(resolveAgeLabels("C-02", "age_14_17").labels).toEqual(["15-19"]);
    const compiled = compileCensusQuery({
      year: 2011,
      state: "Rajasthan",
      socialGroup: "sc",
      metric: "currently_married_share",
      ageBand: "14-17",
    });
    expect(compiled.postgresTable).toBe("raw_c_02_sc");
    expect(compiled.filters).toEqual(
      expect.arrayContaining([{ op: "eq", column: "age_group_1", value: "15-19" }]),
    );
  });

  it("compiles ST currently-married in Rajasthan to C-02 ST All ages", () => {
    const compiled = compileCensusQuery({
      year: "2011",
      state: "State - RAJASTHAN (08)",
      sex: "female",
      socialGroup: "st",
      metric: "currently_married_share",
      ageBand: "ST females",
    });
    expect(compiled.postgresTable).toBe("raw_c_02_st");
    expect(compiled.filters).toEqual(
      expect.arrayContaining([
        { op: "eq", column: "year", value: 2011 },
        { op: "eq", column: "total_rural_urban", value: "Total" },
        { op: "ilike", column: "area_name", value: "%RAJASTHAN%" },
        { op: "in", column: "distt_code", values: ["000", "00", "0"] },
        { op: "eq", column: "age_group_1", value: "All ages" },
      ]),
    );
  });

  it("requires religion on C-09", () => {
    expect(() =>
      compileCensusQuery({
        year: 2011,
        state: "Kerala",
        metric: "literacy_rate",
        socialGroup: "religion",
      }),
    ).toThrow(/religion/);
  });

  it("rejects unknown keys that look like SQL", () => {
    expect(() =>
      compileCensusQuery({
        year: 2011,
        state: "Odisha",
        metric: "literacy_rate",
        cardId: "c08_sc; drop table",
      }),
    ).toThrow(/Unknown cardId/);
  });

  it("rejects invalid year", () => {
    expect(() =>
      compileCensusQuery({
        year: 1991,
        state: "Odisha",
        metric: "literacy_rate",
      }),
    ).toThrow(/Invalid census query/);
  });
});

describe("computeMetricFromRows", () => {
  it("parses text counts and returns a percent", () => {
    expect(parseCensusNumber("1,825,159")).toBe(1825159);
    expect(computeRate(1825159, 3570655)).toBe(Number(((1825159 / 3570655) * 100).toFixed(4)));
  });

  it("sums C-08 single-year rows for a bracket", () => {
    const compiled = compileCensusQuery({
      year: 2011,
      state: "Odisha",
      socialGroup: "sc",
      metric: "literacy_rate",
      sex: "female",
      ageBand: "age_14_17",
    });
    const computed = computeMetricFromRows(compiled, [
      { females_10: "10", females_4: "40" },
      { females_10: "20", females_4: "60" },
    ]);
    expect(computed.numerator).toBe(30);
    expect(computed.denominator).toBe(100);
    expect(computed.value).toBe(30);
    expect(computed.sourceRowCount).toBe(2);
  });

  it("returns null rate when the denominator is zero", () => {
    const compiled = compileCensusQuery({
      year: 2011,
      state: "Goa",
      metric: "literacy_rate",
    });
    const computed = computeMetricFromRows(compiled, [{ females_10: "0", females_4: "0" }]);
    expect(computed.value).toBeNull();
  });
});

describe("runCensusQuery", () => {
  it("returns a structured error for bad DSL without hitting the database", async () => {
    const result = await runCensusQuery({ year: 2011, metric: "literacy_rate" });
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/Invalid census query/);
    expect(result.compiled).toBeNull();
  });

  it("computes from an injected fetcher", async () => {
    const result = await runCensusQuery(
      {
        year: 2011,
        state: "Odisha",
        socialGroup: "sc",
        sex: "female",
        metric: "literacy_rate",
      },
      {
        fetchRows: async () => [
          {
            area_name: "State - ODISHA",
            females_4: "3570655",
            females_10: "1825159",
          },
        ],
      },
    );
    expect(result.ok).toBe(true);
    expect(result.computed?.value).toBe(Number(((1825159 / 3570655) * 100).toFixed(4)));
    expect(result.computed?.numeratorColumn).toBe("females_10");
    expect(result.computed?.denominatorColumn).toBe("females_4");
  });

  it("surfaces a hint when the fetcher returns no rows", async () => {
    const result = await runCensusQuery(
      { year: 2011, state: "Odisha", metric: "literacy_rate" },
      { fetchRows: async () => [] },
    );
    expect(result.ok).toBe(true);
    expect(result.hint).toMatch(/0 rows/);
    expect(result.computed).toBeNull();
  });
});

const hasLive = Boolean(process.env.VITE_SUPABASE_URL && process.env.VITE_SUPABASE_ANON_KEY);

describe.skipIf(!hasLive)("runCensusQuery live Supabase", () => {
  it("returns SC female literacy for Odisha 2011 All ages", async () => {
    const result = await runCensusQuery({
      year: 2011,
      state: "Odisha",
      socialGroup: "sc",
      sex: "female",
      metric: "literacy_rate",
      area: "Total",
      ageBand: "all",
    });
    if (!result.ok) {
      throw new Error(result.error);
    }
    if (result.computed === null) {
      throw new Error(result.hint ?? "no rows from live Supabase");
    }
    expect(result.compiled?.postgresTable).toBe("raw_c_08_sc");
    expect(result.computed.denominator).toBe(3570655);
    expect(result.computed.numerator).toBe(1825159);
    expect(result.computed.value).toBe(Number(((1825159 / 3570655) * 100).toFixed(4)));
  });

  it("returns ST female currently-married share for Rajasthan 2011 All ages", async () => {
    const result = await runCensusQuery({
      year: 2011,
      state: "Rajasthan",
      socialGroup: "st",
      sex: "female",
      metric: "currently_married_share",
      area: "Total",
      ageBand: "all",
    });
    if (!result.ok) {
      throw new Error(result.error);
    }
    if (result.computed === null) {
      throw new Error(result.hint ?? "no rows from live Supabase");
    }
    expect(result.compiled?.postgresTable).toBe("raw_c_02_st");
    expect(result.computed.denominator).toBe(4495591);
    expect(result.computed.numerator).toBe(2123951);
    expect(result.computed.value).toBe(Number(((2123951 / 4495591) * 100).toFixed(4)));
  });
});
