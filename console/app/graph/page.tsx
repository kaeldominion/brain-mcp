import Shell from "@/components/shell";
import { brain } from "@/lib/brain";
import GraphView from "./view";

export default async function Graph() {
  const { nodes, edges } = await brain("/graph");
  return (
    <Shell active="/graph">
      <h1>Graph</h1>
      <p className="dim">
        The brain as a mind-map: every note is a node, every wikilink an edge. Colors are folders.
      </p>
      <hr className="hairline" />
      {nodes.length === 0 ? (
        <p className="empty">No notes yet — the graph grows as agents write.</p>
      ) : (
        <GraphView nodes={nodes} edges={edges} />
      )}
    </Shell>
  );
}
