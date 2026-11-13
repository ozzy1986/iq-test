import { useEffect, useState } from 'react'
import { api, clock, date, price, saved, type Result, type SessionState } from '../api'
import type { Nav } from '../App'
import { OptionBody } from '../Figure'
import { Status, useTitle } from '../ui'

type Props = { state: SessionState; onState: (s: SessionState) => void; nav: Nav }

export default function ResultScreen({ state, onState, nav }: Props) {
  const [result, setResult] = useState<Result | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.result(state.id).then(setResult).catch((e: Error) => setError(e.message))
  }, [state.id])

  useTitle(result ? `Ваш IQ — ${result.iq}` : 'Ваш результат')
  if (error)
    return <Status title="Не удалось открыть отчёт" text={error}
      action={{ label: 'Повторить', onClick: () => location.reload() }} />
  if (!result) return <Status />

  return (
    <main className="screen result">
      <section className="card score">
        <p className="chip chip-accent">Ваш результат</p>
        <h1 className="iq" aria-label={`Ваш IQ — ${result.iq}`}>{result.iq}</h1>
        <p className="level">{result.level.title}</p>
        <Bell iq={result.iq} />
        <p className="percentile">Выше, чем у <b>{result.percentile}%</b> людей</p>
        <p className="muted">{result.level.text}</p>
        <ul className="facts small">
          <li><b>{result.correct}/{result.total}</b><span>верных ответов</span></li>
          <li><b>{clock(result.duration_sec)}</b><span>время</span></li>
        </ul>
      </section>

      <section>
        <h2>Профиль по навыкам</h2>
        <div className="card">
          {result.breakdown.map((b) => (
            <div className="bar-row" key={b.key}>
              <span>{b.title}<em>{b.correct} из {b.total}</em></span>
              <div className="bar"><div style={{ width: `${Math.max(4, (b.correct / b.total) * 100)}%` }} /></div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2>Главные выводы</h2>
        <ul className="insights">
          {result.insights.map((text) => <li key={text}>{text}</li>)}
        </ul>
      </section>

      <section>
        <h2>Разбор вопросов</h2>
        <div className="review">
          {result.review.map((r) => (
            <details key={r.n}>
              <summary>
                <i className={r.is_correct ? 'mark ok' : 'mark bad'}>{r.is_correct ? '✓' : '✕'}</i>
                <span><b>Вопрос {r.n}</b><em>{r.category}</em></span>
              </summary>
              <p>{r.prompt}</p>
              {r.series && <p className="series sm">{r.series}</p>}
              <div className="answers">
                {!r.is_correct && r.your && <div className="answer bad"><span>Ваш ответ</span><OptionBody option={r.your} /></div>}
                <div className="answer ok"><span>Верный ответ</span><OptionBody option={r.right} /></div>
              </div>
              <p className="muted">{r.explain}</p>
            </details>
          ))}
        </div>
      </section>

      <SubscriptionCard state={state} onState={onState} />

      <button className="btn btn-ghost btn-lg" onClick={() => { saved.set(null); nav('/') }}>Пройти тест заново</button>
      <p className="fineprint">
        Результат — ориентировочная оценка по короткому тесту. Он не заменяет профессиональную
        психометрическую диагностику.
      </p>
    </main>
  )
}

function SubscriptionCard({ state, onState }: Pick<Props, 'state' | 'onState'>) {
  const sub = state.subscription!
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const cancel = async () => {
    setBusy(true)
    setError('')
    try {
      onState(await api.cancel(state.id))
      setConfirming(false)
    } catch (e) {
      setError((e as Error).message)
    }
    setBusy(false)
  }

  return (
    <section>
      <h2>Подписка</h2>
      <div className="card">
        {sub.status === 'active' ? (
          <>
            <div className="price-row"><span>Статус</span><b className="ok-text">Активна</b></div>
            <div className="price-row"><span>Следующее списание</span><span>{date(sub.current_period_end)}, {price(state.plan.amount)}</span></div>
            {confirming ? (
              <div className="confirm">
                <p>Отменить подписку? Отчёт останется доступен до {date(sub.current_period_end)}.</p>
                <div className="confirm-actions">
                  <button className="btn btn-danger" onClick={cancel} disabled={busy}>{busy ? 'Отменяем…' : 'Да, отменить'}</button>
                  <button className="btn btn-ghost" onClick={() => setConfirming(false)} disabled={busy}>Оставить</button>
                </div>
              </div>
            ) : (
              <button className="link-btn" onClick={() => setConfirming(true)}>Отменить подписку</button>
            )}
            {error && <p className="alert-error" role="alert">{error}</p>}
          </>
        ) : (
          <>
            <div className="price-row"><span>Статус</span><b>Отменена</b></div>
            <p className="muted">Списаний больше не будет. Отчёт доступен до {date(sub.current_period_end)}.</p>
          </>
        )}
        {state.email && <p className="fineprint">Оформлена на {state.email}. Оплата — демо, деньги не списывались.</p>}
      </div>
    </section>
  )
}

/** Колокол нормального распределения N(100, 15) с отметкой результата. */
function Bell({ iq }: { iq: number }) {
  const W = 320, H = 96, LO = 55, HI = 145
  const x = (v: number) => ((v - LO) / (HI - LO)) * W
  const y = (v: number) => H - 6 - Math.exp(-((v - 100) ** 2) / (2 * 15 ** 2)) * (H - 16)
  const pts = (to: number) => {
    const out: string[] = []
    for (let v = LO; v <= to; v += 1) out.push(`${x(v).toFixed(1)},${y(v).toFixed(1)}`)
    return out.join(' ')
  }
  const at = Math.min(HI - 2, Math.max(LO + 2, iq))
  return (
    <svg className="bell" viewBox={`0 0 ${W} ${H + 16}`} role="img" aria-label={`Положение результата ${iq} на шкале IQ`}>
      <polygon points={`${x(LO)},${H - 6} ${pts(at)} ${x(at)},${H - 6}`} className="bell-fill" />
      <polyline points={pts(HI)} className="bell-line" />
      <line x1={x(at)} x2={x(at)} y1={y(at) - 6} y2={H - 6} className="bell-mark" />
      <circle cx={x(at)} cy={y(at)} r="5" className="bell-dot" />
      {[70, 85, 100, 115, 130].map((v) => (
        <text key={v} x={x(v)} y={H + 10} textAnchor="middle" className="bell-tick">{v}</text>
      ))}
    </svg>
  )
}
