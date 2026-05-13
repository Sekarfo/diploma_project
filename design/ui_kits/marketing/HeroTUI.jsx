// Hero TUI mockup — the single dark surface in the whole site.
function HeroTUI() {
  return (
    <div style={{
      background: 'var(--color-surface-dark)',
      padding: '64px 32px',
      fontFamily: 'var(--font-mono)',
      color: 'var(--color-on-dark)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 28,
    }}>
      <Wordmark size={14} color="var(--color-on-dark)" />
      <div style={{
        background: 'var(--color-surface-dark-elevated)',
        padding: '10px 14px',
        borderRadius: 4,
        fontSize: 15,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        width: 'min(720px, 100%)',
        boxSizing: 'border-box',
        color: 'var(--color-on-dark)',
      }}>
        <span style={{ color: 'var(--color-ash)' }}>|</span>
        <span style={{ fontWeight: 500 }}>Build</span>
        <span style={{ color: 'var(--color-ash)' }}>·</span>
        <span style={{ color: 'var(--color-ash)' }}>[Claude Opus 4.5]</span>
        <span style={{ marginLeft: 'auto', color: 'var(--color-ash)' }}>opencode Zen</span>
      </div>
      <div style={{ display: 'flex', gap: 24, fontSize: 13, color: 'var(--color-ash)' }}>
        <span><b style={{ color: 'var(--color-on-dark)', fontWeight: 500 }}>tab</b> switch agent</span>
        <span><b style={{ color: 'var(--color-on-dark)', fontWeight: 500 }}>ctrl-p</b> commands</span>
      </div>
    </div>
  );
}
Object.assign(window, { HeroTUI });
