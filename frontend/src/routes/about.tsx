import { createFileRoute, Link } from "@tanstack/react-router";
import { SiteLayout } from "@/components/SiteLayout";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "About — Bachpan" },
      { name: "description", content: "How this atlas is built, the indicators it uses, and what the numbers mean." },
    ],
  }),
  component: About,
});

function About() {
  return (
    <SiteLayout>
      <article className="max-w-[760px] mx-auto px-6 py-16 prose-like">
        <div className="eyebrow">Editor's note</div>
        <h1 className="font-display text-5xl tracking-tight mt-1">About this atlas</h1>
        <p className="mt-6 text-lg leading-relaxed dropcap">
          Bachpan is a reading of India's 2001 and 2011 decennial censuses, focused on a single
          question: how often, and where, do Indian children become spouses? The atlas threads child
          marriage through literacy, dropout, work, and social identity — the structural variables that
          shape it.
        </p>

        <h2 className="font-display text-2xl mt-10">What's measured</h2>
        <ul className="mt-3 space-y-2 text-foreground/85">
          <li><strong>CMPR</strong> — the share of an age cohort reported "ever married" in C-02 / C-03.</li>
          <li><strong>Education</strong> — literacy and educational attainment from C-08 / C-09.</li>
          <li><strong>Schooling</strong> — attendance and child-labour from C-12.</li>
          <li><strong>Worker category</strong> — economic activity by marriage status from C-07.</li>
          <li><strong>Social splits</strong> — SC, ST, and religion from C-02 / C-03 / C-05.</li>
        </ul>

        <h2 className="font-display text-2xl mt-10">A note on the data</h2>
        <p className="mt-3 text-foreground/85">
          The figures shown in this preview build are <em>synthetic but realistic</em>: state ordering,
          year-on-year direction, and worker-category gradients are calibrated to reflect publicly known
          patterns. Real Census tables can be loaded once the data layer is wired up.
        </p>

        <div className="mt-10 flex gap-4">
          <Link to="/" className="bg-ink text-paper px-4 py-2 rounded text-sm">Open the atlas</Link>
          <Link to="/explore" className="border border-rule px-4 py-2 rounded text-sm">Browse raw tables</Link>
        </div>
      </article>
    </SiteLayout>
  );
}
