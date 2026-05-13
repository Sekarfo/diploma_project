// Three page bodies — home, /zen, /enterprise — plus a tiny page-switcher.

function HomePage({ navigate }) {
  const features = [
    { glyph: '[+]', label: 'LSP enabled', desc: 'Automatically loads the right LSPs for your project.' },
    { glyph: '[+]', label: 'Themable', desc: 'Bring your terminal palette — opencode adopts it.' },
    { glyph: '[+]', label: 'Native TUI', desc: 'No GUI. No Electron. Runs where you already work.' },
    { glyph: '[-]', label: 'No telemetry', desc: 'Local by default. Your code never leaves the box.' },
    { glyph: '[x]', label: 'Open source', desc: 'MIT-licensed. Read the source. Send a PR.' },
  ];
  const faq = [
    { q: 'How is opencode different from other agents?', a: 'opencode is terminal-first and open source. It runs where you already work, reads the LSP your editor is using, and never sends your code off the box.' },
    { q: 'What models does it support?', a: 'Bring your own key (Anthropic, OpenAI, Mistral, local llama.cpp) or route through opencode Zen for a managed experience.' },
    { q: 'Does it work offline?', a: 'With a local model, yes — opencode is a thin CLI on top of whichever backend you wire up.' },
    { q: 'Is it free?', a: 'opencode itself is free and open source. Zen is the optional managed plan.' },
  ];
  return (
    <main>
      <section style={{ padding: '48px 24px 0' }}>
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 24 }}>
            <span className="badge-news">News</span>
            <span style={{ fontSize: 15, color: 'var(--color-body)' }}>opencode v2.4 ships with Go support → <a href="#" style={{ color: 'var(--color-ink)' }}>changelog</a></span>
          </div>
          <h1 style={{ fontSize: 38, fontWeight: 700, lineHeight: 1.5, margin: 0, color: 'var(--color-ink)' }}>
            The open source AI coding agent
          </h1>
          <p style={{ fontSize: 16, lineHeight: 1.5, color: 'var(--color-body)', maxWidth: 680, marginTop: 16 }}>
            opencode is a terminal-native coding agent. No GUI, no telemetry, no vendor lock. Bring your own model or
            route through <span style={{ color: 'var(--color-ink)', textDecoration: 'underline', cursor: 'pointer' }} onClick={() => navigate('zen')}>opencode Zen</span> for a managed experience.
          </p>
          <div style={{ marginTop: 28 }}>
            <InstallBlock />
          </div>
        </div>
      </section>

      <section style={{ marginTop: 96 }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', padding: '0 24px' }}>
          <HeroTUI />
        </div>
      </section>

      <section style={{ marginTop: 96, padding: '0 24px' }}>
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
          <SectionLabel>What is opencode?</SectionLabel>
          <FeatureList items={features} />
        </div>
      </section>

      <section style={{ marginTop: 96, padding: '0 24px' }}>
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
          <SectionLabel>open source AI coding agent</SectionLabel>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 0 }}>
            <ChartTile kind="dots" caption="Fig 1. 150K GitHub Stars" />
            <ChartTile kind="line" caption="Fig 2. 850 Contributors" />
            <ChartTile kind="sparse" caption="Fig 3. 6.5M Monthly Devs" />
          </div>
        </div>
      </section>

      <section style={{ marginTop: 96, padding: '0 24px' }}>
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
          <SectionLabel>FAQ</SectionLabel>
          <FAQList items={faq} />
        </div>
      </section>

      <div style={{ marginTop: 96 }}>
        <Footer />
      </div>
    </main>
  );
}

