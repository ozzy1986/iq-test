import type { Fig, Option, Question } from './api'

const LAYOUT: Record<number, { r: number; at: [number, number][] }> = {
  1: { r: 15, at: [[30, 30]] },
  2: { r: 10, at: [[17, 30], [43, 30]] },
  3: { r: 7.5, at: [[11, 30], [30, 30], [49, 30]] },
  4: { r: 9, at: [[18, 18], [42, 18], [18, 42], [42, 42]] },
}

function Shape({ fig, cx, cy, r }: { fig: Fig; cx: number; cy: number; r: number }) {
  const paint = {
    fill: fig.fill === 'none' ? 'none' : 'currentColor',
    fillOpacity: fig.fill === 'light' ? 0.28 : 1,
    stroke: 'currentColor',
    strokeWidth: 2.5,
    strokeLinejoin: 'round' as const,
  }
  const t = r * 0.36 // половина толщины перекладины креста
  switch (fig.shape) {
    case 'circle':
      return <circle cx={cx} cy={cy} r={r} {...paint} />
    case 'square':
      return <rect x={cx - r} y={cy - r} width={2 * r} height={2 * r} rx={1.5} {...paint} />
    case 'triangle':
      return <polygon points={`${cx},${cy - r} ${cx + r},${cy + r * 0.85} ${cx - r},${cy + r * 0.85}`} {...paint} />
    case 'diamond':
      return <polygon points={`${cx},${cy - r * 1.1} ${cx + r * 0.85},${cy} ${cx},${cy + r * 1.1} ${cx - r * 0.85},${cy}`} {...paint} />
    case 'cross':
      return <polygon {...paint} points={[
        [-t, -r], [t, -r], [t, -t], [r, -t], [r, t], [t, t], [t, r], [-t, r], [-t, t], [-r, t], [-r, -t], [-t, -t],
      ].map(([x, y]) => `${cx + x},${cy + y}`).join(' ')} />
    default:
      return (
        <g transform={`rotate(${fig.rot} 30 30)`} fill="none" stroke="currentColor" strokeWidth={4} strokeLinecap="round" strokeLinejoin="round">
          <path d="M30 47V14M19 25l11-12 11 12" />
        </g>
      )
  }
}

export function FigCell({ fig }: { fig: Fig | null }) {
  if (!fig)
    return (
      <svg viewBox="0 0 60 60" className="fig fig-missing" aria-label="пропущенная фигура">
        <text x="30" y="40" textAnchor="middle" fontSize="28" fontWeight="600" fill="currentColor">?</text>
      </svg>
    )
  const { r, at } = LAYOUT[fig.count] ?? LAYOUT[1]
  return (
    <svg viewBox="0 0 60 60" className="fig" aria-hidden="true">
      {at.map(([cx, cy], i) => (
        <Shape key={i} fig={fig} cx={cx} cy={cy} r={r * (fig.size ?? 1)} />
      ))}
    </svg>
  )
}

export function OptionBody({ option }: { option: Option }) {
  return option.fig ? <FigCell fig={option.fig} /> : <span>{option.text}</span>
}

/** Матрица или ряд фигур с пропуском — в вопросе и в разборе ответов. */
export function Matrix({ figure, small }: { figure: NonNullable<Question['figure']>; small?: boolean }) {
  return (
    <div className={small ? 'matrix matrix-sm' : 'matrix'} role="img" aria-label="Фигуры с пропуском"
      style={{ gridTemplateColumns: `repeat(${figure.cols}, 1fr)`, maxWidth: figure.cols * (small ? 60 : 88) }}>
      {figure.cells.map((cell, i) => <FigCell key={i} fig={cell} />)}
    </div>
  )
}
