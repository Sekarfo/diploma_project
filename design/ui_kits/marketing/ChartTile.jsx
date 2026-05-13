// Sparse-line "chart" tile for the stat block.
function ChartTile({ caption, kind = 'dots' }) {
  // Two abstract SVG plots — dotted and sparse-line, no specific data.
  const dots = (
    <svg viewBox="0 0 200 80" width="100%" height="80" preserveAspectRatio="none">
      {Array.from({ length: 40 }).map((_, i) => (
        <circle key={i} cx={5 + i * 5} cy={70 - Math.abs(Math.sin(i * 0.45) * 50) - (i * 0.6)} r="1.4" fill="var(--color-body)" />
      ))}
    </svg>
  );
  const line = (
    <svg viewBox="0 0 200 80" width="100%" height="80" preserveAspectRatio="none">
      <polyline
        points={Array.from({ length: 40 }).map((_, i) => `${5 + i * 5},${70 - Math.abs(Math.sin(i * 0.35 + 1.2) * 40) - (i * 0.8)}`).join(' ')}
        fill="none"
        stroke="var(--color-body)"
        strokeWidth="1"
        strokeDasharray={kind === 'dashed' ? '2 3' : ''}
      />
    </svg>
  );
  const sparse = (
    <svg viewBox="0 0 200 80" width="100%" height="80" preserveAspectRatio="none">
      {[10, 50, 90, 130, 170].map((x, i) => (
        <g key={i}>
          <line x1={x} y1="78" x2={x} y2={78 - (20 + i * 10)} stroke="var(--color-body)" strokeWidth="1" />
          <circle cx={x} cy={78 - (20 + i * 10)} r="1.6" fill="var(--color-body)" />
        </g>
      ))}
    </svg>
  );
  return (
    <div style={{ padding: 16, fontFamily: 'var(--font-mono)' }}>
      {kind === 'dots' ? dots : kind === 'sparse' ? sparse : line}
      <div style={{ fontSize: 14, color: 'var(--color-mute)', marginTop: 8, lineHeight: 2 }}>{caption}</div>
    </div>
  );
}
Object.assign(window, { ChartTile });
