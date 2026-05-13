// FAQ list with bracket toggle markers.
function FAQList({ items }) {
  const [open, setOpen] = useState(null);
  return (
    <div style={{ fontFamily: 'var(--font-mono)' }}>
      {items.map((it, i) => {
        const isOpen = open === i;
        return (
          <div key={i} style={{ borderBottom: '1px solid var(--color-hairline)' }}>
            <button
              onClick={() => setOpen(isOpen ? null : i)}
              style={{
                width: '100%',
                background: 'transparent',
                border: 0,
                padding: '12px 0',
                textAlign: 'left',
                fontFamily: 'var(--font-mono)',
                fontSize: 16,
                color: 'var(--color-ink)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'baseline',
                gap: 14,
              }}
            >
              <b style={{ width: 14 }}>{isOpen ? '−' : '+'}</b>
              <span>{it.q}</span>
            </button>
            {isOpen ? (
              <div style={{ paddingBottom: 14, paddingLeft: 28, color: 'var(--color-body)', fontSize: 15, lineHeight: 1.6 }}>
                {it.a}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
Object.assign(window, { FAQList });
