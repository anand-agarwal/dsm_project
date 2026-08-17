import { describe, expect, it } from "vitest";
import {
  allAllowedHosts,
  duckDuckGoSiteFilter,
  isDeniedResearchHost,
  matchResearchSource,
  RESEARCH_SOURCES,
} from "./researchSources";

describe("researchSources", () => {
  it("has unique ids and no Wikipedia", () => {
    const ids = RESEARCH_SOURCES.map((s) => s.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(allAllowedHosts().some((h) => h.includes("wikipedia"))).toBe(false);
  });

  it("matches UNFPA India and UNICEF data subdomains", () => {
    expect(matchResearchSource("https://india.unfpa.org/en/publications/child-marriage-india-key-insights-nfhs-5")?.id).toBe(
      "unfpa",
    );
    expect(matchResearchSource("https://data.unicef.org/topic/child-protection/child-marriage/")?.id).toBe(
      "unicef",
    );
  });

  it("rejects Wikipedia even if DuckDuckGo returns it", () => {
    expect(isDeniedResearchHost("https://en.wikipedia.org/wiki/Child_marriage_in_India")).toBe(true);
    expect(matchResearchSource("https://en.wikipedia.org/wiki/Child_marriage_in_India")).toBeNull();
  });

  it("builds a site: filter the duckduckgo-search query can use", () => {
    const law = duckDuckGoSiteFilter("law");
    expect(law).toContain("site:indiacode.nic.in");
    expect(law).toContain("site:prsindia.org");
    expect(law).not.toContain("wikipedia");
  });
});
