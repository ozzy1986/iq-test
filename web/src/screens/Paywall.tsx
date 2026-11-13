import { useEffect } from 'react'
import { api, clock, price, type SessionState } from '../api'
import type { Nav } from '../App'
import { useTitle } from '../ui'

export default function Paywall({ state, nav }: { state: SessionState; nav: Nav }) {
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

      <h2>Что внутри отчёта</h2>
      <ul className="checks">
        <li><b>Ваш IQ и уровень</b> — число и что оно значит</li>
        <li><b>Процентиль</b> — у какой доли людей результат ниже вашего</li>
        <li><b>Профиль по 4 навыкам</b> — сильные стороны и зоны роста</li>
        <li><b>Разбор всех {preview.total} вопросов</b> — верные ответы с объяснениями</li>
      </ul>

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

      <div className="sticky-cta">
        <button className="btn btn-primary btn-lg" onClick={go}>Открыть результат — {price(plan.amount)}</button>
      </div>
    </main>
  )
}
