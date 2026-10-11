# Broker Gmail mail filters (runtime)

Sender / subject / attachment filters for Email Extractor are **Vault-backed**.  
Change values → restart the pod. No code deploy required for filter tweaks.

## Vault

| Item | Value |
|------|--------|
| Path | `apps/data/{env}/services/am-email-extractor` |
| Key | `GMAIL_BROKER_PATTERNS_JSON` |
| CSI env | `GMAIL_BROKER_PATTERNS_JSON` (see `helm/vault-mappings.yaml` → `service-oauth`) |

`{env}` = `dev` \| `preprod` \| `prod`.

## JSON shape

Object keyed by broker API id (`groww`, `zerodha`, `angleone`, `dhan`, `mstock`):

```json
{
  "dhan": {
    "from": "statements@dhan.co",
    "subject": "Demat Holding Summary",
    "file_pattern": [".pdf", ".xlsx", ".xls"]
  }
}
```

| Field | Meaning |
|-------|---------|
| `from` | Gmail `from:` query (address or domain) |
| `subject` | Gmail `subject:"…"` (primary); if 0 hits, search retries without subject |
| `file_pattern` | List of extensions to download (string still accepted) |

Code defaults in `gmail_integration.py` apply when the Vault key is missing or invalid. Vault values **merge over** defaults per broker.

## Current filters (seed)

| Broker | from | subject | files | PDF password |
|--------|------|---------|-------|--------------|
| Groww | `groww.in` | Holding Statement | PDF | PAN |
| Zerodha | `zerodha.net` | Holding Statement | PDF | PAN |
| AngelOne | `angelone.in` | Holdings | Excel | none |
| Dhan | `statements@dhan.co` | Demat Holding Summary | PDF + spreadsheet | PAN |
| Mstock | `mstock.com` | TRANSACTION STATEMENT | PDF | PAN |

**Dhan primary query:**  
`from:statements@dhan.co has:attachment after:{YYYY/MM/DD} subject:"Demat Holding Summary"`

Extract prefers the **PDF** when both PDF and spreadsheet are present; spreadsheet is still downloaded.

## Patch + restart

Example (dev) — merge one key without wiping other secrets:

```bash
# After loading VAULT_ADDR / VAULT_TOKEN (e.g. ~/.asrax)
python services/am-email-extractor/scripts/seed_broker_mail_filters_vault.py --envs dev,preprod,prod
kubectl --kubeconfig ~/.asrax/kubeconfig.dev -n am-apps-dev \
  rollout restart deploy/am-email-extractor-dev
```

Or patch JSON manually with Vault UI / `vault kv patch`, then rollout restart.

## Related

- OAuth / redirect URIs: [GMAIL_OAUTH_SETUP.md](./GMAIL_OAUTH_SETUP.md)
- Probe (JWT): `GET /api/v1/gmail/mailbox-probe?brokers=dhan&days=365`
- Extract (JWT): `GET /api/v1/extract/gmail/dhan?pan=YOURPAN`
