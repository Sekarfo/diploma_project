// 5-up footer with copyright + utility cluster.
function Footer() {
  const cells = ['GitHub [150K]', 'Docs', 'Changelog', 'Discord', 'X'];
  return (
    <footer style={{
      borderTop: '1px solid var(--color-hairline)',
      padding: '32px 24px',
      fontFamily: 'var(--font-mono)',
      fontSize: 14,
      color: 'var(--color-body)',
    }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', textAlign: 'center', lineHeight: 2 }}>
        {cells.map((c, i) => (
          <div key={i} style={{ borderRight: i < 4 ? '1px solid var(--color-hairline)' : 'none' }}>{c}</div>
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 20, color: 'var(--color-mute)' }}>
        <span>©2026 Anomaly</span>
        <span>Brand · Privacy · Terms · English ▼</span>
      </div>
    </footer>
  );
}
Object.assign(window, { Footer });
