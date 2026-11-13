import { useEffect, useState, type FormEvent } from 'react'
import { api, price, type SessionState } from '../api'
import type { Nav } from '../App'

export default function Checkout({ state, onPaid, nav }: { state: SessionState; onPaid: (s: SessionState) => void; nav: Nav }) {
  const { plan } = state
  const [email, setEmail] = useState(state.email ?? '')
  const [stage, setStage] = useState<'form' | 'paying' | 'done'>('form')
  const [error, setError] = useState('')

  useEffect(() => api.track('checkout_view', state.id), [state.id])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email.trim())) {
      setError('Проверьте адрес почты')
      return
    }
    setError('')
    setStage('paying')
    try {
      const [next] = await Promise.all([api.checkout(state.id, email), new Promise((r) => setTimeout(r, 1200))])
      setStage('done')
      setTimeout(() => onPaid(next), 1100)
    } catch (err) {
      setStage('form')
      setError((err as Error).message)
    }
  }

  if (stage === 'done')
    return (
      <main className="screen center">
        <div className="success-mark">✓</div>
        <h1>Оплата прошла</h1>
        <p className="muted">Открываем ваш отчёт…</p>
      </main>
    )

  return (
    <main className="screen checkout">
      <button className="link-btn" onClick={() => nav(`/t/${state.id}`)} disabled={stage === 'paying'}>← Назад</button>
      <h1>Оформление подписки</h1>

      <div className="card">
        <div className="price-row"><span>{plan.title}</span><b>{price(plan.amount)}</b></div>
        <div className="price-row muted"><span>Следующее списание</span><span>через {plan.period_days} дней</span></div>
        <div className="price-row total"><span>К оплате сегодня</span><b>{price(plan.amount)}</b></div>
      </div>

      <form onSubmit={submit} noValidate>
        <label htmlFor="email">Электронная почта</label>
        <input id="email" type="email" inputMode="email" autoComplete="email" placeholder="you@example.com"
          value={email} onChange={(e) => setEmail(e.target.value)} disabled={stage === 'paying'}
          aria-invalid={!!error} aria-describedby="email-hint" />
        <p className="fineprint" id="email-hint">К этому адресу привязывается подписка. В демо-режиме письма не отправляются.</p>

        <div className="demo-note">
          <b>Демо-режим.</b> Платёжный провайдер не подключён: карта не нужна, деньги не списываются.
          Кнопка ниже имитирует успешный платёж.
        </div>

        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn-lg" type="submit" disabled={stage === 'paying'}>
          {stage === 'paying' ? 'Проводим платёж…' : `Оплатить ${price(plan.amount)}`}
        </button>
        <p className="fineprint">
          Подписка продлевается автоматически каждые {plan.period_days} дней. Отменить можно в любой момент
          на странице результата.
        </p>
      </form>
    </main>
  )
}
