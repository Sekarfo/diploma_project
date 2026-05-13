interface Props {
  score: number;
}

function scoreBar(score: number): { on: number; off: number } {
  const filled = Math.round((score / 100) * 10);
  return { on: filled, off: 10 - filled };
}

export function ScoreBadge({ score }: Props): JSX.Element {
  const { on, off } = scoreBar(score);
  const cls = score >= 85 ? "badge-success" : score >= 70 ? "" : "";
  return (
    <div className="score">
      <span className="score-bar">
        <span className="on">{"█".repeat(on)}</span>
        {off > 0 && <span className="off">{"─".repeat(off)}</span>}
      </span>
      <span className={`badge ${cls}`}>{score.toFixed(1)}%</span>
    </div>
  );
}
