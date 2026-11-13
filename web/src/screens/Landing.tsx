import { useEffect, useState } from 'react'
import { api, price, saved, type Plan } from '../api'
import type { Nav } from '../App'
import { FigCell } from '../Figure'
import { useTitle } from '../ui'

type Props = { nav: Nav; start: () => void; starting: boolean; error: string }

export default function Landing({ nav, start, starting, error }: Props) {
  const [plan, setPlan] = useState<Plan | null>(null)
  const resumeId = saved.get()
  useTitle('Узнайте свой IQ за 10 минут')

  useEffect(() => {
    api.track('landing_view')
    api.plan().then((p) => setPlan(p.plan)).catch(() => {})
  }, [])

  const cta = (
    <button className="btn btn-primary btn-lg" onClick={start} disabled={starting}>
      {starting ? 'Готовим тест…' : 'Начать тест'}
    </button>
  )

  return (
    <main className="screen landing">
      <section className="hero">
        <p className="chip chip-accent">Бесплатно · без регистрации</p>
        <h1 className="title-hero">Узнайте свой IQ за 10 минут</h1>
        <p className="lead">12 заданий на числовые ряды, аналогии, логику и визуальные паттерны — от простых к сложным.</p>

        <div className="hero-art" aria-hidden="true">
          <FigCell fig={{ shape: 'circle', count: 1, fill: 'solid', rot: 0 }} />
          <FigCell fig={{ shape: 'square', count: 1, fill: 'light', rot: 0 }} />
          <FigCell fig={{ shape: 'triangle', count: 1, fill: 'none', rot: 0 }} />
          <FigCell fig={null} />
        </div>

        <div className="cta-block">
          {cta}
          {resumeId && (
            <button className="btn btn-ghost btn-lg" onClick={() => nav(`/t/${resumeId}`)}>Продолжить прошлый тест</button>
          )}
          {error && <p className="alert-error" role="alert">{error}</p>}
          <p className="fineprint">
            Тест бесплатный. Подробный отчёт с результатом — по подписке
            {plan ? ` ${price(plan.amount)} в месяц` : ''}, отмена в один клик.
          </p>
        </div>
      </section>

      <ul className="facts">
        <li><b>12</b><span>вопросов</span></li>
        <li><b>~10</b><span>минут</span></li>
        <li><b>4</b><span>навыка</span></li>
      </ul>

      <section className="how">
        <h2 className="title-section">Как это работает</h2>
        <ol>
          <li className="card"><h3>Проходите тест</h3><p>Один вопрос на экран, к прошлым можно вернуться. Прогресс сохраняется.</p></li>
          <li className="card"><h3>Видите, что будет в отчёте</h3><p>До оплаты показываем состав отчёта и все условия подписки.</p></li>
          <li className="card"><h3>Получаете результат</h3><p>IQ, процентиль, профиль по четырём навыкам и разбор каждого вопроса.</p></li>
        </ol>
        <div className="cta-block">{cta}</div>
      </section>

      <p className="fineprint center-text">
        Тест носит развлекательно-познавательный характер и не является клинической или профессиональной
        психометрической диагностикой.
      </p>
    </main>
  )
}
