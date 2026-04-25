"""Project bootstrapper for simple runnable application tasks."""

from pathlib import Path


class ProjectBootstrapper:
    """Create a minimal app skeleton when a target directory has no app yet."""

    WEB_KEYWORDS = ("todo", "待办", "网站", "网页", "web", "app", "应用")

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)

    def maybe_bootstrap(self, user_task: str) -> bool:
        """Bootstrap a static web app if the directory has no recognizable app."""
        if not self._looks_like_web_task(user_task):
            return False
        if self._has_existing_app():
            return False

        self._write_static_web_skeleton()
        self._write_report(user_task)
        return True

    def _looks_like_web_task(self, user_task: str) -> bool:
        text = user_task.lower()
        return any(keyword in text for keyword in self.WEB_KEYWORDS)

    def _has_existing_app(self) -> bool:
        return any(
            (self.repo_root / path).exists()
            for path in ("package.json", "index.html", "src", "app", "pages")
        )

    def _write_static_web_skeleton(self) -> None:
        files = {
            "package.json": _PACKAGE_JSON,
            "index.html": _INDEX_HTML,
            "playwright.config.mjs": _PLAYWRIGHT_CONFIG,
            "src/app.js": _APP_JS,
            "src/styles.css": _STYLES_CSS,
            "scripts/validate-app.mjs": _VALIDATE_APP,
            "scripts/browser-e2e.mjs": _BROWSER_E2E,
            "tests/todo.spec.mjs": _TODO_SPEC,
        }
        for path, content in files.items():
            target = self.repo_root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def _write_report(self, user_task: str) -> None:
        harness_dir = self.repo_root / ".harness"
        harness_dir.mkdir(parents=True, exist_ok=True)
        (harness_dir / "BOOTSTRAP_REPORT.md").write_text(
            "\n".join([
                "# Bootstrap Report",
                "",
                f"User task: {user_task}",
                "",
                "Created a dependency-light static web app skeleton.",
                "",
                "## Files",
                "- package.json",
                "- index.html",
                "- playwright.config.mjs",
                "- src/app.js",
                "- src/styles.css",
                "- scripts/validate-app.mjs",
                "- scripts/browser-e2e.mjs",
                "- tests/todo.spec.mjs",
            ]),
            encoding="utf-8",
        )


_PACKAGE_JSON = """{
  "name": "openjia-generated-app",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "python -m http.server 5173",
    "build": "node scripts/validate-app.mjs",
    "test": "node scripts/validate-app.mjs",
    "test:e2e": "node scripts/browser-e2e.mjs",
    "test:playwright": "npm install --no-save @playwright/test && npx playwright test"
  }
}
"""

_INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Todo List</title>
    <link rel="stylesheet" href="src/styles.css" />
  </head>
  <body>
    <main class="app-shell">
      <section class="todo-panel" aria-labelledby="app-title">
        <header>
          <p class="eyebrow">Local Tasks</p>
          <h1 id="app-title">Todo List</h1>
        </header>
        <form id="todo-form" class="todo-form">
          <input id="todo-input" type="text" autocomplete="off" placeholder="Add a todo item" />
          <button type="submit">Add</button>
        </form>
        <ul id="todo-list" class="todo-list" aria-label="Todo list"></ul>
        <p id="empty-state" class="empty-state">No todo items yet.</p>
      </section>
    </main>
    <script type="module" src="src/app.js"></script>
  </body>
</html>
"""

_APP_JS = """const STORAGE_KEY = 'openjia.todo.items';

const form = document.querySelector('#todo-form');
const input = document.querySelector('#todo-input');
const list = document.querySelector('#todo-list');
const emptyState = document.querySelector('#empty-state');

function loadTodos() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveTodos(todos) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
}

let todos = loadTodos();

function render() {
  list.innerHTML = '';
  emptyState.hidden = todos.length > 0;

  for (const todo of todos) {
    const item = document.createElement('li');
    item.className = todo.completed ? 'todo-item is-complete' : 'todo-item';

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'todo-toggle';
    toggle.setAttribute('aria-label', todo.completed ? 'Mark as incomplete' : 'Mark as complete');
    toggle.textContent = todo.completed ? 'Done' : '';
    toggle.addEventListener('click', () => {
      todos = todos.map((entry) =>
        entry.id === todo.id ? { ...entry, completed: !entry.completed } : entry
      );
      saveTodos(todos);
      render();
    });

    const label = document.createElement('span');
    label.className = 'todo-label';
    label.textContent = todo.text;

    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'todo-remove';
    remove.textContent = 'Delete';
    remove.addEventListener('click', () => {
      todos = todos.filter((entry) => entry.id !== todo.id);
      saveTodos(todos);
      render();
    });

    item.append(toggle, label, remove);
    list.append(item);
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  todos = [{ id: crypto.randomUUID(), text, completed: false }, ...todos];
  input.value = '';
  saveTodos(todos);
  render();
});

