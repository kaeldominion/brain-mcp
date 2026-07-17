import Link from "next/link";
import Shell from "@/components/shell";
import { brain } from "@/lib/brain";
import ReviewActions from "./actions";

export default async function Review() {
  const { items } = await brain("/review");
  return (
    <Shell active="/review">
      <h1>Review queue</h1>
      <p className="dim">Everything unverified plus every inbox item. Promote what's true; archive the rest.</p>
      <hr className="hairline" />
      {items.length === 0 ? (
        <p className="empty">Nothing unverified. The brain is clean.</p>
      ) : (
        <table>
          <thead>
            <tr><th>note</th><th>kind</th><th>agent</th><th>modified</th><th style={{ textAlign: "right" }}>actions</th></tr>
          </thead>
          <tbody>
            {items.map((i: any) => (
              <tr key={i.path}>
                <td>
                  <Link href={`/vault?path=${encodeURIComponent(i.path)}`}>{i.title ?? i.path}</Link>
                  <div className="dim mono" style={{ fontSize: 11.5 }}>{i.path}</div>
                </td>
                <td><span className={`badge ${i.kind}`}>{i.kind}</span></td>
                <td>{i.author_agent ?? "—"}</td>
                <td className="dim mono">{i.modified}</td>
                <td style={{ textAlign: "right" }}><ReviewActions path={i.path} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Shell>
  );
}
