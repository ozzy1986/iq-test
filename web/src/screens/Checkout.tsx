import { useEffect, useState, type FormEvent } from 'react'
import { api, isEmail, price, sleep, type SessionState } from '../api'
import type { Nav } from '../App'
import { Status, useTitle } from '../ui'

export default function Checkout({ state, onPaid, nav }: { state: SessionState; onPaid: (s: SessionState) => void; nav: Nav }) {
  const { plan } = state
  const [email, setEmail] = useState(state.email ?? '')
  const [stage, setStage] = useState<'form' | 'paying' | 'done'>('form')
  const [error, setError] = useState('')

  useTitle('Оформление подписки')
  useEffect(() => api.track('checkout_view', state.id), [state.id])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!isEmail(email)) {
      setError('Проверьте адрес почты')
      return
    }
    setError('')
    setStage('paying')
    try {
      const [next] = await Promise.all([api.checkout(state.id, email), sleep(1200)])
      setStage('done')
      setTimeout(() => onPaid(next), 1100)
    } catch (err) {
      setStage('form')
      setError((err as Error).message)
    }
  }

  if (stage === 'done')
    return (
      <Status title="Оплата прошла" text="Открываем ваш отчёт…">
        <div className="success-mark" aria-hidden="true">✓</div>
      </Status>
    )

  return (
    <main className="screen checkout">
      <button className="link-btn" onClick={() => nav(`/t/${state.id}`)} disabled={stage === 'paying'}>← Назад</button>
      <h1 className="title-page">Оформление подписки</h1>

      <div className="card">
        <div className="price-row"><span>{plan.title}</span><b>{price(plan.amount)}</b></div>
        <div className="price-row muted"><span>Следующее списание</span><span>через {plan.period_days} дней</span></div>
        <div className="price-row total"><span>К оплате сегодня</span><b>{price(plan.amount)}</b></div>
      </div>

      <form className="form-card" onSubmit={submit} noValidate>
        <label htmlFor="email">Электронная почта</label>
        <input id="email" type="email" inputMode="email" autoComplete="email" placeholder="you@example.com" enterKeyHint="go" autoCapitalize="none" spellCheck={false}
          value={email} onChange={(e) => setEmail(e.target.value)} disabled={stage === 'paying'}
          aria-invalid={!!error} aria-describedby="email-hint" />
        <p className="fineprint" id="email-hint">К этому адресу привязывается подписка. В демо-режиме письма не отправляются.</p>

        <div className="demo-note">
          <b>Демо-режим.</b> Платёжный провайдер не подключён: карта не нужна, деньги не списываются.
          Кнопка ниже имитирует успешный платёж.
        </div>

        {error && <p className="alert-error" role="alert">{error}</p>}
        <button className="btn btn-primary btn-lg" type="submit" disabled={stage === 'paying'}>
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