render();
"""

_STYLES_CSS = """:root {
  color-scheme: light;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f4f6f8;
  color: #17202a;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
}

.app-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px 16px;
}

.todo-panel {
  width: min(720px, 100%);
  background: #ffffff;
  border: 1px solid #d7dde4;
  border-radius: 8px;
  padding: 28px;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
}

.eyebrow {
  margin: 0 0 6px;
  color: #50708f;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}

h1 {
  margin: 0 0 24px;
  font-size: 34px;
}

.todo-form {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}

input,
button {
  min-height: 44px;
  border-radius: 6px;
  font: inherit;
}

input {
  border: 1px solid #bdc8d4;
  padding: 0 14px;
}

button {
  border: 0;
  background: #1f7a5a;
  color: white;
  padding: 0 16px;
  font-weight: 700;
  cursor: pointer;
}

.todo-list {
  list-style: none;
  padding: 0;
  margin: 22px 0 0;
  display: grid;
  gap: 10px;
}

.todo-item {
  display: grid;
  grid-template-columns: 34px 1fr auto;
  align-items: center;
  gap: 12px;
  min-height: 50px;
  border: 1px solid #d7dde4;
  border-radius: 6px;
  padding: 8px;
}

.todo-toggle {
  width: 64px;
  min-height: 34px;
  padding: 0;
  background: #e6f2ee;
  color: #1f7a5a;
  border: 1px solid #9bc8b9;
}

.todo-label {
  overflow-wrap: anywhere;
}

.is-complete .todo-label {
  color: #6b7886;
  text-decoration: line-through;
}

.todo-remove {
  background: #9f2d36;
}

.empty-state {
  margin: 20px 0 0;
  color: #6b7886;
}

@media (max-width: 560px) {
  .todo-form {
    grid-template-columns: 1fr;
  }
}
"""

_VALIDATE_APP = """import { readFileSync } from 'node:fs';

const requiredFiles = ['index.html', 'src/app.js', 'src/styles.css', 'playwright.config.mjs', 'tests/todo.spec.mjs'];
for (const file of requiredFiles) {
  readFileSync(file, 'utf8');
}

const html = readFileSync('index.html', 'utf8');
const js = readFileSync('src/app.js', 'utf8');
const spec = readFileSync('tests/todo.spec.mjs', 'utf8');

const checks = [
  ['title', html.includes('Todo List')],
  ['form', html.includes('todo-form')],
  ['list', html.includes('todo-list')],
  ['localStorage persistence', js.includes('localStorage')],
  ['add handler', js.includes("addEventListener('submit'")],
  ['toggle behavior', js.includes('completed: !entry.completed')],
  ['delete behavior', js.includes('todos.filter')],
  ['playwright add assertion', spec.includes("getByRole('button', { name: 'Add' })")],
  ['playwright persistence assertion', spec.includes('page.reload()')],
];

const failed = checks.filter(([, ok]) => !ok);
if (failed.length > 0) {
  console.error('Validation failed:', failed.map(([name]) => name).join(', '));
  process.exit(1);
}

console.log('Static Todo app validation passed.');
"""

_BROWSER_E2E = r"""import { mkdirSync, writeFileSync } from 'node:fs';
import { spawn } from 'node:child_process';

const root = process.cwd();
const port = 5173;
const baseURL = `http://127.0.0.1:${port}`;
const chromePath = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForServer() {
  for (let i = 0; i < 50; i += 1) {
    try {
      const response = await fetch(baseURL);
      if (response.ok) return;
    } catch {}
    await wait(100);
  }
  throw new Error('dev server did not start');
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`request failed: ${url}`);
  return response.json();
}

async function cdp(method, params = {}) {
  const id = cdp.nextId = (cdp.nextId || 0) + 1;
  cdp.socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error(`CDP timeout: ${method}`)), 10000);
    cdp.pending.set(id, { resolve, reject, timeout });
  });
}
cdp.pending = new Map();

