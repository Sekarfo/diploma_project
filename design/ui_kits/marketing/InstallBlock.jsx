// Install method tab strip + snippet, exactly as on opencode.ai home.
function InstallBlock() {
  const [tab, setTab] = useState('curl');
  const cmds = {
    curl: 'curl -fsSL https://opencode.ai/install | bash',
    npm: 'npm i -g opencode',
    bun: 'bun add -g opencode',
    brew: 'brew install opencode',
    yay: 'yay -S opencode',
  };
  const [copied, setCopied] = useState(false);
  const copy = () => { setCopied(true); setTimeout(() => setCopied(false), 1200); };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 640 }}>
      <div style={{ display: 'flex', borderBottom: '1px solid var(--color-hairline-strong)', alignItems: 'flex-end' }}>
        {Object.keys(cmds).map((k) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            style={{
              background: 'transparent',
              color: tab === k ? 'var(--color-ink)' : 'var(--color-mute)',
              border: 0,
              borderRadius: 0,
              padding: '8px 16px',
              fontFamily: 'var(--font-mono)',
              fontSize: 16,
              fontWeight: 500,
              cursor: 'pointer',
              borderBottom: tab === k ? '2px solid var(--color-ash)' : '2px solid transparent',
              marginBottom: -1,
            }}
          >
            {k}
          </button>
        ))}
      </div>
      <div style={{
        background: 'var(--color-surface-card)',
        color: 'var(--color-ink)',
        padding: '12px 16px',
        borderRadius: 4,
        fontFamily: 'var(--font-mono)',
        fontSize: 16,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 16,
      }}>
        <span><span style={{ color: 'var(--color-mute)' }}>$</span> {cmds[tab]}</span>
        <span onClick={copy} style={{ cursor: 'pointer', color: copied ? 'var(--color-ink)' : 'var(--color-mute)', fontSize: 14 }}>
          {copied ? '[copied]' : '[copy]'}
        </span>
      </div>
    </div>
  );
}
Object.assign(window, { InstallBlock });
