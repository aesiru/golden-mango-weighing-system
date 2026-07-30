import { test, expect } from '@playwright/test'

test.describe('Login Flow', () => {
  test('should show login page', async ({ page }) => {
    await page.goto('/login')
    await expect(page).toHaveURL(/login/)
    await expect(page.locator('input[type="text"], input[name="username"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
  })

  test('should reject invalid credentials', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="text"], input[name="username"]', 'baduser')
    await page.fill('input[type="password"]', 'badpass')
    await page.click('button[type="submit"]')
    // Should stay on login page or show error
    await expect(page).toHaveURL(/login/)
  })

  test('should login with valid credentials and redirect', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="text"], input[name="username"]', 'admin')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button[type="submit"]')
    // Should redirect away from login
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 })
    expect(page.url()).not.toContain('/login')
  })
})

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.fill('input[type="text"], input[name="username"]', 'admin')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button[type="submit"]')
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 })
  })

  test('should load home page after login', async ({ page }) => {
    await expect(page.locator('body')).toBeVisible()
  })

  test('should navigate to an entity list', async ({ page }) => {
    await page.goto('/asset')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('body')).toBeVisible()
  })
})
