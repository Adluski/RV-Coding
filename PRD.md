# PRD — Hosted Online Coding Judge MVP

Build a small, hosted online coding judge for a class project. The repository is currently empty. Work in this repository’s `main` branch.

## Deadline and priorities

Hard deadline: **2:30 PM Asia/Kolkata today**. Work autonomously: inspect the repository, choose simple implementation details, and do not pause for preference questions. If a missing account, credential, or interactive sign-in blocks deployment, finish the code and give the exact blocker and next step.

Prioritize this order:

1. A working hosted end-to-end submission flow.
2. Sample/hidden test separation and correct verdicts.
3. User history and leaderboard.
4. Minimal admin problem creation.
5. README and a bounded concurrency check if time remains.

Do not spend time on the quiz, local/offline mode, Docker runner, contests, syntax highlighting, custom output comparison, or visual polish.

## Product and users

- **Admin:** sign in, create/edit and publish problems with sample and hidden tests.
- **Participant:** register and sign in, view published problems and samples, submit Python 3 or C++17 code, see verdicts, view own submission history, and compare scores on the leaderboard.
- **Anonymous:** register or sign in only.

## Intended stack

Use FastAPI, SQLAlchemy, Neon Postgres, React/Vite, Vercel, and hosted Judge0 CE. Keep API routes under `/api`. Use same-origin API calls in production. Do not implement a code sandbox; Judge0 is responsible for isolated code execution.

If the intended hosting setup is blocked by missing credentials or sign-in, finish the app and document the blocker. Do not claim the project is deployed unless you have a live URL and have checked it.

## Minimum data

Create models for:

- Users: username, password hash, role.
- Problems: title, statement, time limit, memory limit, published state.
- Test cases: problem, input, expected output, sample/hidden flag, position.
- Submissions: owner, problem, language, source code, pending/done status, verdict, failed test position, runtime/memory, Judge0 tokens, timestamp.

Use an idempotent seed script to create an admin from environment variables and at least one usable problem with sample and hidden tests.

## Authentication and access rules

- Registration creates participant accounts only.
- Hash passwords with bcrypt.
- Create the initial admin through seed environment variables; there must be no public admin registration.
- Use an httpOnly, SameSite=Lax cookie for authentication; use Secure cookies in production.
- Enforce role and ownership checks in the backend.
- A participant can read only their own submission details and history.
- Never return hidden test input or expected output from participant endpoints.
- Do not log passwords, submitted source code, or hidden test contents.
- Limit submitted source code to 64 KB.

## API needed by the frontend

Implement these endpoints with JSON responses:

- `POST /api/auth/register` and `POST /api/auth/login`: accept `{username, password}`, set the login cookie, return `{username, role}`.
- `POST /api/auth/logout`; `GET /api/auth/me`.
- `GET /api/problems`: published problems with `id`, `title`, and whether the current participant has solved each.
- `GET /api/problems/{id}`: problem details and sample tests only.
- `POST /api/submissions`: accept `{problem_id, language, source_code}`, return `{id}` promptly.
- `GET /api/submissions/{id}`: owner/admin only; return `id`, `status`, `verdict`, `failed_test`, `runtime_ms`, `memory_kb`, and a short message where appropriate.
- `GET /api/submissions`: current user’s history, newest first.
- `GET /api/leaderboard`: participant rankings with `rank`, `username`, `solved`, and `wrong`.
- `GET /api/admin/problems`, `POST /api/admin/problems`, and `PUT /api/admin/problems/{id}`: admin-only problem management. A simple form that accepts test cases as JSON is enough.

Use `{ "error": "message" }` for API errors.

## Submission and verdict behavior

- Accept only `python` and `cpp`.
- Submit each problem’s tests to Judge0 asynchronously. Return the app submission ID without waiting for execution.
- Store Judge0 tokens and poll them from `GET /api/submissions/{id}`. The browser will poll every two seconds until the status is done.
- Use Judge0’s expected-output comparison; do not implement a custom comparer.
- Return `AC`, `WA`, `TLE`, `RE`, `CE`, or `ERR`.
- `ERR` means the judge failed. Do not report it as the participant’s wrong answer.
- For ordinary failed tests, show only the first failing test’s position, never its input or expected output.
- If Judge0 rejects or throttles a request, show a clear error; do not invent a result or retry in a tight loop.
- Leaderboard order: solved count descending, then wrong attempts ascending, then earlier latest first-AC time. Count `WA`, `TLE`, and `RE` attempts before the first AC for solved problems. Do not count `CE` or `ERR`. Exclude admins.

## Required UI

Build plain, readable pages:

- `/login` and `/register`
- `/` problem list
- `/problems/:id` with statement, samples, language selector, code textarea, submit button, pending state, verdict, runtime, memory, and failed test number
- `/submissions` history
- `/leaderboard`
- `/admin` minimal problem/test form

Use plain CSS and no editor framework. Do not display hidden tests.

## Verification and honest limits

Check the core flow if the required services are available:

1. Register/login as a participant.
2. Sign in as admin, create or edit a problem with sample and hidden tests.
3. Confirm the participant API returns samples but no hidden tests.
4. Submit Python and C++ solutions and check the results poll to completion.
5. Check WA, TLE, RE, and CE if time and the judge service allow.
6. Check that a participant cannot read another participant’s submission.
7. Check history and leaderboard after an AC.

Persist submissions and return pending status while Judge0 processes them. Judge0’s queue handles execution; the public service may throttle requests. If time permits, run one bounded check with 20 submissions and report the actual result. Do not claim 20-user capacity, hostile-code safety, or a passed verdict check unless you actually checked it. State that code and tests are sent to the hosted Judge0 service.

## Finish

Add a README with setup, required environment variables, deployment steps, the request flow, and known limitations. Keep secrets in environment settings; never commit `.env` or real keys.

Commit the work on `main` and push it to `origin` when the implementation is ready. Report the commit, build/check results, live URL if deployed, and anything that remains incomplete.