"""Real-browser smoke test (Playwright driving the system Microsoft Edge).

Needs: backend on :8000 (seeded, with ADMIN e2e_admin / e2e-admin-pass), `vite preview` on :4173, internet for Judge0.
  python e2e/browser_check.py [screenshot_dir]
"""
import random
import sys
import time
from pathlib import Path

import httpx
from playwright.sync_api import expect, sync_playwright

BASE = "http://localhost:4173"
SHOTS = Path(sys.argv[1] if len(sys.argv) > 1 else "e2e/shots")
SHOTS.mkdir(parents=True, exist_ok=True)
PY_OK = "a, b = map(int, input().split())\nprint(a + b)\n"
PY_WRONG = "a, b = map(int, input().split())\nprint(a - b)\n"
results, problems = [], []


def check(name, fn):
    t0 = time.time()
    try:
        fn()
        results.append((name, "PASS", f"{time.time() - t0:.1f}s"))
    except Exception as e:  # noqa: BLE001
        results.append((name, "FAIL", f"{type(e).__name__}: {str(e).splitlines()[0][:160]}"))


def wait_up(url):
    for _ in range(60):
        try:
            httpx.get(url, timeout=2)
            return
        except httpx.HTTPError:
            time.sleep(1)
    raise SystemExit(f"{url} is not up")


