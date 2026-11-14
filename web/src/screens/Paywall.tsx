import { useEffect, useState, type FormEvent } from 'react'
import { api, clock, isEmail, price, type SessionState } from '../api'
import type { Nav } from '../App'
import { useTitle } from '../ui'

type Props = { state: SessionState; onState: (s: SessionState) => void; nav: Nav }

export default function Paywall({ state, onState, nav }: Props) {
  const { plan } = state
  const preview = state.preview!
  useTitle('Ваш отчёт готов')
  useEffect(() => api.track('paywall_view', state.id), [state.id])
  const go = () => nav(`/t/${state.id}/checkout`)

  return (
    <main className="screen paywall">
      <p className="chip chip-ok">✓ Анализ завершён</p>
      <h1 className="title-page">Ваш отчёт готов</h1>
      <p className="lead">
        Вы ответили на {preview.answered} из {preview.total} вопросов за {clock(preview.duration_sec)}.
        Результат посчитан и сохранён.
      </p>

      <div className="card locked" aria-label="Отчёт закрыт до оплаты">
        <div className="locked-blur" aria-hidden="true">
          <div className="locked-iq"><span>Ваш IQ</span><b>000</b></div>
          {preview.categories.map((title, i) => (
            <div className="bar-row" key={title}>
              <span>{title}</span>
              <div className="bar"><div style={{ width: `${[72, 48, 85, 60][i % 4]}%` }} /></div>
            </div>
          ))}
        </div>
        <div className="locked-badge"><span className="chip">Откроется после оплаты</span></div>
      </div>

      <section>
        <h2>Что даёт подписка</h2>
        <ul className="checks">
          <li><b>Отчёт по этому тесту</b> — IQ по стандартной шкале с погрешностью, процентиль и уровень</li>
          <li><b>Профиль по 4 навыкам</b> — сильные стороны и зоны роста</li>
          <li><b>Разбор всех {preview.total} вопросов</b> — верные ответы с объяснениями</li>
          <li><b>Повторные прохождения без ограничений</b> — каждый раз новый набор заданий</li>
          <li><b>Динамика результата</b> — история ваших попыток на одном графике</li>
        </ul>
      </section>

      <div className="card terms">
        <div className="price-row">
          <span>{plan.title}</span>
          <b>{price(plan.amount)}</b>
        </div>
        <ul>
          <li>Это подписка: {price(plan.amount)} раз в {plan.period_days} дней, пока вы её не отмените.</li>
          <li>Отмена — одной кнопкой на странице результата. Доступ останется до конца оплаченного периода.</li>
          <li>Никаких пробных периодов за 1 ₽ и скрытых доплат.</li>
        </ul>
      </div>

      <LeadForm state={state} onState={onState} />

      <div className="sticky-cta">
        <button className="btn btn-primary btn-lg" onClick={go}>Открыть результат — {price(plan.amount)}</button>
      </div>
    </main>
  )
}

/** Не готов платить сейчас — оставь почту: результат не пропадёт, а у нас появляется контакт. */
function LeadForm({ state, onState }: Pick<Props, 'state' | 'onState'>) {
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (state.lead_email)
    return (
      <div className="card lead-card" role="status">
        <b>Результат сохранён за {state.lead_email}</b>
        <p className="muted">Вернуться к оплате можно по ссылке на эту страницу. В демо-режиме письма не отправляются.</p>
      </div>
    )

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!isEmail(email)) {
      setError('Проверьте адрес почты')
      return
    }
    setBusy(true)
    setError('')
    try {
      onState(await api.lead(state.id, email))
    } catch (err) {
      setError((err as Error).message)
    }
    setBusy(false)
  }

  return (
    <form className="card lead-card" onSubmit={submit} noValidate>
      <label htmlFor="lead-email"><b>Не готовы сейчас?</b> Сохраним результат и пришлём ссылку на него</label>
      <div className="inline-form">
        <input id="lead-email" type="email" inputMode="email" autoComplete="email" placeholder="you@example.com"
          autoCapitalize="none" spellCheck={false} value={email} onChange={(e) => setEmail(e.target.value)}
          disabled={busy} aria-invalid={!!error} />
        <button className="btn btn-ghost" type="submit" disabled={busy}>{busy ? 'Сохраняем…' : 'Сохранить'}</button>
      </div>
      {error && <p className="alert-error" role="alert">{error}</p>}
    </form>
  )
}
