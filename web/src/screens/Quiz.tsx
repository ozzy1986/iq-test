import { useEffect, useState } from 'react'
import { api, type SessionState } from '../api'
import { FigCell, OptionBody } from '../Figure'

const STEPS = ['Проверяем ответы', 'Считаем баллы по четырём навыкам', 'Собираем отчёт']

export default function Quiz({ state, onFinished }: { state: SessionState; onFinished: (s: SessionState) => void }) {
  const { questions } = state
  const [answers, setAnswers] = useState(state.answers)
  const [index, setIndex] = useState(() => {
    const first = questions.findIndex((q) => !(q.id in state.answers))
    return first === -1 ? questions.length - 1 : first
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [analyzing, setAnalyzing] = useState(false)

  const q = questions[index]
  const last = index === questions.length - 1
  const chosen = answers[q.id]

  const finish = async () => {
    setBusy(true)
    setError('')
    try {
      const [next] = await Promise.all([api.finish(state.id), new Promise((r) => setTimeout(r, 2600))])
      onFinished(next)
    } catch (e) {
      setAnalyzing(false)
      setBusy(false)
      setError((e as Error).message)
    }
  }

  const choose = async (option: number) => {
    if (busy) return
    setBusy(true)
    setError('')
    const next = { ...answers, [q.id]: option }
    setAnswers(next)
    try {
      await api.answer(state.id, q.id, option)
      await new Promise((r) => setTimeout(r, 220)) // дать увидеть выбранный вариант
      if (!last) setIndex(index + 1)
      else if (questions.every((x) => x.id in next)) {
        setAnalyzing(true)
        return finish()
      }
    } catch (e) {
      setAnswers(answers)
      setError((e as Error).message)
    }
    setBusy(false)
  }

  if (analyzing) return <Analyzing />

  const visual = !!q.options[0].fig
  return (
    <main className="screen quiz">
      <div className="progress-row">
        <button className="link-btn" onClick={() => setIndex(index - 1)} disabled={index === 0 || busy}>← Назад</button>
        <span className="muted">{index + 1} из {questions.length}</span>
      </div>
      <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={questions.length} aria-valuenow={index}>
        <div style={{ width: `${(index / questions.length) * 100}%` }} />
      </div>

      <div className="question" key={q.id}>
        <p className="tag">{q.category}</p>
        <h1 className="prompt">{q.prompt}</h1>
        {q.series && <p className="series">{q.series}</p>}
        {q.figure && (
          <div className="matrix" style={{ gridTemplateColumns: `repeat(${q.figure.cols}, 1fr)`, maxWidth: q.figure.cols * 84 }}>
            {q.figure.cells.map((cell, i) => <FigCell key={i} fig={cell} />)}
          </div>
        )}
        <div className={visual ? 'options options-visual' : 'options'}>
          {q.options.map((option, i) => (
            <button key={i} className={'option' + (chosen === i ? ' selected' : '')} onClick={() => choose(i)}
              aria-pressed={chosen === i} disabled={busy}>
              <i>{'ABCD'[i]}</i>
              <OptionBody option={option} />
            </button>
          ))}
        </div>
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {chosen !== undefined && !busy && (
        last
          ? <button className="btn" onClick={() => { setAnalyzing(true); finish() }}>Завершить тест</button>
          : <button className="btn btn-ghost" onClick={() => setIndex(index + 1)}>Далее →</button>
      )}
    </main>
  )
}

function Analyzing() {
  const [step, setStep] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 850)
    return () => clearInterval(t)
  }, [])
  return (
    <main className="screen center">
      <div className="spinner" />
      <h1>Тест завершён</h1>
      <ul className="steps">
        {STEPS.map((text, i) => (
          <li key={text} className={i < step ? 'done' : i === step ? 'active' : ''}>{text}</li>
        ))}
      </ul>
    </main>
  )
}
