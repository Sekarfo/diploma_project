// /zen testimonial row.
function TestimonialRow({ name, role, quote, hue = '#9a8a82' }) {
  return (
    <div style={{
      background: 'var(--color-surface-soft)',
      padding: '16px 20px',
      borderRadius: 4,
      display: 'flex',
      gap: 14,
      fontFamily: 'var(--font-mono)',
    }}>
      <div style={{ width: 32, height: 32, borderRadius: 9999, background: hue, flexShrink: 0 }} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ fontSize: 16, fontWeight: 500, color: 'var(--color-ink)' }}>{name} · {role}</div>
        <div style={{ fontSize: 16, color: 'var(--color-body)', lineHeight: 1.5 }}>"{quote}"</div>
      </div>
    </div>
  );
}
Object.assign(window, { TestimonialRow });
