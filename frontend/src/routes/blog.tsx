import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/blog")({
  head: () => ({
    meta: [
      { title: "Blog — Bachpan" },
      {
        name: "description",
        content: "Child marriage in India: a data-driven analysis based on Census insights.",
      },
    ],
  }),
  component: BlogPage,
});

function BlogPage() {
  return (
    <iframe
      src="/blog.html"
      title="Child Marriage in India: A Data-Driven Analysis"
      className="block h-screen w-full border-0"
    />
  );
}
