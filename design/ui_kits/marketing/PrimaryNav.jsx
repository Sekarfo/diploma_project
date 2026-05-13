// Primary nav with ASCII wordmark + link cluster + Download CTA.
function PrimaryNav({ current = 'home', onNavigate }) {
  const links = [
    { id: 'github', label: 'GitHub', meta: '[150K]' },
    { id: 'docs', label: 'Docs' },
    { id: 'zen', label: 'Zen' },
    { id: 'go', label: 'Go' },
    { id: 'enterprise', label: 'Enterprise' },
  ];
  return (
    <nav style={{
      height: 56,
      background: 'var(--color-canvas)',
      borderBottom: '1px solid var(--color-hairline)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 24px',
      gap: 24,
      fontFamily: 'var(--font-mono)',
    }}>
      <a onClick={() => onNavigate('home')} style={{ cursor: 'pointer', textDecoration: 'none', display: 'block' }}>
        <Wordmark size={6} />
      </a>
      <div style={{ flex: 1, display: 'flex', gap: 20, justifyContent: 'flex-end', alignItems: 'center', fontSize: 14, fontWeight: 500, color: 'var(--color-ink)' }}>
        {links.map((l) => (
          <span
            key={l.id}
            onClick={() => onNavigate && onNavigate(l.id)}
            style={{
              cursor: 'pointer',
              color: current === l.id ? 'var(--color-ink)' : 'var(--color-ink)',
              borderBottom: current === l.id ? '2px solid var(--color-ash)' : '2px solid transparent',
              paddingBottom: 2,
            }}
          >
            {l.label}{l.meta ? <span style={{ color: 'var(--color-mute)', marginLeft: 4 }}>{l.meta}</span> : null}
          </span>
        ))}
        <Button onClick={() => onNavigate && onNavigate('download')} style={{ marginLeft: 8 }}>↓ Download</Button>
      </div>
    </nav>
  );
}

Object.assign(window, { PrimaryNav });
