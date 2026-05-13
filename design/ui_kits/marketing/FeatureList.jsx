// [+] / [-] feature row list.
function FeatureList({ items }) {
  return (
    <div>
      {items.map((it, i) => (
        <BracketBullet key={i} glyph={it.glyph || '[+]'} label={it.label} desc={it.desc} />
      ))}
    </div>
  );
}
Object.assign(window, { FeatureList });
