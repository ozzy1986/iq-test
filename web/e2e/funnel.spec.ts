import { expect, test, type Page } from '@playwright/test'

const TOTAL = 30

async function expectNoHorizontalScroll(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
}

/** Все видимые кнопки не ниже 44 px — минимальная зона нажатия пальцем. */
async function expectTouchTargets(page: Page) {
  if ((page.viewportSize()?.width ?? 0) > 600) return // мышью попасть проще
  const small = await page.evaluate(() =>
    [...document.querySelectorAll('button, summary')]
      .filter((el) => (el as HTMLElement).offsetParent !== null)
      .map((el) => ({ label: el.textContent!.trim().slice(0, 30), height: el.getBoundingClientRect().height }))
      .filter((b) => b.height < 44))
  expect(small).toEqual([])
}

/** Снимок экрана целиком — в test-results, чтобы глазами посмотреть вёрстку после прогона. */
async function shot(page: Page, name: string) {
  await page.screenshot({ path: `test-results/screens/${test.info().project.name}-${name}.png`, fullPage: true })
}

async function startTest(page: Page) {
  await page.goto('/')
  await page.locator('main').getByRole('button', { name: 'Начать тест' }).first().click()
  await expect(page.getByText(`Вопрос 1 из ${TOTAL}`)).toBeVisible()
}

async function answerFrom(page: Page, first: number, shots?: string) {
  for (let n = first; n <= TOTAL; n++) {
    await expect(page.getByText(`Вопрос ${n} из ${TOTAL}`)).toBeVisible()
    if (shots && [8, 20, 30].includes(n)) await shot(page, `${shots}-${n}`)
    await page.locator('.option').first().click()
  }
}

test('воронка: тест → paywall → оплата → результат → повторное прохождение', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Узнайте свой IQ')
  await expect(page.getByText('7 дней за 29 ₽, затем 399 ₽ в месяц')).toBeVisible() // обе цены названы до старта
  await expectNoHorizontalScroll(page)
  await expectTouchTargets(page)

  await page.locator('main').getByRole('button', { name: 'Начать тест' }).first().click()
  await expect(page).toHaveURL(/\/t\/[0-9a-f-]{36}$/)
  await expectTouchTargets(page)

  // Прогресс переживает перезагрузку страницы, к прошлому вопросу можно вернуться.
  await page.locator('.option').first().click()
  await page.locator('.option').first().click()
  await expect(page.getByText(`Вопрос 3 из ${TOTAL}`)).toBeVisible()
  await page.reload()
  await expect(page.getByText(`Вопрос 3 из ${TOTAL}`)).toBeVisible()
  await page.getByRole('button', { name: '← Назад' }).click()
  await expect(page.getByText(`Вопрос 2 из ${TOTAL}`)).toBeVisible()
  await expect(page.locator('.option.selected')).toHaveCount(1)
  await expectNoHorizontalScroll(page)
  await page.getByRole('button', { name: 'Далее →' }).click()

  await answerFrom(page, 3, 'quiz')

  // Paywall: отчёт готов, но сам результат не показан.
  await expect(page.getByRole('heading', { name: 'Ваш отчёт готов' })).toBeVisible({ timeout: 15_000 })
  await expect(page.locator('.iq')).toHaveCount(0)
  await expect(page.getByText('Затем, если не отменить')).toBeVisible() // полная цена рядом с пробной
  await expect(page.getByText('399 ₽ в месяц', { exact: true })).toBeVisible()
  await shot(page, 'paywall')
  await expectNoHorizontalScroll(page)
  await expectTouchTargets(page)

  // Почта без оплаты: результат закрепляется за человеком.
  await page.getByRole('button', { name: 'Сохранить' }).click()
  await expect(page.getByRole('alert')).toHaveText('Проверьте адрес почты')
  await page.locator('#lead-email').fill('lead@example.com')
  await page.getByRole('button', { name: 'Сохранить' }).click()
  await expect(page.getByText('Результат сохранён за lead@example.com')).toBeVisible()

  // Оформление: проверка почты и имитация оплаты.
  await page.getByRole('button', { name: /Открыть результат/ }).click()
  await expect(page.getByRole('heading', { name: 'Оформление подписки' })).toBeVisible()
  await expect(page.getByText('Демо-режим.', { exact: true })).toBeVisible()
  await expect(page.getByText(/Следующее списание — .+/)).toBeVisible()
  await shot(page, 'checkout')
  await expectNoHorizontalScroll(page)
  await page.getByRole('button', { name: /Оплатить/ }).click()
  await expect(page.getByRole('alert')).toHaveText('Проверьте адрес почты')
  await page.locator('#email').fill('buyer@example.com')
  await page.getByRole('button', { name: /Оплатить/ }).click()
  await expect(page.getByRole('heading', { name: 'Оплата прошла' })).toBeVisible()

  // Результат открыт и остаётся открытым после перезагрузки.
  await expect(page.locator('.iq')).toBeVisible({ timeout: 10_000 })
  await page.reload()
  await expect(page.locator('.iq')).toContainText(/\d{2,3}±\d/)
  await expect(page.getByText('Выше, чем у')).toBeVisible()
  await shot(page, 'result')
  await expectNoHorizontalScroll(page)
  await expectTouchTargets(page)
  await page.getByText('Вопрос 1', { exact: true }).click()
  await expect(page.locator('.review details[open] .answer.ok')).toBeVisible()
  await expect(page.locator('.history li')).toHaveCount(1)
  await expect(page.getByText('Пробный период', { exact: true })).toBeVisible()

  // Отмена подписки в один клик, доступ сохраняется.
  await page.getByRole('button', { name: 'Отменить подписку' }).click()
  await page.getByRole('button', { name: 'Да, отменить' }).click()
  await expect(page.getByText('Отменена')).toBeVisible()
  await expect(page.locator('.iq')).toBeVisible()

  // Повторное прохождение: задания новые, paywall больше не появляется, попытка попадает в историю.
  await page.getByRole('button', { name: 'Пройти ещё раз с новыми заданиями' }).click()
  await answerFrom(page, 1)
  await expect(page.locator('.iq')).toBeVisible({ timeout: 15_000 })
  await expect(page.locator('.history li')).toHaveCount(2)
  await shot(page, 'result-second-attempt')
})

test('ответ с клавиатуры', async ({ page, isMobile }) => {
  test.skip(isMobile, 'на телефоне нет клавиатуры')
  await startTest(page)
  await page.keyboard.press('2')
  await expect(page.getByText(`Вопрос 2 из ${TOTAL}`)).toBeVisible()
  await expect(page.locator('h1.prompt')).toBeFocused() // фокус переходит на новый вопрос
})

test('неизвестная ссылка ведёт на понятный экран', async ({ page }) => {
  await page.goto('/t/00000000-0000-4000-8000-000000000000')
  await expect(page.getByRole('heading', { name: 'Тест не найден' })).toBeVisible()
  await page.getByRole('button', { name: 'На главную' }).click()
  await expect(page).toHaveURL(/\/$/)
})

test('оплаченную ссылку нельзя открыть в обход paywall', async ({ page, request }) => {
  await startTest(page)
  const id = page.url().split('/t/')[1]
  expect((await request.get(`/api/sessions/${id}/result`)).status()).toBe(409) // тест не завершён
  const state = await (await request.get(`/api/sessions/${id}`)).json()
  expect(JSON.stringify(state)).not.toContain('"correct"') // ответы не уходят в браузер
})
