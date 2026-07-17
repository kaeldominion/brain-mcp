import Shell from "@/components/shell";
import { brain } from "@/lib/brain";
import { AddAgent, AgentRowActions } from "./ui";

export default async function Agents() {
  const { clients } = await brain("/clients");
  const roles = ["editor", "contributor"];
  return (
    <Shell active="/agents">
      <h1>Agents</h1>
      <p className="dim">
        Every agent is an external MCP client with its own token and role. Adding one here is instant — no restarts.
      </p>
      <hr className="hairline" />
      <AddAgent roles={roles} />
      <table>
        <thead>
          <tr><th>name</th><th>role</th><th>source</th><th style={{ textAlign: "right" }}>actions</th></tr>
        </thead>
        <tbody>
          {clients.map((c: any) => (
            <tr key={c.name}>
              <td>{c.name}</td>
              <td><span className="badge">{c.role}</span></td>
              <td className="dim">{c.source}</td>
              <td style={{ textAlign: "right" }}>
                <AgentRowActions name={c.name} source={c.source} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="dim" style={{ marginTop: 16, fontSize: 12.5 }}>
        <b>server-managed</b> = the bootstrap admin (and any pre-registry agents): rotate those with
        ./brain on the server. Everything added here is instant and fully manageable. Revoking an
        agent kills its token immediately — its notes and audit history remain, stamped with its name.
      </p>
    </Shell>
  );
}
