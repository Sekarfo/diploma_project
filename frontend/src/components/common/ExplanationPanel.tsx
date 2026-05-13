import type { ExplanationFactor } from "../../types";

interface Props {
  title?: string;
  summary: string;
  factors: ExplanationFactor[];
}

function asciiBar(value: number): { on: string; off: string } {
  const filled = Math.round(value * 10);
  return {
    on: "█".repeat(filled),
    off: "─".repeat(10 - filled),
  };
}

export function ExplanationPanel({ title = "shap-based factors", summary, factors }: Props): JSX.Element {
  return (
    <div className="shap">
      <div className="shap-name">{title}</div>
      <div className="mono-mute">{summary}</div>
      <hr />
      {factors.map((factor) => {
        const { on, off } = asciiBar(factor.impact);
        return (
          <div key={factor.factor}>
            <div className="shap-row">
              <span>{factor.factor}</span>
              <span className="num">{Math.round(factor.impact * 100)}%</span>
            </div>
            <div className="shap-bar">
              <span style={{ color: "var(--ink)" }}>{on}</span>
              {off && <span style={{ color: "var(--ash)" }}>{off}</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
