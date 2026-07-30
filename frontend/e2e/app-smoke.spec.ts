import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "@playwright/test";

const USERNAME = process.env.E2E_USERNAME ?? "Administrator";
const PASSWORD = process.env.E2E_PASSWORD ?? "yTonJATR";
const BACKEND_API_URL =
  process.env.E2E_BACKEND_API_URL ?? "http://127.0.0.1:8000/api";

async function waitForOkResponse(page: Page, pattern: RegExp) {
  return page.waitForResponse(
    (response) =>
      pattern.test(response.url()) &&
      response.status() >= 200 &&
      response.status() < 300,
    { timeout: 20_000 },
  );
}

async function loginViaUi(page: Page) {
  await page.goto("/login");
  await page.getByPlaceholder("Enter your username").fill(USERNAME);
  await page.getByPlaceholder("Enter your password").fill(PASSWORD);

  const bootResponse = waitForOkResponse(page, /\/auth\/boot(?:$|\?)/);
  await page.getByRole("button", { name: "Sign In" }).click();

  await bootResponse;
  await page.waitForURL((url) => !url.pathname.includes("/login"), {
    timeout: 20_000,
  });
}

async function getBrowserToken(page: Page) {
  const token = await page.evaluate(() =>
    window.localStorage.getItem("auth_token"),
  );
  expect(token).toBeTruthy();
  return token as string;
}

async function getFirstEntityId(
  request: APIRequestContext,
  token: string,
  entity: string,
) {
  const response = await request.get(
    `${BACKEND_API_URL}/entity/${entity}/list?page=1&page_size=1`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  expect(response.ok()).toBeTruthy();

  const payload = await response.json();
  const firstRecord = payload?.data?.[0];

  expect(
    firstRecord?.id,
    `Expected at least one ${entity} record for the smoke test`,
  ).toBeTruthy();
  return String(firstRecord.id);
}

async function getFirstWorkflowId(request: APIRequestContext, token: string) {
  const response = await request.get(`${BACKEND_API_URL}/workflow`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  expect(response.ok()).toBeTruthy();

  const payload = await response.json();
  const firstWorkflow = payload?.data?.[0];

  expect(
    firstWorkflow?.id,
    "Expected at least one workflow for the smoke test",
  ).toBeTruthy();
  return String(firstWorkflow.id);
}

test.describe("Application smoke coverage", () => {
  test("admin can render core screens with live backend data", async ({
    page,
    request,
  }) => {
    test.slow();

    await loginViaUi(page);
    await expect(
      page.getByRole("heading", { name: /Welcome back/i }),
    ).toBeVisible();

    const token = await getBrowserToken(page);
    const roleId = await getFirstEntityId(request, token, "role");
    const workflowId = await getFirstWorkflowId(request, token);

    await test.step("dashboard loads its widgets", async () => {
      const dashboardResponse = waitForOkResponse(
        page,
        /\/operations\/dashboard\/widgets\//,
      );
      await page.goto("/dashboard");
      await dashboardResponse;

      await expect(
        page.getByRole("heading", { name: "Dashboard" }),
      ).toBeVisible();
      await expect(page.getByRole("button", { name: "Refresh" })).toBeVisible();
    });

    await test.step("entity list and detail routes load", async () => {
      const listResponse = waitForOkResponse(
        page,
        /\/entity\/role\/list(?:$|\?)/,
      );
      await page.goto("/role");
      await listResponse;

      await expect(page.locator("table").first()).toBeVisible();

      const detailResponse = waitForOkResponse(
        page,
        new RegExp(`/entity/role/detail/${roleId}(?:$|\\?)`),
      );
      await page.goto(`/role/${roleId}`);
      await detailResponse;

      await expect(page).toHaveURL(new RegExp(`/role/${roleId}(?:$|\\?)`));
      await expect(page.locator("body")).toBeVisible();
    });

    await test.step("workflow list and detail routes load", async () => {
      const workflowListResponse = waitForOkResponse(
        page,
        /\/workflow(?:$|\?)/,
      );
      await page.goto("/workflow");
      await workflowListResponse;

      await expect(
        page.getByRole("heading", { name: "Workflows" }),
      ).toBeVisible();

      const workflowDetailResponse = waitForOkResponse(
        page,
        new RegExp(`/workflow/${workflowId}(?:$|\\?)`),
      );
      await page.goto(`/workflow/${workflowId}`);
      await workflowDetailResponse;

      await expect(
        page.getByRole("button", { name: /Add State/i }),
      ).toBeVisible();
    });

    await test.step("calendar view renders with task data request", async () => {
      const calendarResponse = waitForOkResponse(
        page,
        /\/pm-calendar\/tasks(?:$|\?)/,
      );
      await page.goto("/calendar");
      await calendarResponse;

      await expect(page.getByRole("button", { name: "Today" })).toBeVisible();
      await expect(page.locator(".pm-calendar-page")).toBeVisible();
    });
  });
});
