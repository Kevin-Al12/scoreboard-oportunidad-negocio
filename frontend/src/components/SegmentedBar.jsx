export default function SegmentedBar({ segments }) {
  // segments: [{ pct, color }]
  return (
    <div className="segmented-bar">
      {segments.map((s, i) => (
        <div key={i} style={{ width: `${s.pct}%`, background: s.color }} />
      ))}
    </div>
  );
}
