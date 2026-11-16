# Working with teammates

The owner can invite teammates from the GitHub repository's **Settings →
Collaborators → Add people**. Enter each teammate's GitHub username and have them
accept the invitation. Public visibility allows reading; it does not grant push
access. GitHub access is separate from application accounts.

Clone the repository, create a branch such as `feature/alert-filters`, make a
focused change, and open a pull request into `main`. Describe the resulting
behavior and relevant validation. Avoid pushing directly to `main`.

The owner can protect `main` under **Settings → Rules → Rulesets**: require a pull
request, one teammate approval, and the `backend`, `frontend`, and
`deployment-and-browser` checks after those check names have appeared. Prevent
force pushes and deletion. Do not require reviews before a second maintainer is
available if it would prevent all changes.

Use Python 3.12, Node 22, and a separate disposable PostgreSQL database beginning
with `zuka_test_` for backend tests. Run `python -m pytest -q`, and in `frontend`
run `npm ci`, `npm run lint`, `npm run build`, and `npm audit --audit-level=low`.
CI also builds/runs Docker and exercises desktop/mobile UI workflows. Never run
the test suite against a database containing real user records.

Keep `.env`, database URLs, model-provider keys, SMTP credentials, local account
databases, and generated indexes out of commits. Use hosting secret settings and
GitHub Actions secrets where needed. Do not commit the generated `model.ubj`;
the container builds it from the included compressed source model.

No project-wide open-source license has been selected by the owner. Public
visibility alone does not grant a general redistribution license. Check dataset
and model usage terms before redistribution.
