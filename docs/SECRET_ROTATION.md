# Secret Rotation Runbook

This project has, at various points, kept live credentials in files that are
tracked by git. This runbook explains what was exposed, what has already been
rotated, and what **you** still need to rotate at each provider.

> ⚠️ **Rule of thumb:** anything that was ever committed to git must be treated
> as compromised. Removing the file from the working tree is **not** enough —
> it still exists in history until you purge it (see step 5).

---

## 1. What was exposed

| Secret | Where it leaked | Rotated here? |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | `.env` (git-ignored, but shared in plaintext) | ✅ Rotated in local `.env` |
| PostgreSQL password | `.env` (git-ignored) | ❌ Rotate at DB (step 3) |
| Tigris access/secret keys | `.env` (git-ignored) | ❌ Rotate at Tigris (step 4) |
| OpenAI API key | `.env` **and** a partial key inside `qs_ai_db_local.sql` which **was committed** | ❌ Rotate at OpenAI (step 4) |
| User password hashes + emails | `qs_ai_db_local.sql` (**committed**) | ❌ Purge from history (step 5) |

The committed `qs_ai_db_local.sql` dump is the most serious: it contained real
`users_user` rows (PBKDF2 password hashes, email addresses) and an error string
embedding a partial OpenAI key. It has been removed from tracking and added to
`.gitignore`, but it remains in git **history**.

---

## 2. Generate a new Django secret key (already done locally)

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

The freshly generated value has already been written to your local `.env`.
For every deployed environment, set it as a Fly secret:

```bash
fly secrets set DJANGO_SECRET_KEY="<new-value>" --app qs-ai-api
fly secrets set DJANGO_SECRET_KEY="<new-value>" --app qs-ai-worker
fly secrets set DJANGO_SECRET_KEY="<new-value>" --app qs-ai-flower
```

Rotating this invalidates all existing sessions and password-reset tokens —
users simply need to log in again.

---

## 3. Rotate the PostgreSQL password

The app reads `POSTGRES_PASSWORD` from the environment. To rotate:

1. Connect as an admin and run:
   ```sql
   ALTER USER qs_ai_user WITH PASSWORD '<new-strong-password>';
   ```
2. Update the password in `.env` locally.
3. Update it on every Fly app:
   ```bash
   fly secrets set POSTGRES_PASSWORD="<new-strong-password>" --app qs-ai-api
   fly secrets set POSTGRES_PASSWORD="<new-strong-password>" --app qs-ai-worker
   ```

---

## 4. Rotate provider API keys

### OpenAI
1. Go to <https://platform.openai.com/account/api-keys>.
2. **Revoke** the old key(s) — including the partial one visible in the old SQL
   dump, if it matches a real key you still hold.
3. Create a new key and set it everywhere:
   ```bash
   fly secrets set OPENAI_API_KEY="sk-proj-..." --app qs-ai-api
   fly secrets set OPENAI_API_KEY="sk-proj-..." --app qs-ai-worker
   ```

### Tigris object storage
1. In the Tigris dashboard, create a **new** access key pair and disable the
   old pair.
2. Update `TIGRIS_ACCESS_KEY` / `TIGRIS_SECRET_KEY` on all apps:
   ```bash
   fly secrets set TIGRIS_ACCESS_KEY="tid_..." TIGRIS_SECRET_KEY="tsec_..." --app qs-ai-api
   fly secrets set TIGRIS_ACCESS_KEY="tid_..." TIGRIS_SECRET_KEY="tsec_..." --app qs-ai-worker
   ```

---

## 5. Purge the leaked SQL dump from git history

`qs_ai_db_local.sql` has been removed from the index and added to
`.gitignore`, so it will not be committed again. To erase it from **history**
and force-push:

```bash
# Option A — git filter-repo (recommended; install from https://github.com/newren/git-filter-repo)
git filter-repo -- invert --path qs_ai_db_local.sql

# Option B — BFG Repo-Cleaner
bfg --delete-files qs_ai_db_local.sql
git reflog expire --expire=now --all && git gc --prune=now --aggressive

git push origin --force --all
```

> Because force-pushing rewrites shared history, coordinate with anyone else
> who has cloned the repo. After purging, every exposed credential above must
> be considered public and rotated regardless.

---

## 6. Prevent recurrence

- `.env` is git-ignored — never `git add -f` it.
- Commit only `.env.example` (no real values) as the template.
- Store production values exclusively in `fly secrets`, never in `fly.toml`
  or the image.
- Consider adding a pre-commit secret scanner (e.g. `gitleaks`,
  `detect-secrets`) to CI to catch accidental commits.