function ZenPage({ navigate }) {
  const features = [
    { glyph: '[+]', label: 'Managed routing', desc: 'Zen picks the right model for the task — Opus for reasoning, Haiku for edits.' },
    { glyph: '[+]', label: 'Usage-based pricing', desc: 'Pay per token. No seat fees. No retainers.' },
    { glyph: '[+]', label: 'SOC 2 Type II', desc: 'Audited controls. Data residency in US or EU.' },
    { glyph: '[x]', label: 'Same opencode CLI', desc: 'Drop in a Zen key — every command works identically.' },
  ];
  const quotes = [
    { name: 'Ada Reyes', role: 'Staff Eng @ Anomaly', quote: "It's the first agent that respects my terminal. No GUI. No telemetry. It just edits.", hue: '#9a8a82' },
    { name: 'Ben Kawamoto', role: 'CTO @ Plate', quote: "We replaced three editor plugins with one CLI. Cost dropped, latency dropped.", hue: '#7a8a82' },
    { name: 'Priya Shah', role: 'Founding Eng @ Lattice', quote: "Zen handles the model-routing decision for us. We just write code.", hue: '#8a7a82' },
  ];
  return (
    <main>
      <section style={{ padding: '48px 24px 0' }}>
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
          <h1 style={{ fontSize: 38, fontWeight: 700, lineHeight: 1.5, margin: 0 }}>opencode Zen</h1>
          <p style={{ fontSize: 16, lineHeight: 1.5, color: 'var(--color-body)', maxWidth: 680, marginTop: 16 }}>
            The managed plan for opencode. Bring your team, not your API keys.
          </p>
          <div style={{ marginTop: 28, display: 'flex', gap: 12 }}>
            <Button>Get started with Zen</Button>
            <Button variant="secondary">Read docs →</Button>
          </div>
        </div>
      </section>

      <section style={{ marginTop: 96, padding: '0 24px' }}>
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
          <SectionLabel>What you get</SectionLabel>
          <FeatureList items={features} />
        </div>
      </section>

      <section style={{ marginTop: 96, padding: '0 24px' }}>
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
          <SectionLabel>From the field</SectionLabel>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {quotes.map((q, i) => <TestimonialRow key={i} {...q} />)}
          </div>
        </div>
      </section>

      <div style={{ marginTop: 96 }}>
        <Footer />
      </div>
    </main>
  );
}

function EnterprisePage() {
  const [form, setForm] = useState({ name: '', role: '', company: '', email: '', phone: '', problem: '' });
  const [sent, setSent] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const features = [
    { glyph: '[+]', label: 'Self-hosted', desc: 'Run opencode entirely inside your VPC. Bring your own inference.' },
    { glyph: '[+]', label: 'SSO & SCIM', desc: 'Okta, Entra, Workspace. Provision and deprovision via SCIM 2.0.' },
    { glyph: '[+]', label: 'Audit log', desc: 'Every prompt, edit and shell command, written to your SIEM.' },
    { glyph: '[x]', label: 'Built for privacy first', desc: "Code never leaves your network. Period." },
  ];
  return (
    <main>
      <section style={{ padding: '48px 24px 0' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'grid', gridTemplateColumns: 'minmax(280px, 360px) 1fr', gap: 64, alignItems: 'start' }}>
          <div>
            <h1 style={{ fontSize: 32, fontWeight: 700, lineHeight: 1.5, margin: 0 }}>opencode for the enterprise</h1>
            <p style={{ fontSize: 16, lineHeight: 1.5, color: 'var(--color-body)', marginTop: 16 }}>
              Run opencode inside your own perimeter. Self-hosted, audit-logged, SSO-protected.
            </p>
            <div style={{ marginTop: 28 }}>
              <FeatureList items={features} />
            </div>
          </div>
          <div style={{ background: 'var(--color-canvas)', padding: 24, border: '1px solid var(--color-hairline)', borderRadius: 0, maxWidth: 480, width: '100%', justifySelf: 'end' }}>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>Talk to us</div>
            <div style={{ fontSize: 14, color: 'var(--color-mute)', marginBottom: 20, lineHeight: 1.5 }}>We'll respond within one business day.</div>
            {sent ? (
              <div style={{ padding: '24px 0', fontSize: 16, color: 'var(--color-ink)' }}>
                <b>[x]</b> Thanks — we'll be in touch at <b>{form.email || 'you@company.com'}</b>.
              </div>
            ) : (
              <form onSubmit={(e) => { e.preventDefault(); setSent(true); }} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <TextField label="Full name" placeholder="Ada Reyes" value={form.name} onChange={set('name')} />
                <TextField label="Role" placeholder="VP Engineering" value={form.role} onChange={set('role')} />
                <TextField label="Company" placeholder="Anomaly" value={form.company} onChange={set('company')} />
                <TextField label="Company email" type="email" placeholder="ada@anomaly.dev" value={form.email} onChange={set('email')} />
                <TextField label="Phone number" placeholder="+1 415 555 0100" value={form.phone} onChange={set('phone')} />
                <TextArea label="What problem are you trying to solve?" placeholder="We want to deploy a coding agent on-prem…" value={form.problem} onChange={set('problem')} />
                <Button>Send</Button>
              </form>
            )}
          </div>
        </div>
      </section>

      <div style={{ marginTop: 96 }}>
        <Footer />
      </div>
    </main>
  );
}

Object.assign(window, { HomePage, ZenPage, EnterprisePage });
