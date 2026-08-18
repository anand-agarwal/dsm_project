import { createFileRoute } from "@tanstack/react-router";
import { SiteLayout } from "@/components/SiteLayout";
import { TathyaWorkspace } from "@/components/TathyaWorkspace";
import { AGENT_NAME } from "@/agent/identity";

export const Route = createFileRoute("/ask")({
  head: () => ({
    meta: [
      { title: `${AGENT_NAME} - Bachpan` },
      {
        name: "description",
        content:
          "Ask Tathya about India: Census C-series rates (currently 2001 and 2011) plus live search for policy, news, and later census rounds.",
      },
    ],
  }),
  component: AskPage,
});

function AskPage() {
  return (
    <SiteLayout footer={false} fill>
      <TathyaWorkspace />
    </SiteLayout>
  );
}
