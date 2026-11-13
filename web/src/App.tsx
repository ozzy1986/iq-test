import { useCallback, useEffect, useState } from 'react'
import { api, ApiError, saved, type SessionState } from './api'
import Checkout from './screens/Checkout'
import Landing from './screens/Landing'
import Paywall from './screens/Paywall'
import Quiz from './screens/Quiz'
import ResultScreen from './screens/Result'
import { ErrorBoundary, Status } from './ui'

const ROUTE = /^\/t\/([0-9a-f-]{36})(\/checkout)?\/?$/

export type Nav = (path: string, replace?: boolean) => void

export default function App() {
  const [path, setPath] = useState(location.pathname)
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState('')

  useEffect(() => {
    const onPop = () => setPath(location.pathname)
    addEventListener('popstate', onPop)
    return () => removeEventListener('popstate', onPop)
  }, [])

  const nav: Nav = useCallback((to, replace) => {
    if (replace) history.replaceState(null, '', to)
    else history.pushState(null, '', to)
    setPath(to)
    scrollTo(0, 0)
  }, [])

  const start = useCallback(async () => {
    setStarting(true)
    setStartError('')
    try {
      const s = await api.create()
      saved.set(s.id)
      nav(`/t/${s.id}`)
    } catch (e) {
      setStartError((e as Error).message)
    }
    setStarting(false)
  }, [nav])

  const match = path.match(ROUTE)
  return (
    <div className="app">
      <header className="site-header">
        <div className="header-inner">
          <a className="brand" href="/" onClick={(e) => { e.preventDefault(); nav('/') }}>
            <span className="brand-mark" aria-hidden="true">IQ</span>Тест
          </a>
          {!match && (
            <button className="btn btn-primary nav-cta" onClick={start} disabled={starting}>Начать тест</button>
          )}
        </div>
      </header>
      <ErrorBoundary key={path}>
        {match
          ? <Flow key={match[1]} id={match[1]} checkout={!!match[2]} nav={nav} />
          : <Landing nav={nav} start={start} starting={starting} error={startError} />}
      </ErrorBoundary>
    </div>
  )
}

/** Экран определяется состоянием на сервере — обновление страницы ничего не сбрасывает. */
function Flow({ id, checkout, nav }: { id: string; checkout: boolean; nav: Nav }) {
  const [state, setState] = useState<SessionState | null>(null)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    api.get(id).then((s) => { saved.set(s.id); setState(s) }).catch((e: ApiError) => {
      if (e.status === 404) saved.set(null)
      setError(e)
    })
  }, [id])

  useEffect(() => {
    if (state && checkout && (state.access || state.status !== 'finished')) nav(`/t/${id}`, true)
  }, [state, checkout, id, nav])

  if (error?.status === 404)
    return <Status title="Тест не найден" text="Ссылка устарела или введена с ошибкой."
      action={{ label: 'На главную', onClick: () => nav('/') }} />
  if (error)
    return <Status title="Не удалось загрузить тест" text={error.message}
      action={{ label: 'Повторить', onClick: () => location.reload() }} />
  if (!state) return <Status />

  if (state.status === 'started') return <Quiz state={state} onFinished={setState} />
  if (state.access) return <ResultScreen state={state} onState={setState} nav={nav} />
  if (checkout) return <Checkout state={state} onPaid={(s) => { setState(s); nav(`/t/${id}`, true) }} nav={nav} />
  return <Paywall state={state} nav={nav} />
}
