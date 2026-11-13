import type { Fig, Option } from './api'

const LAYOUT: Record<number, { r: number; at: [number, number][] }> = {
  1: { r: 15, at: [[30, 30]] },
  2: { r: 10, at: [[17, 30], [43, 30]] },
  3: { r: 7.5, at: [[11, 30], [30, 30], [49, 30]] },
}

function Shape({ fig, cx, cy, r }: { fig: Fig; cx: number; cy: number; r: number }) {
  const paint = {
    fill: fig.fill === 'none' ? 'none' : 'currentColor',
    fillOpacity: fig.fill === 'light' ? 0.28 : 1,
    stroke: 'currentColor',
    strokeWidth: 2.5,
    strokeLinejoin: 'round' as const,
  }
  if (fig.shape === 'circle') return <circle cx={cx} cy={cy} r={r} {...paint} />
  if (fig.shape === 'square') return <rect x={cx - r} y={cy - r} width={2 * r} height={2 * r} rx={1.5} {...paint} />
  if (fig.shape === 'triangle')
    return <polygon points={`${cx},${cy - r} ${cx + r},${cy + r * 0.85} ${cx - r},${cy + r * 0.85}`} {...paint} />
  return (
    <g transform={`rotate(${fig.rot} 30 30)`} fill="none" stroke="currentColor" strokeWidth={4} strokeLinecap="round" strokeLinejoin="round">
      <path d="M30 47V14M19 25l11-12 11 12" />
    </g>
  )
}

export function FigCell({ fig }: { fig: Fig | null }) {
  if (!fig)
    return (
      <svg viewBox="0 0 60 60" className="fig fig-missing" aria-label="пропущенная фигура">
        <text x="30" y="40" textAnchor="middle" fontSize="28" fontWeight="700" fill="currentColor">?</text>
      </svg>
    )
  const { r, at } = LAYOUT[fig.count] ?? LAYOUT[1]
  return (
    <svg viewBox="0 0 60 60" className="fig" aria-hidden="true">
      {at.map(([cx, cy], i) => (
        <Shape key={i} fig={fig} cx={cx} cy={cy} r={r} />
      ))}
    </svg>
  )
}

export function OptionBody({ option }: { option: Option }) {
  return option.fig ? <FigCell fig={option.fig} /> : <span>{option.text}</span>
}
