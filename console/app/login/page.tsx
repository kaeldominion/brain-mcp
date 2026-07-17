const ERRORS: Record<string, string> = {
  missing: "Paste a token to sign in.",
  invalid: "That token isn't recognized.",
  role: "That's an agent token. The console needs a console or admin token (create one: ./brain console).",
};

export default async function Login({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  return (
    <div className="login-wrap">
      <div className="login-box">
        <div className="wordmark" style={{ fontSize: 22, marginBottom: 6 }}>
          2nd <span className="grad-text">Brain</span> Console
        </div>
        <p className="dim" style={{ marginBottom: 20 }}>
          The control room for your Company 2nd Brain.
        </p>
        <hr className="hairline" />
        <form method="post" action="/api/session">
          <label className="dim" style={{ display: "block", marginBottom: 6 }}>
            Console token
          </label>
          <input
            type="password"
            name="token"
            placeholder="paste your console or admin token"
            style={{ width: "100%", marginBottom: 12 }}
            autoFocus
          />
          {error && (
            <p style={{ color: "var(--red)", fontSize: 13, marginBottom: 12 }}>{ERRORS[error] ?? "Sign-in failed."}</p>
          )}
          <button className="btn btn-primary" style={{ width: "100%", padding: "10px 0" }}>
            Sign in
          </button>
        </form>
        <p className="dim" style={{ marginTop: 28, fontSize: 11.5 }}>
          2nd Brain MCP · by Sentient Labs
        </p>
      </div>
    </div>
  );
}
