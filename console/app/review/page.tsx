import Shell from "@/components/shell";
import { brain } from "@/lib/brain";
import ReviewTable from "./table";

export default async function Review() {
  const { items } = await brain("/review");
  return (
    <Shell active="/review">
      <h1>Review queue</h1>
      <p className="dim">
        Everything unverified plus every inbox item. Promote what's true; archive the rest — singly
        or in bulk. Tip: your admin agent can do this conversationally too ("review the unverified
        notes with me"), and a fresh onboarding always starts with a large batch here.
      </p>
      <hr className="hairline" />
      <ReviewTable items={items} />
    </Shell>
  );
}
