import { useEffect, useRef, useState } from 'react'
import { api, sleep, type SessionState } from '../api'
import { FigCell, OptionBody } from '../Figure'
import { Status, useTitle } from '../ui'

const STEPS = ['Проверяем ответы', 'Считаем баллы по четырём навыкам', 'Собираем отчёт']
const KEYS = ['1234', 'abcd', 'фисв'] // цифры и буквы A–D в обеих раскладках

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
  const heading = useRef<HTMLHeadingElement>(null)
  const mounted = useRef(false)

  const q = questions[index]
  const last = index === questions.length - 1
  const chosen = answers[q.id]
  useTitle(`Вопрос ${index + 1} из ${questions.length}`)

  // При смене вопроса переводим фокус на формулировку: скринридер читает новый вопрос,
  // а клавиатурный фокус не остаётся на исчезнувшей кнопке.
  useEffect(() => {
    if (mounted.current) heading.current?.focus({ preventScroll: true })
    mounted.current = true
    scrollTo(0, 0)
  }, [index])

  const finish = async () => {
    setAnalyzing(true)
    setBusy(true)
    setError('')
    try {
      const [next] = await Promise.all([api.finish(state.id), sleep(2600)])
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
      await sleep(220) // дать увидеть выбранный вариант
      if (!last) setIndex(index + 1)
      else if (questions.every((x) => x.id in next)) return finish()
    } catch (e) {
      setAnswers(answers)
      setError((e as Error).message)
    }
    setBusy(false)
  }

  // Клавиши 1–4 и A–D на десктопе.
  const chooseRef = useRef(choose)
  chooseRef.current = choose
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const key = e.key.toLowerCase()
      const option = KEYS.map((row) => row.indexOf(key)).find((i) => i >= 0)
      if (option !== undefined) chooseRef.current(option)
    }
    addEventListener('keydown', onKey)
    return () => removeEventListener('keydown', onKey)
  }, [])

  if (analyzing) return <Analyzing />

  const visual = !!q.options[0].fig
  return (
    <main className="screen quiz">
      <div className="progress-row">
        <button className="link-btn" onClick={() => setIndex(index - 1)} disabled={index === 0 || busy}>← Назад</button>
        <span className="muted" aria-live="polite">Вопрос {index + 1} из {questions.length}</span>
      </div>
      <div className="progress" role="progressbar" aria-label="Прогресс теста" aria-valuemin={0}
        aria-valuemax={questions.length} aria-valuenow={index}>
        <div style={{ width: `${(index / questions.length) * 100}%` }} />
      </div>

      <div className="question" key={q.id}>
        <p className="chip chip-accent">{q.category}</p>
        <h1 className="prompt" ref={heading} tabIndex={-1}>{q.prompt}</h1>
        {q.series && <p className="series">{q.series}</p>}
        {q.figure && (
          <div className="matrix" role="img" aria-label="Ряд фигур с пропуском"
            style={{ gridTemplateColumns: `repeat(${q.figure.cols}, 1fr)`, maxWidth: q.figure.cols * 88 }}>
            {q.figure.cells.map((cell, i) => <FigCell key={i} fig={cell} />)}
          </div>
        )}
        <div className={visual ? 'options options-visual' : 'options'} role="group" aria-label="Варианты ответа">
          {q.options.map((option, i) => (
            <button key={i} className={'option' + (chosen === i ? ' selected' : '')} onClick={() => choose(i)}
              aria-pressed={chosen === i} aria-label={option.fig ? `Вариант ${'ABCD'[i]}` : undefined} disabled={busy}>
              <i aria-hidden="true">{'ABCD'[i]}</i>
              <OptionBody option={option} />
            </button>
          ))}
        </div>
      </div>

      {error && <p className="alert-error" role="alert">{error}</p>}
      {chosen !== undefined && !busy && (
        last
          ? <button className="btn btn-primary btn-lg" onClick={finish}>Завершить тест</button>
          : <button className="btn btn-ghost btn-lg" onClick={() => setIndex(index + 1)}>Далее →</button>
      )}
    </main>
  )
}

function Analyzing() {
  const [step, setStep] = useState(0)
  useTitle('Тест завершён')
  useEffect(() => {
    const t = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 850)
    return () => clearInterval(t)
  }, [])
  return (
    <Status>
      <div className="spinner" aria-hidden="true" />
      <h1 className="title-page">Тест завершён</h1>
      <ul className="steps">
        {STEPS.map((text, i) => (
          <li key={text} className={i < step ? 'done' : i === step ? 'active' : ''}>{text}</li>
        ))}
      </ul>
    </Status>
  )
}