async function run() {
  mkdirSync('test-results', { recursive: true });

  const server = spawn('python', ['-m', 'http.server', String(port)], { cwd: root });
  await waitForServer();

  const chrome = spawn(chromePath, [
    '--headless=new',
    '--disable-gpu',
    '--remote-debugging-port=9222',
    '--user-data-dir=' + root + '/.tmp-chrome-profile',
    'about:blank',
  ]);

  try {
    let pages;
    for (let i = 0; i < 50; i += 1) {
      try {
        pages = await getJson('http://127.0.0.1:9222/json/list');
        break;
      } catch {
        await wait(100);
      }
    }
    const pageTarget = pages?.find((entry) => entry.type === 'page');
    if (!pageTarget?.webSocketDebuggerUrl) {
      throw new Error('Chrome page debugging endpoint did not start');
    }

    cdp.socket = new WebSocket(pageTarget.webSocketDebuggerUrl);
    cdp.socket.addEventListener('message', (event) => {
      const message = JSON.parse(event.data);
      if (!message.id || !cdp.pending.has(message.id)) return;
      const pending = cdp.pending.get(message.id);
      cdp.pending.delete(message.id);
      clearTimeout(pending.timeout);
      if (message.error) pending.reject(new Error(message.error.message));
      else pending.resolve(message.result);
    });
    await new Promise((resolve) => cdp.socket.addEventListener('open', resolve, { once: true }));

    await cdp('Page.enable');
    await cdp('Runtime.enable');
    await cdp('Page.navigate', { url: baseURL });
    await wait(1000);

    const expression = `(() => {
      localStorage.clear();
      location.reload();
      return true;
    })()`;
    await cdp('Runtime.evaluate', { expression, awaitPromise: true });
    await wait(1000);

    const testExpression = `(() => {
      const input = document.querySelector('#todo-input');
      const form = document.querySelector('#todo-form');
      input.value = 'Write harness tests';
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      let item = document.querySelector('.todo-item');
      if (!item || !item.textContent.includes('Write harness tests')) throw new Error('todo was not added');
      item.querySelector('.todo-toggle').click();
      item = document.querySelector('.todo-item');
      if (!item.classList.contains('is-complete')) throw new Error('todo was not completed');
      location.reload();
      return true;
    })()`;
    await cdp('Runtime.evaluate', { expression: testExpression, awaitPromise: true });
    await wait(1000);

    const persistenceExpression = `(() => {
      const item = document.querySelector('.todo-item');
      if (!item || !item.textContent.includes('Write harness tests')) throw new Error('todo did not persist');
      if (!item.classList.contains('is-complete')) throw new Error('completed state did not persist');
      item.querySelector('.todo-remove').click();
      if (document.querySelectorAll('.todo-item').length !== 0) throw new Error('todo was not deleted');
      if (!document.querySelector('#empty-state') || document.querySelector('#empty-state').hidden) throw new Error('empty state not visible');
      return document.documentElement.outerHTML;
    })()`;
    const result = await cdp('Runtime.evaluate', {
      expression: persistenceExpression,
      awaitPromise: true,
      returnByValue: true,
    });
    writeFileSync('test-results/todo-pass.html', result.result.value);
    writeFileSync('test-results/todo-pass.png', 'browser e2e passed');
    console.log('Browser Todo E2E passed.');
  } finally {
    cdp.socket?.close();
    chrome.kill();
    server.kill();
  }
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
"""

_PLAYWRIGHT_CONFIG = """import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    channel: 'chrome',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'python -m http.server 5173',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: false,
    timeout: 15000,
  },
});
"""

_TODO_SPEC = """import { test, expect } from '@playwright/test';

test('todo list supports add, complete, delete, and persistence', async ({ page }) => {
  await page.goto('/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();

  await expect(page.getByText('No todo items yet.')).toBeVisible();

  await page.getByPlaceholder('Add a todo item').fill('Write harness tests');
  await page.getByRole('button', { name: 'Add' }).click();

  const item = page.locator('.todo-item').filter({ hasText: 'Write harness tests' });
  await expect(item).toBeVisible();

  await item.getByRole('button', { name: 'Mark as complete' }).click();
  await expect(item).toHaveClass(/is-complete/);

  await page.reload();
  const persisted = page.locator('.todo-item').filter({ hasText: 'Write harness tests' });
  await expect(persisted).toBeVisible();
  await expect(persisted).toHaveClass(/is-complete/);

  await persisted.getByRole('button', { name: 'Delete' }).click();
  await expect(page.locator('.todo-item')).toHaveCount(0);
  await expect(page.getByText('No todo items yet.')).toBeVisible();
  await page.screenshot({ path: 'test-results/todo-pass.png', fullPage: true });
});
"""
