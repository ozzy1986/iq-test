import { useEffect, useState } from 'react'
import { api, clock, date, price, type Result, type SessionState } from '../api'
import { Matrix, OptionBody } from '../Figure'
import { Status, useTitle } from '../ui'

type Props = { state: SessionState; onState: (s: SessionState) => void; retake: () => void; retaking: boolean }

export default function ResultScreen({ state, onState, retake, retaking }: Props) {
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
        <h1 className="iq" aria-label={`Ваш IQ — ${result.iq}, погрешность ${result.margin}`}>
          {result.iq}<small>±{result.margin}</small>
        </h1>
        <p className="level">{result.level.title}</p>
        <Bell iq={result.iq} />
        <p className="percentile">Выше, чем у <b>{result.percentile}%</b> людей</p>
        <p className="muted">{result.level.text}</p>
        <ul className="facts small">
          <li><b>{result.correct}/{result.total}</b><span>верных ответов</span></li>
          <li><b>{clock(result.duration_sec)}</b><span>время</span></li>
        </ul>
        <details className="method">
          <summary><span><b>Как посчитан результат</b></span></summary>
          <p>
            Шкала стандартная для IQ-тестов: среднее значение 100, стандартное отклонение 15. Около 68% людей
            получают от 85 до 115.
          </p>
          <p>
            Оценка учитывает не только число верных ответов, но и то, какие именно задания решены: у каждого
            своя сложность и своя вероятность случайного угадывания (модель IRT, которую используют в
            современных тестах). Погрешность ±{result.margin} показывает разброс оценки для теста такой длины.
          </p>
          <p>
            Сложность заданий задана экспертно и уточняется по ответам участников по мере накопления
            данных. Теста на представительной выборке не проводилось, поэтому результат ориентировочный.
            Точный IQ определяет только очный тест у психолога.
          </p>
        </details>
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
        <h2>Динамика</h2>
        <div className="card">
          <History items={result.history} />
          <p className="muted">
            {result.history.length > 1
              ? 'Каждая попытка — новый набор заданий, поэтому рост результата отражает навык, а не память.'
              : 'Пройдите тест ещё раз через несколько дней: задания будут новыми, а результат появится на графике.'}
          </p>
          <button className="btn btn-primary" onClick={retake} disabled={retaking}>
            {retaking ? 'Готовим тест…' : 'Пройти ещё раз с новыми заданиями'}
          </button>
        </div>
      </section>

      <section>
        <h2>Разбор вопросов</h2>
        <div className="review">
          {result.review.map((r) => (
            <details key={r.n}>
              <summary>
                <i className={r.is_correct ? 'mark ok' : 'mark bad'}>{r.is_correct ? '✓' : '✕'}</i>
                <span><b>Вопрос {r.n}</b><em>{r.category} · сложность {r.difficulty} из 5</em></span>
              </summary>
              <p>{r.prompt}</p>
              {r.series && <p className="series sm">{r.series}</p>}
              {r.figure && <Matrix figure={r.figure} small />}
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

      <p className="fineprint">
        Результат — ориентировочная оценка по короткому тесту. Он не заменяет профессиональную
        психометрическую диагностику.
      </p>
    </main>
  )
}

function History({ items }: { items: Result['history'] }) {
  const max = Math.max(...items.map((i) => i.iq), 130)
  return (
    <ol className="history" aria-label="История прохождений">
      {items.slice(-8).map((item) => (
        <li key={item.id} className={item.current ? 'current' : ''}>
          <b>{item.iq}</b>
          <div style={{ height: `${Math.max(12, ((item.iq - 50) / (max - 50)) * 100)}%` }} />
          <span>{new Date(item.finished_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}</span>
        </li>
      ))}
    </ol>
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
            <div className="price-row"><span>Статус</span><b className="ok-text">{sub.trial ? 'Пробный период' : 'Активна'}</b></div>
            <div className="price-row"><span>Следующее списание</span><span>{date(sub.current_period_end)}, {price(state.plan.amount)}</span></div>
            {confirming ? (
              <div className="confirm">
                <p>Отменить подписку? {sub.trial && `${price(state.plan.amount)} не спишутся. `}Отчёты и новые прохождения останутся доступны до {date(sub.current_period_end)}.</p>
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
            <p className="muted">Списаний больше не будет. Отчёты и новые прохождения доступны до {date(sub.current_period_end)}.</p>
          </>
        )}
        <p className="fineprint">Оплата — демо, деньги не списывались.</p>
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
