import { useCallback, useEffect, useState } from 'react'
import { api, ApiError, saved, type SessionState } from './api'
import Checkout from './screens/Checkout'
import Landing from './screens/Landing'
import Paywall from './screens/Paywall'
import Quiz from './screens/Quiz'
import ResultScreen from './screens/Result'

const ROUTE = /^\/t\/([0-9a-f-]{36})(\/checkout)?\/?$/

export type Nav = (path: string, replace?: boolean) => void

export default function App() {
  const [path, setPath] = useState(location.pathname)

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

  const match = path.match(ROUTE)
  return (
    <div className="app">
      <header className="topbar">
        <a className="logo" href="/" onClick={(e) => { e.preventDefault(); nav('/') }}>
          <span className="logo-mark">IQ</span> Тест
        </a>
      </header>
      {match ? <Flow key={match[1]} id={match[1]} checkout={!!match[2]} nav={nav} /> : <Landing nav={nav} />}
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

  if (error)
    return (
      <main className="screen center">
        <h1>{error.status === 404 ? 'Тест не найден' : 'Не удалось загрузить тест'}</h1>
        <p className="muted">{error.status === 404 ? 'Ссылка устарела или введена с ошибкой.' : error.message}</p>
        <button className="btn" onClick={() => (error.status === 404 ? nav('/') : location.reload())}>
          {error.status === 404 ? 'На главную' : 'Повторить'}
        </button>
      </main>
    )
  if (!state) return <main className="screen center"><div className="spinner" aria-label="Загрузка" /></main>

  if (state.status === 'started') return <Quiz state={state} onFinished={setState} />
  if (state.access) return <ResultScreen state={state} onState={setState} nav={nav} />
  if (checkout) return <Checkout state={state} onPaid={(s) => { setState(s); nav(`/t/${id}`, true) }} nav={nav} />
  return <Paywall state={state} nav={nav} />
}
