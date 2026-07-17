import Shell from "@/components/shell";

export default function Help() {
  return (
    <Shell active="/help">
      <h1>How it works</h1>
      <p className="dim">The 2nd Brain in five minutes — what it is, how it fills up, and what to do here.</p>
      <hr className="hairline" />

      <div className="note-body">
        <h2>What this is</h2>
        <p>
          Your company's shared memory: an organized vault of notes — companies, people, properties,
          projects, meetings, decisions, procedures — written and maintained by your AI agents, owned
          by you. Agents read it before answering questions and write to it as they work, so knowledge
          stops living in one person's head or a chat scrollback.
        </p>

        <h2>How knowledge gets in</h2>
        <p>
          You talk to your agents (Telegram, chat — wherever they live). They file what they learn:
          meeting summaries, new contacts, decisions, procedures. Everything an agent writes starts as{" "}
          <span className="badge unverified">unverified</span> — visible and searchable, but marked as
          unconfirmed until a human approves it. Approved notes become{" "}
          <span className="badge ok">canonical</span>: company truth.
        </p>
        <p>
          A new brain seeds itself through the <b>onboarding interview</b>: your admin agent asks
          about the business one question at a time and builds the first ~30–50 notes from your
          answers. The dashboard tracks its progress; the interview ends with a review where you
          confirm what's true — no buttons needed.
        </p>

        <h2>What each page is for</h2>
        <ul>
          <li><b>Dashboard</b> — the brain at a glance: size, what's awaiting review, recent agent activity.</li>
          <li><b>Review queue</b> — everything unconfirmed. Promote what's true, archive the rest — singly or in bulk. Your admin agent can run this with you conversationally instead.</li>
          <li><b>Graph</b> — the brain as a mind-map. Well-linked clusters mean healthy knowledge; orphan dots are notes nothing references yet.</li>
          <li><b>Agents</b> — who has access and with what role. Add an agent here and paste the shown token into its config; revoke and the access dies instantly (its notes and history remain).</li>
          <li><b>Vault</b> — read and search every note. Read-only by design: writes go through agents so everything stays audited.</li>
          <li><b>Audit</b> — every write, allowed or denied, forever. Who did what, when, to which note.</li>
        </ul>

        <h2>Getting the most out of it</h2>
        <ul>
          <li><b>Ask your agent, not your memory.</b> "What did we decide about X?" — the agent searches the brain and answers with sources.</li>
          <li><b>Send things in as they happen.</b> Paste a meeting link, forward a detail, mention a new contact — the agent files it properly.</li>
          <li><b>Do the weekly review.</b> Ten minutes: confirm or archive the week's unverified notes, here or in chat. This is what keeps the brain trustworthy.</li>
          <li><b>Never put secrets in it.</b> No passwords, API keys, or banking credentials — agents are instructed to refuse, and the audit trail watches.</li>
          <li><b>Roles keep it safe.</b> Editors write in their areas, contributors only to their inbox, and only the admin (that's you, via your agent) declares things true.</li>
        </ul>

        <h2>Where the data lives</h2>
        <p>
          Plain Markdown files on your own server — no lock-in. Backed up to a private Git repository
          you own (also openable in Obsidian, read-only). Server operations — updates, backups,
          verification — run from the <code>./brain</code> terminal console on the VPS.
        </p>
      </div>
    </Shell>
  );
}
