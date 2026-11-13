import { Component, useEffect, type ReactNode } from 'react'

/** Заголовок вкладки под текущий экран. */
export function useTitle(title: string) {
  useEffect(() => {
    document.title = `${title} — IQ-тест`
  }, [title])
}

/** Экран-состояние: загрузка, ошибка, подтверждение — одна разметка на всё приложение. */
export function Status({ title, text, action, children }: {
  title?: string
  text?: string
  action?: { label: string; onClick: () => void }
  children?: ReactNode
}) {
  return (
    <main className="screen center" aria-live="polite">
      {children ?? (!title && <div className="spinner" role="status" aria-label="Загрузка" />)}
      {title && <h1 className="title-page">{title}</h1>}
      {text && <p className="muted">{text}</p>}
      {action && <button className="btn btn-primary" onClick={action.onClick}>{action.label}</button>}
    </main>
  )
}

/** Ошибка рендера не должна оставлять человека с пустой страницей. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <Status title="Что-то сломалось" text="Обновите страницу — ваш прогресс сохранён на сервере."
        action={{ label: 'Обновить', onClick: () => location.reload() }} />
    )
  }
}
