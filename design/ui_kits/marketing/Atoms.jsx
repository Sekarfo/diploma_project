// Shared atoms used across the marketing UI kit.
// Loaded as a single Babel script; components attach to window.

const { useState } = React;

function Button({ variant = 'primary', children, onClick, style }) {
  const base = {
    fontFamily: 'var(--font-mono)',
    fontSize: 16,
    fontWeight: 500,
    lineHeight: 2,
    padding: '4px 20px',
    borderRadius: 4,
    border: '1px solid transparent',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    textDecoration: 'none',
  };
  const v = variant === 'primary'
    ? { background: 'var(--color-primary)', color: 'var(--color-on-primary)', borderColor: 'var(--color-primary)' }
    : variant === 'secondary'
      ? { background: 'var(--color-canvas)', color: 'var(--color-ink)', borderColor: 'var(--color-hairline-strong)' }
      : { background: 'var(--color-surface-card)', color: 'var(--color-ash)', cursor: 'not-allowed' };
  return <button style={{ ...base, ...v, ...style }} onClick={onClick}>{children}</button>;
}

function Hairline({ strong, style }) {
  return <hr style={{
    border: 0,
    borderTop: `1px solid ${strong ? 'var(--color-hairline-strong)' : 'var(--color-hairline)'}`,
    margin: 0,
    ...style,
  }} />;
}

function SectionLabel({ children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-ink)', marginBottom: 12 }}>{children}</div>
      <Hairline />
    </div>
  );
}

function BracketBullet({ glyph = '[+]', label, desc }) {
  return (
    <div style={{ padding: '8px 0', display: 'grid', gridTemplateColumns: '180px 1fr', gap: 16, fontFamily: 'var(--font-mono)', fontSize: 16, lineHeight: 1.5 }}>
      <div style={{ color: 'var(--color-ink)', fontWeight: 700 }}>{glyph} {label}</div>
      <div style={{ color: 'var(--color-body)' }}>{desc}</div>
    </div>
  );
}

function TextField({ label, placeholder, type = 'text', value, onChange, focused }) {
  const [isFocused, setFocused] = useState(false);
  const active = focused || isFocused;
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontFamily: 'var(--font-mono)' }}>
      <span style={{ fontSize: 14, color: 'var(--color-mute)' }}>{label}</span>
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          background: active ? 'var(--color-canvas)' : 'var(--color-surface-soft)',
          color: 'var(--color-ink)',
          border: `1px solid ${active ? 'var(--color-ink)' : 'var(--color-hairline)'}`,
          borderRadius: 4,
          padding: '8px 12px',
          fontFamily: 'var(--font-mono)',
          fontSize: 16,
          lineHeight: 1.5,
          height: 40,
          width: '100%',
          boxSizing: 'border-box',
          outline: 'none',
        }}
      />
    </label>
  );
}

function TextArea({ label, placeholder, value, onChange }) {
  const [isFocused, setFocused] = useState(false);
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontFamily: 'var(--font-mono)' }}>
      <span style={{ fontSize: 14, color: 'var(--color-mute)' }}>{label}</span>
      <textarea
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        rows={4}
        style={{
          background: isFocused ? 'var(--color-canvas)' : 'var(--color-surface-soft)',
          color: 'var(--color-ink)',
          border: `1px solid ${isFocused ? 'var(--color-ink)' : 'var(--color-hairline)'}`,
          borderRadius: 4,
          padding: 12,
          fontFamily: 'var(--font-mono)',
          fontSize: 16,
          lineHeight: 1.5,
          width: '100%',
          boxSizing: 'border-box',
          outline: 'none',
          resize: 'vertical',
        }}
      />
    </label>
  );
}

function Wordmark({ size = 8, color = 'var(--color-ink)' }) {
  const art =
` ████  █████  █████  █   █   ████   ████   █████   █████
█    █ █    █ █      ██  █  █      █    █  █    █  █    
█    █ █████  ████   █ █ █  █      █    █  █    █  ████ 
█    █ █      █      █  ██  █      █    █  █    █  █    
 ████  █      █████  █   █   ████   ████   █████   █████`;
  return (
    <pre style={{
      margin: 0,
      fontFamily: 'var(--font-mono)',
      fontWeight: 700,
      fontSize: size,
      lineHeight: 1,
      color,
      whiteSpace: 'pre',
    }}>{art}</pre>
  );
}

Object.assign(window, { Button, Hairline, SectionLabel, BracketBullet, TextField, TextArea, Wordmark });