def main():
    wait_up("http://127.0.0.1:8000/api/auth/me")
    wait_up(BASE)
    user = f"e2e_{random.randint(10000, 99999)}"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="dark")
        page = ctx.new_page()
        # The browser logs every 4xx as a console error; judge them by URL instead, allowing only the ones this
        # script provokes on purpose (logged-out /me, bad registration, wrong password).
        expected = {("/api/auth/me", 401), ("/api/auth/register", 400), ("/api/auth/login", 401)}
        page.on("console", lambda m: problems.append(f"console.{m.type}: {m.text}")
                if m.type == "error" and "Failed to load resource" not in m.text else None)
        page.on("response", lambda r: problems.append(f"HTTP {r.status} {r.url}")
                if r.status >= 400 and (r.url.replace(BASE, "").split("?")[0], r.status) not in expected else None)
        page.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
        editor = page.locator(".editor textarea")

        def login_redirect():
            page.goto(BASE + "/")
            expect(page).to_have_url(BASE + "/login")
            expect(page.locator("canvas.particles")).to_have_count(1)
            page.screenshot(path=SHOTS / "01-login.png")
        check("anonymous user is sent to /login; particle canvas present", login_redirect)

        def register():
            page.click("text=Create an account")
            expect(page).to_have_url(BASE + "/register")
            page.fill("input[autocomplete=username]", "x y")
            page.fill("input[type=password]", "password123")
            page.click("button[type=submit]")
            expect(page.locator(".err")).to_contain_text("Username")
            page.fill("input[autocomplete=username]", user)
            page.click("button[type=submit]")
            expect(page).to_have_url(BASE + "/")
            expect(page.locator("table.list tbody tr")).to_have_count(51)
            page.screenshot(path=SHOTS / "02-problems.png")
        check("register (bad username rejected, then success) and see 51 problems", register)

        def filters():
            page.click(".seg >> text=Hard")
            expect(page.locator("table.list tbody tr")).to_have_count(10)
            page.click(".seg >> text=All")
            page.fill(".search", "two sum")
            expect(page.locator("table.list tbody tr")).to_have_count(1)
            page.fill(".search", "zzzz-no-match")
            expect(page.locator("table.list tbody")).to_contain_text("No problems match")
            page.fill(".search", "")
        check("difficulty filter, search and empty state", filters)

        def open_problem():
            page.click("text=A + B")
            expect(page.locator(".ptitle")).to_have_text("A + B")
            expect(page.locator(".example")).to_have_count(2)
            expect(page.locator("details.reveal")).to_have_count(2)
            page.screenshot(path=SHOTS / "03-workspace.png")
        check("open problem: statement, 2 examples, hint and complexity reveals", open_problem)

        def editor_keys():
            editor.fill("")
            editor.click()
            page.keyboard.type("if True:")
            page.keyboard.press("Enter")
            page.keyboard.type("x = 1")
            assert editor.input_value() == "if True:\n    x = 1", repr(editor.input_value())
            page.keyboard.press("Home")
            page.keyboard.press("Shift+Tab")
            assert editor.input_value() == "if True:\nx = 1", repr(editor.input_value())
            page.keyboard.press("Tab")
            assert editor.input_value().startswith("if True:\n    "), repr(editor.input_value())
            expect(page.locator(".gutter div")).to_have_count(2)
        check("editor: auto-indent, Tab, Shift+Tab, line numbers", editor_keys)

        def run_samples():
            editor.fill(PY_OK)
            page.click(".action-bar >> text=Run")
            expect(page.locator(".result-head .big")).to_have_text("Accepted", timeout=120000)
            expect(page.locator(".result-head")).to_contain_text("2/2 examples passed")
            page.screenshot(path=SHOTS / "04-run-accepted.png")
        check("Run on examples -> Accepted 2/2", run_samples)

        def run_wrong():
            editor.fill(PY_WRONG)
            page.keyboard.press("Control+Enter") if False else page.click(".action-bar >> text=Run")
            expect(page.locator(".result-head .big")).to_have_text("Wrong Answer", timeout=120000)
            expect(page.locator(".case.fail")).to_have_count(2)
            expect(page.locator("pre.out.bad")).to_have_text("-1")
            page.screenshot(path=SHOTS / "05-run-wrong.png")
        check("Run wrong code -> Wrong Answer, per-case output shown", run_wrong)

        def run_custom():
            editor.fill(PY_OK)
            page.click(".console-tabs >> text=Testcase")
            page.click("text=Custom input")
            page.fill(".custom-input", "40 2\n")
            editor.click()
            page.keyboard.press("Control+Enter")
            expect(page.locator(".result-head .big")).to_have_text("Finished", timeout=120000)
            expect(page.locator("pre.out").first).to_have_text("42")
            page.click(".console-tabs >> text=Testcase")
            page.click(".cases >> text=Case 1")
        check("Ctrl+Enter runs with custom input -> prints 42", run_custom)

        def submit_ac():
            editor.fill(PY_OK)
            page.fill("input[aria-label='Your time complexity']", "O(1)")
            page.fill("input[aria-label='Your space complexity']", "O(1)")
            page.click(".action-bar >> text=Submit")
            expect(page.locator(".result-head .big")).to_have_text("Accepted", timeout=180000)
            expect(page.locator(".result-head")).to_contain_text("5 / 5 tests passed")
            expect(page.locator(".meter")).to_have_count(2)
            expect(page.locator(".strip .tick")).to_have_count(5)
            expect(page.locator(".complexity")).to_contain_text("Intended solution")
            expect(page.locator(".meta")).to_contain_text("Solved")
            page.screenshot(path=SHOTS / "06-submit-accepted.png")
        check("Submit -> Accepted, 5/5, runtime/memory meters, per-test strip, complexity", submit_ac)

        def submit_wa():
            editor.fill(PY_WRONG)
            page.click(".action-bar >> text=Submit")
            expect(page.locator(".result-head .big")).to_have_text("Wrong Answer", timeout=180000)
            expect(page.locator(".result-head")).to_contain_text("0 / 5 tests passed")
            expect(page.locator(".console-body")).to_contain_text("Wrong answer on test 1")
            expect(page.locator(".console-body")).not_to_contain_text("2000000000")
            page.screenshot(path=SHOTS / "07-submit-wrong.png")
        check("Submit wrong -> WA on test 1, hidden data not shown", submit_wa)

        def cpp_ce_and_draft():
            page.select_option(".code-bar select", "cpp")
            assert "#include" in editor.input_value()
            editor.fill("int main() { return x; }\n")
            page.click(".action-bar >> text=Run")
            expect(page.locator(".result-head .big")).to_have_text("Compilation Error", timeout=120000)
            expect(page.locator("pre.err-out")).to_contain_text("error")
            page.screenshot(path=SHOTS / "08-compile-error.png")
            page.reload()
            expect(page.locator(".code-bar select")).to_have_value("cpp")
            assert editor.input_value() == "int main() { return x; }\n"
            page.select_option(".code-bar select", "python")
            assert editor.input_value() == PY_WRONG
        check("C++ compile error shown; drafts persist per language across reload", cpp_ce_and_draft)

        def submissions_page():
            page.click("nav >> text=Submissions")
            rows = page.locator("table.list tbody tr")
            expect(rows).to_have_count(2)
            expect(rows.nth(0)).to_contain_text("Wrong Answer")
            expect(rows.nth(1)).to_contain_text("Accepted")
            expect(rows.nth(1)).to_contain_text("O(1) · O(1)")
            page.screenshot(path=SHOTS / "09-submissions.png")
        check("Submissions page lists both, newest first, with stated complexity", submissions_page)

        def leaderboard():
            page.click("nav >> text=Leaderboard")
            me = page.locator("tr.me")
            expect(me).to_contain_text(user)
            expect(me).to_contain_text("you")
            page.screenshot(path=SHOTS / "10-leaderboard.png")
        check("Leaderboard highlights the current user", leaderboard)

        def solved_mark():
            page.click("nav >> text=Problems")
            expect(page.locator("tr", has_text="A + B").locator("svg.check")).to_have_count(1)
        check("Solved checkmark appears in problem list", solved_mark)

        def participant_no_admin():
            page.goto(BASE + "/admin")
            expect(page).to_have_url(BASE + "/")
            expect(page.locator("nav >> text=Admin")).to_have_count(0)
        check("participant cannot open /admin", participant_no_admin)

        def logout():
            page.click("text=Log out")
            expect(page).to_have_url(BASE + "/login")
            page.goto(BASE + "/submissions")
            expect(page).to_have_url(BASE + "/login")
        check("logout, then protected pages redirect to login", logout)

        def admin():
            page.fill("input[autocomplete=username]", "e2e_admin")
            page.fill("input[type=password]", "wrong-password")
            page.click("button[type=submit]")
            expect(page.locator(".err")).to_contain_text("Invalid")
            page.fill("input[type=password]", "e2e-admin-pass")
            page.click("button[type=submit]")
            page.click("nav >> text=Admin")
            expect(page.locator(".admin-list tbody tr")).to_have_count(51)
            page.click(".admin-list tr:has-text('Two Sum') >> text=Edit")
            expect(page.locator(".form h2")).to_contain_text("Edit problem")
            page.screenshot(path=SHOTS / "11-admin.png")
        check("admin login (wrong password first) and admin page", admin)

        ctx.close()

        light = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="light")
        lp = light.new_page()
        lp.on("pageerror", lambda e: problems.append(f"pageerror(light): {e}"))

        def light_mode():
            lp.goto(BASE + "/login")
            lp.fill("input[autocomplete=username]", user)
            lp.fill("input[type=password]", "password123")
            lp.click("button[type=submit]")
            expect(lp).to_have_url(BASE + "/")
            lp.screenshot(path=SHOTS / "12-light-problems.png")
            lp.click("text=Two Sum")
            expect(lp.locator(".ptitle")).to_have_text("Two Sum")
            lp.screenshot(path=SHOTS / "13-light-workspace.png")
        check("light colour scheme renders", light_mode)
        light.close()

        mobile = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme="dark",
                                     reduced_motion="reduce", is_mobile=True, has_touch=True)
        mp = mobile.new_page()
        mp.on("pageerror", lambda e: problems.append(f"pageerror(mobile): {e}"))

        def mobile_view():
            mp.goto(BASE + "/login")
            mp.fill("input[autocomplete=username]", user)
            mp.fill("input[type=password]", "password123")
            mp.click("button[type=submit]")
            expect(mp).to_have_url(BASE + "/")
            mp.screenshot(path=SHOTS / "14-mobile-problems.png", full_page=True)
            overflow = mp.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            assert overflow <= 1, f"horizontal overflow {overflow}px"
            mp.goto(BASE + "/problems/1")
            expect(mp.locator(".ptitle")).to_have_text("A + B")
            mp.screenshot(path=SHOTS / "15-mobile-workspace.png", full_page=True)
            overflow = mp.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            assert overflow <= 1, f"horizontal overflow {overflow}px"
        check("mobile 390px with reduced motion: no horizontal overflow", mobile_view)
        mobile.close()
        browser.close()

    width = max(len(n) for n, _, _ in results)
    for n, s, d in results:
        print(f"{s}  {n.ljust(width)}  {d}")
    print(f"\n{sum(s == 'PASS' for _, s, _ in results)}/{len(results)} passed")
    print("browser errors:", problems or "none")
    sys.exit(0 if all(s == "PASS" for _, s, _ in results) and not problems else 1)


if __name__ == "__main__":
    main()
