import './MetricsDashboard.css'

export default function MetricsDashboard({ metrics, total }) {
  const items = [
    { key: 'critical', label: 'Críticos', color: '#dc2626', bg: '#fee2e2', count: metrics.critical ?? 0 },
    { key: 'moderate', label: 'Moderados', color: '#f59e0b', bg: '#fef3c7', count: metrics.moderate ?? 0 },
    { key: 'mild', label: 'Leves', color: '#10b981', bg: '#dcfce7', count: metrics.mild ?? 0 },
  ]

  return (
    <div className="metrics-dashboard">
      {items.map(({ key, label, color, bg, count }) => (
        <div key={key} className="metric-card" style={{ borderTopColor: color, backgroundColor: bg }}>
          <span className="metric-count" style={{ color }}>{count}</span>
          <span className="metric-label">{label}</span>
          {total > 0 && (
            <span className="metric-pct" style={{ color }}>
              {Math.round((count / total) * 100)}%
            </span>
          )}
        </div>
      ))}
    </div>
  )
}
