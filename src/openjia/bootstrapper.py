"""Project bootstrapper for simple runnable application tasks."""

from pathlib import Path


class ProjectBootstrapper:
    """Create minimal runnable scaffolds when a target directory has no app yet."""

    WEB_KEYWORDS = ("网站", "网页", "web", "app", "应用")

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)

    def maybe_bootstrap(self, user_task: str, mode: str = "static_web") -> bool:
        """Bootstrap a web runtime if the directory has no recognizable app."""
        if not self._looks_like_web_task(user_task):
            return False
        if self._has_existing_app():
            return False

        if mode == "generic_web":
            self._write_generic_web_scaffold()
        else:
            self._write_static_web_skeleton()
        self._write_report(user_task, mode)
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
        """Backward-compatible alias for the generic runtime scaffold."""
        self._write_generic_web_scaffold()

    def _write_generic_web_scaffold(self) -> None:
        """Write runtime files only; Planner/Generator own app code."""
        files = {
            "package.json": _PACKAGE_JSON,
            "playwright.config.mjs": _PLAYWRIGHT_CONFIG,
            "scripts/validate-app.mjs": _GENERIC_VALIDATE_APP,
            "scripts/browser-e2e.mjs": _GENERIC_BROWSER_E2E,
        }
        self._write_files(files)

    def _write_files(self, files: dict[str, str]) -> None:
        for path, content in files.items():
            target = self.repo_root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def _write_report(self, user_task: str, mode: str) -> None:
        harness_dir = self.repo_root / ".harness"
        harness_dir.mkdir(parents=True, exist_ok=True)
        if mode == "generic_web":
            summary = "Created a generic web runtime scaffold. Business files are left to Planner/Generator."
            files = [
                "package.json",
                "playwright.config.mjs",
                "scripts/validate-app.mjs",
                "scripts/browser-e2e.mjs",
            ]
        else:
            summary = "Created a dependency-light generic web runtime scaffold."
            files = [
                "package.json",
                "playwright.config.mjs",
                "scripts/validate-app.mjs",
                "scripts/browser-e2e.mjs",
            ]
        (harness_dir / "BOOTSTRAP_REPORT.md").write_text(
            "\n".join([
                "# Bootstrap Report",
                "",
                f"User task: {user_task}",
                "",
                f"Mode: {mode}",
                "",
                summary,
                "",
                "## Files",
                *[f"- {path}" for path in files],
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

_GENERIC_VALIDATE_APP = """import { existsSync, readFileSync } from 'node:fs';

const requiredFiles = ['index.html'];
for (const file of requiredFiles) {
  if (!existsSync(file)) {
    console.error(`Missing required app file: ${file}`);
    process.exit(1);
  }
}

const html = readFileSync('index.html', 'utf8');
const checks = [
  ['doctype/html shell', /<html[\\s>]/i.test(html)],
  ['body content', /<body[\\s>]/i.test(html)],
  ['script or inline behavior', html.includes('<script') || existsSync('src/app.js')],
];

if (existsSync('src/app.js')) {
  const js = readFileSync('src/app.js', 'utf8');
  checks.push(['non-empty app script', js.trim().length > 0]);
}

if (existsSync('src/styles.css')) {
  const css = readFileSync('src/styles.css', 'utf8');
  checks.push(['non-empty stylesheet', css.trim().length > 0]);
}

const failed = checks.filter(([, ok]) => !ok);
if (failed.length > 0) {
  console.error('Validation failed:', failed.map(([name]) => name).join(', '));
  process.exit(1);
}

console.log('Generic web app validation passed.');
"""

_GENERIC_BROWSER_E2E = r"""import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { spawn } from 'node:child_process';

const root = process.cwd();
const port = 5173;
const baseURL = `http://127.0.0.1:${port}`;
const chromePath = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const chromeProfile = mkdtempSync(`${tmpdir()}/openjia-chrome-`);

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function cleanupChromeProfile() {
  try {
    rmSync(chromeProfile, { recursive: true, force: true });
  } catch {}
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
    '--user-data-dir=' + chromeProfile,
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

    const smoke = await cdp('Runtime.evaluate', {
      expression: `(() => {
        const text = document.body?.innerText || '';
        if (!document.body || text.trim().length === 0) throw new Error('page body is empty');
        return document.documentElement.outerHTML;
      })()`,
      awaitPromise: true,
      returnByValue: true,
    });
    if (smoke.exceptionDetails) {
      throw new Error(smoke.exceptionDetails.text || 'browser evaluation failed');
    }
    const html = smoke.result?.value;
    if (typeof html !== 'string') {
      throw new Error('browser evaluation did not return HTML evidence');
    }
    writeFileSync('test-results/page-smoke.html', html);

    const interactionProbe = await cdp('Runtime.evaluate', {
      expression: `(() => {
        const inputs = [...document.querySelectorAll('input, textarea')];
        const buttons = [...document.querySelectorAll('button')];
        const text = document.body.innerText.toLowerCase();
        return {
          hasTextInput: inputs.some((input) => !input.type || ['text', 'search', ''].includes(input.type)),
          hasAddButton: buttons.some((button) => /add|new|create|新增|添加/i.test(button.innerText || button.ariaLabel || '')),
          mentionsEntity: /item|task|entry|record|note|事项|任务|条目/.test(text),
        };
      })()`,
      awaitPromise: true,
      returnByValue: true,
    });
    const crudLike = Boolean(interactionProbe.result?.value?.hasTextInput && (interactionProbe.result?.value?.hasAddButton || interactionProbe.result?.value?.mentionsEntity));

    if (crudLike) {
      const addResult = await cdp('Runtime.evaluate', {
        expression: `(async () => {
          localStorage.clear();
          const input = document.querySelector('input[type="text"], input:not([type]), textarea, input[type="search"]');
          if (!input) throw new Error('text input not found');
          input.value = 'OpenJIA interaction test';
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          const addButton = [...document.querySelectorAll('button')]
            .find((button) => /add|new|create|新增|添加/i.test(button.innerText || button.ariaLabel || ''));
          if (addButton) addButton.click();
          else input.closest('form')?.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
          await new Promise((resolve) => setTimeout(resolve, 500));
          if (!document.body.innerText.includes('OpenJIA interaction test')) throw new Error('item add failed');

          const item = [...document.querySelectorAll('li, [data-testid], .item, .task-item, .entry, .record, article, div')]
            .find((node) => node.innerText?.includes('OpenJIA interaction test'));
          if (!item) throw new Error('created item not found after add');
          const completeButton = [...item.querySelectorAll('button, input[type="checkbox"]')]
            .find((node) => /complete|done|finish|完成|check|mark/i.test(node.innerText || node.ariaLabel || node.title || node.className || node.type || ''));
          if (completeButton) {
            completeButton.click();
            await new Promise((resolve) => setTimeout(resolve, 300));
          }
          return true;
        })()`,
        awaitPromise: true,
        returnByValue: true,
      });
      if (addResult.exceptionDetails) {
        throw new Error(addResult.exceptionDetails.text || 'item add/complete evaluation failed');
      }

      await cdp('Page.reload', { ignoreCache: true });
      await wait(1000);

      const interactionResult = await cdp('Runtime.evaluate', {
        expression: `(async () => {
          if (!document.body.innerText.includes('OpenJIA interaction test')) throw new Error('item persistence failed after refresh');

          const persisted = [...document.querySelectorAll('li, [data-testid], .item, .task-item, .entry, .record, article, div')]
            .find((node) => node.innerText?.includes('OpenJIA interaction test'));
          if (!persisted) throw new Error('persisted item not found after refresh');
          const deleteButton = [...(persisted || document).querySelectorAll('button')]
            .find((button) => /delete|remove|clear|删除|移除/i.test(button.innerText || button.ariaLabel || button.title || button.className || ''));
          if (!deleteButton) throw new Error('delete control not found');
          deleteButton.click();
          await new Promise((resolve) => setTimeout(resolve, 500));
          if (document.body.innerText.includes('OpenJIA interaction test')) throw new Error('item delete failed');
          return document.documentElement.outerHTML;
        })()`,
        awaitPromise: true,
        returnByValue: true,
      });
      if (interactionResult.exceptionDetails) {
        throw new Error(interactionResult.exceptionDetails.text || 'interaction evaluation failed');
      }
      writeFileSync('test-results/crud-interactions.html', interactionResult.result?.value || '');
      writeFileSync('test-results/crud-interactions.txt', 'crud add optional-complete persist refresh delete interaction e2e passed');
      console.log('CRUD interaction E2E passed: add, optional complete, persist, refresh, delete.');
    } else {
      writeFileSync('test-results/page-smoke.txt', 'generic browser smoke passed');
      console.log('Generic browser smoke passed.');
    }
  } finally {
    cdp.socket?.close();
    chrome.kill();
    server.kill();
    cleanupChromeProfile();
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




