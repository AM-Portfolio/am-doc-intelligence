# Gmail OAuth Setup (Email Extractor)

## Architecture (Keycloak vs Gmail)

| Layer | Who | Purpose |
|-------|-----|---------|
| **AM login JWT** | Keycloak (Google IdP broker optional) | User signs into Asrax; UI calls `/api/v1/gmail/connect` with Bearer JWT |
| **Gmail mailbox OAuth** | **Direct Google OAuth** (`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`) | Read-only Gmail scopes for statement attachments |

Email Extractor does **not** broker Gmail through Keycloak. Keycloak only authenticates the AM user to the API.

Cluster credentials use the **same shared Asrax Web OAuth client** as Keycloak / modern-ui / n8n (GCP project `am-asrax`). CSI loads `GOOGLE_*` from Vault `apps/data/{env}/services/am-identity` (google secret path).

## Broker mail filters (runtime)

Sender / subject / attachments are **not** hardcoded for ops changes.  
See [BROKER_MAIL_FILTERS.md](./BROKER_MAIL_FILTERS.md) — Vault key `GMAIL_BROKER_PATTERNS_JSON`, then restart the pod.

## Cluster redirect URIs (required)

On the shared Web client in [Google Cloud Console → Auth Platform → Clients](https://console.cloud.google.com/auth/clients?project=am-asrax) (sign in as `admin@asrax.in`), add these **Authorized redirect URIs**:

- `https://am-dev.asrax.in/email/api/v1/gmail/callback`
- `https://am-preprod.asrax.in/email/api/v1/gmail/callback`
- `https://am.asrax.in/email/api/v1/gmail/callback`

Set `GMAIL_REDIRECT_URI` under Helm **`env:`** (not `config.app` — universal-chart only injects `Values.env`).

> **Note:** Classic Console OAuth clients (`*.apps.googleusercontent.com`) cannot be updated via `gcloud` / Google Cloud MCP. Use the Console UI (or the helper below). Workforce IAM `gcloud iam oauth-clients` is a different product and does not manage this Web client.

**Preferred (agent / amctl MCP — no ask gate):**

```bash
am ai install
am ai mcp-sync --ide cursor --host-launchers
# one-time as admin@asrax.in (persistent Chrome profile):
%USERPROFILE%\.asrax\bin\google-oauth-mcp.cmd auth
```

Then agents call `google_oauth_ensure_email_extractor` (Vault `GOOGLE_*` sync + redirect URIs).  
For the unverified-app removal checklist + Console deep links: `google_oauth_verification_checklist`.

Legacy helper:

```bash
node services/am-email-extractor/scripts/ensure_gmail_google_redirects.mjs
```

Local pointer (never commit): `~/.asrax/secrets/n8n-google-oauth-web.json`.

## Prerequisites

- Gmail API enabled on `am-asrax` (verify: `gcloud services list --enabled --project=am-asrax --filter=config.name:gmail.googleapis.com`)
- OAuth consent screen includes Gmail readonly (+ openid / email / profile)
- If consent screen is in **Testing**, add the mailbox user (e.g. `asraxtech@gmail.com`) as a test user

## Remove “unverified / unsafe” for public users (Google verification)

`gmail.readonly` is a **sensitive** scope. Until Google verifies the OAuth app on project `am-asrax`, users see “Google hasn’t verified this app” / “Go to asrax.in (unsafe)”. **App code cannot remove that screen** — only Console verification does ([Unverified apps](https://support.google.com/cloud/answer/7454865), [sensitive scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification)).

As `admin@asrax.in` → [Auth Platform / OAuth consent](https://console.cloud.google.com/auth/overview?project=am-asrax):

1. **Branding**
   - App name: `asrax.in`
   - Support email: `admin@asrax.in`
   - Authorized domain: `asrax.in`
   - Privacy Policy: `https://am.asrax.in/privacy-policy.html` (confirmed HTTPS 200)
   - Terms of Service: `https://am.asrax.in/terms-of-service.html` (confirmed HTTPS 200)
2. **Scopes** (match code in `gmail_integration.py`):
   - `https://www.googleapis.com/auth/gmail.readonly`
   - openid / `userinfo.email` / `userinfo.profile`
3. **Publish** consent from Testing → **In production** (required to submit).
4. **Submit verification**
   - Justification: “Read-only Gmail to find broker statement attachments and extract portfolio holdings; no send/modify/delete.”
   - Unlisted YouTube demo (English): login → Email Extractor → Authenticate Google Mail → full consent → connected → extract holdings.
   - Homepage / app links on `asrax.in`; respond to Google review email on project owners.
5. **Until approved** — do not market Gmail connect as polished public UX. Testers: Advanced → continue, or Testing + test-user allowlist. UI copy warns users that the Google warning is expected until review finishes.

## Token storage note

After OAuth callback, Gmail credentials are stored server-side in Mongo (`user_tokens`) via `Database.save_user_token` so users do not re-consent every visit. Module `database.get_db()` must return the **`Database` helper** (`db_instance`), not the raw pymongo database — otherwise callback fails with `Collection object is not callable` / missing `save_user_token`.

## Local / legacy development

For the legacy Flask UI (`app.py` on port 5000):

1. Use the same Web client or a separate one
2. Authorized redirect URIs:
   - `http://localhost:5000/gmail/callback`
   - `http://127.0.0.1:5000/gmail/callback`
3. Set in `.env` (never commit):

```
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=...
SESSION_SECRET=...
```

API mode (`app_api.py`) defaults to `http://localhost:8080/api/v1/gmail/callback` unless `GMAIL_REDIRECT_URI` is set.

## Verify on am-dev

1. Confirm pod env `GOOGLE_CLIENT_ID` ends with `.apps.googleusercontent.com` (not `*-fleet-google-client-id`)
2. Open Doc Intelligence → Email Extractor → **Authenticate Google Mail**
3. Complete Google consent in the popup → you should return to `/app/doc-intel/email-extractor` (not stay on a JSON callback URL). Do **not** reload the Google callback URL (the `code=` is one-time).
4. Enter PAN (PDF password) → pick a broker → extract

Env: `GMAIL_REDIRECT_URI` (Google callback) and `GMAIL_UI_SUCCESS_URL` (where the browser lands after success, e.g. `https://am-dev.asrax.in/app/doc-intel/email-extractor`).

## Troubleshooting

| Error | Cause | Fix |
|-------|--------|-----|
| `401: invalid_client` / OAuth client was not found | Fleet placeholder `GOOGLE_CLIENT_ID` in Vault / CSI | Use real Web client from `am-identity` Vault path; restart pod |
| `redirect_uri_mismatch` with `localhost:8080` | Pod missing `GMAIL_REDIRECT_URI` (falls back to localhost) | Put URI under Helm `env:`; restart/roll pod |
| `redirect_uri_mismatch` with cluster URL | Callback not on the Web client | Add cluster redirect URIs above in Console |
| `Collection` / `save_user_token` not callable | `get_db()` returned pymongo DB instead of helper | Deploy image with `get_db()` → `db_instance` |
| Gmail credentials not found | Env vars missing | Check Vault CSI `google` path and mappings |
| Access blocked / app not verified | Consent Testing + user not allowlisted | Add test user or publish consent |
| Unverified / “unsafe” Google screen | Sensitive scope without Google verification | Complete branding + submit verification (section above) |

## Security

- Never commit client secrets or `.env`
- Prefer Vault CSI over long-lived local secrets for cluster deploys
- Scopes: `gmail.readonly`, `userinfo.profile`, `userinfo.email`, `openid`

## References

- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API](https://developers.google.com/gmail/api/guides)
- n8n shared-client notes: `am-n8n-workflows/docs/AUTH.md`
