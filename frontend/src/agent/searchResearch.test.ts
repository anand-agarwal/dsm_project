import { describe, expect, it } from "vitest";
import {
  parseDdgHtml,
  parseFirecrawlSearch,
  parseOpenAlexWorks,
  searchResearch,
  toResearchHits,
  unwrapDdgHref,
} from "./searchResearch";

const FIXTURE = `
<html><body>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Findiacode.nic.in%2Fhandle%2F123456789%2Fpcma">
  Prohibition of Child Marriage Act, 2006
</a>
<a class="result__snippet" href="#">Full Act text on India Code</a>
<a class="result__a" href="https://en.wikipedia.org/wiki/Child_marriage_in_India">Child marriage in India</a>
<a class="result__snippet" href="#">Wikipedia article</a>
<a class="result__a" href="https://www.unicef.org/protection/child-marriage">UNICEF child marriage</a>
<a class="result__snippet" href="#">UNICEF programme page</a>
</body></html>
`;

describe("parseDdgHtml", () => {
  it("unwraps DDG redirect links", () => {
    expect(
      unwrapDdgHref("//duckduckgo.com/l/?uddg=https%3A%2F%2Findiacode.nic.in%2Fact%2Fpcma"),
    ).toBe("https://indiacode.nic.in/act/pcma");
  });

  it("keeps every host, including Wikipedia", () => {
    const raw = parseDdgHtml(FIXTURE);
    expect(raw.map((h) => h.url)).toEqual([
      "https://indiacode.nic.in/handle/123456789/pcma",
      "https://en.wikipedia.org/wiki/Child_marriage_in_India",
      "https://www.unicef.org/protection/child-marriage",
    ]);
    const hits = toResearchHits(raw);
    expect(hits).toHaveLength(3);
    expect(hits.find((h) => h.url.includes("wikipedia"))).toBeTruthy();
    expect(hits.find((h) => h.sourceId === "unicef")?.org).toMatch(/UNICEF/);
  });
});

describe("parseFirecrawlSearch / parseOpenAlexWorks", () => {
  it("reads Firecrawl v1 data[]", () => {
    expect(
      parseFirecrawlSearch({
        data: [{ title: "Hello", url: "https://example.com/a", description: "desc" }],
      }),
    ).toEqual([{ title: "Hello", url: "https://example.com/a", snippet: "desc" }]);
  });

  it("reads OpenAlex works", () => {
    const hits = parseOpenAlexWorks({
      results: [{ display_name: "A paper", doi: "10.1/xyz", publication_year: 2019 }],
    });
    expect(hits[0]?.url).toBe("https://doi.org/10.1/xyz");
  });
});

describe("searchResearch", () => {
  it("returns structured hits through an injected fetcher", async () => {
    const result = await searchResearch(
      { query: "PCMA 2006" },
      { fetch: async () => new Response(FIXTURE, { status: 200 }) },
    );
    expect(result.ok).toBe(true);
    expect(result.hits).toHaveLength(3);
    expect(result.hits.some((h) => h.url.includes("wikipedia"))).toBe(true);
  });

  it("falls back to OpenAlex when DuckDuckGo serves a bot check", async () => {
    const blocked = `<html><div class="anomaly-modal__modal" data-testid="anomaly-modal"></div></html>`;
    const result = await searchResearch(
      { query: "PCMA West Bengal" },
      {
        firecrawlKey: null,
        fetch: async (url) => {
          const u = String(url);
          if (u.includes("duckduckgo")) return new Response(blocked, { status: 202 });
          if (u.includes("openalex")) {
            return Response.json({
              results: [
                {
                  display_name: "Child marriage in West Bengal",
                  doi: "https://doi.org/10.1234/wb",
                  publication_year: 2020,
                },
              ],
            });
          }
          throw new Error(u);
        },
      },
    );
    expect(result.ok).toBe(true);
    expect(result.backend).toBe("openalex");
    expect(result.hits[0]?.url).toContain("doi.org");
  });

  it("uses Firecrawl when a key is set", async () => {
    const result = await searchResearch(
      { query: "PCMA" },
      {
        firecrawlKey: "fc-test",
        fetch: async (url) => {
          const u = String(url);
          if (u.includes("firecrawl.dev")) {
            return Response.json({
              success: true,
              data: [{ title: "PCMA 2006", url: "https://indiacode.nic.in/pcma", description: "Act text" }],
            });
          }
          throw new Error(u);
        },
      },
    );
    expect(result.ok).toBe(true);
    expect(result.backend).toBe("firecrawl");
    expect(result.hits[0]?.sourceId).toBe("india-code");
  });

  it("rejects an empty query without fetching", async () => {
    const result = await searchResearch(
      { query: "  " },
      {
        fetch: async () => {
          throw new Error("should not fetch");
        },
      },
    );
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/query/i);
  });
});
