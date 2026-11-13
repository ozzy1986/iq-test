import { useEffect, useState } from 'react'
import { api, saved } from '../api'
import type { Nav } from '../App'
import { FigCell } from '../Figure'

export default function Landing({ nav }: { nav: Nav }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const resumeId = saved.get()

  useEffect(() => api.track('landing_view'), [])

  const start = async () => {
    setBusy(true)
    setError('')
    try {
      const s = await api.create()
      saved.set(s.id)
      nav(`/t/${s.id}`)
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  return (
    <main className="screen landing">
      <div className="hero-art" aria-hidden="true">
        <FigCell fig={{ shape: 'circle', count: 1, fill: 'solid', rot: 0 }} />
        <FigCell fig={{ shape: 'square', count: 1, fill: 'light', rot: 0 }} />
        <FigCell fig={{ shape: 'triangle', count: 1, fill: 'none', rot: 0 }} />
        <FigCell fig={null} />
      </div>
      <h1>Узнайте свой IQ за 10 минут</h1>
      <p className="lead">12 заданий на числовые ряды, аналогии, логику и визуальные паттерны — от простых к сложным.</p>

      <ul className="facts">
        <li><b>12</b><span>вопросов</span></li>
        <li><b>~10</b><span>минут</span></li>
        <li><b>4</b><span>навыка</span></li>
      </ul>

      <div className="cta-block">
        <button className="btn btn-lg" onClick={start} disabled={busy}>
          {busy ? 'Готовим тест…' : 'Начать тест'}
        </button>
        {resumeId && (
          <button className="btn btn-ghost" onClick={() => nav(`/t/${resumeId}`)}>Продолжить прошлый тест</button>
        )}
        {error && <p className="error" role="alert">{error}</p>}
        <p className="fineprint">
          Тест бесплатный, без регистрации. Подробный отчёт с результатом — по подписке 299 ₽ в месяц,
          отмена в один клик.
        </p>
      </div>

      <section className="how">
        <h2>Как это работает</h2>
        <ol>
          <li><b>Проходите тест.</b> Один вопрос на экран, к прошлым можно вернуться. Прогресс сохраняется.</li>
          <li><b>Видите, что будет в отчёте.</b> До оплаты показываем состав отчёта и все условия подписки.</li>
          <li><b>Получаете результат.</b> IQ, процентиль, профиль по четырём навыкам и разбор каждого вопроса.</li>
        </ol>
      </section>
      <p className="fineprint">
        Тест носит развлекательно-познавательный характер и не является клинической или профессиональной
        психометрической диагностикой.
      </p>
    </main>
  )
}
