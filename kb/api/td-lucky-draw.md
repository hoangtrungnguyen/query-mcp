# TD Lucky Draw — Campaign Management API

Endpoints for the term-deposit lucky draw campaign (`td-lucky-draw`), campaign code
`TRUNGVANG_LUCKYDRAW_2026_SEASON_2`.

Source: Bruno collection `lucky-draw-vang`.

Common:
- Base path: `{{URL}}/api/campaign-management/v1`
- Auth: `GTW-Authorization: $GTW_TOKEN` (gateway token) on non-admin endpoints
- Admin endpoints run against the service directly (e.g. `http://localhost:8084`)

## Get lucky codes by CIF, grouped by account

`GET /campaigns/td-lucky-draw/get-codes-by-account`

Returns all lucky codes for the authenticated customer (CIF from token), grouped per account.

```bash
curl -s -X GET \
  "$URL/api/campaign-management/v1/campaigns/td-lucky-draw/get-codes-by-account?campaignCode=TRUNGVANG_LUCKYDRAW_2026_SEASON_2" \
  -H "Content-Type: application/json" \
  -H "GTW-Authorization: $GTW_TOKEN"
```

Query params:
- `campaignCode` (required) — e.g. `TRUNGVANG_LUCKYDRAW_2026_SEASON_2`

## Get lucky code detail for one account

`GET /campaigns/td-lucky-draw/get-codes-by-account/{accountId}`

Same as above, scoped to a single TD account id (e.g. `T260009746`).

```bash
curl -s -X GET \
  "$URL/api/campaign-management/v1/campaigns/td-lucky-draw/get-codes-by-account/<TD_ACCOUNT_ID>?campaignCode=TRUNGVANG_LUCKYDRAW_2026_SEASON_2" \
  -H "content-type: application/json" \
  -H "gtw-authorization: $GTW_TOKEN"
```

Path params:
- `accountId` — TD account id, format like `T260009746`

## Manually add codes for an account (admin)

`POST /admin/campaigns/td-lucky-draw/create-codes`

Manually issues lucky codes for a TD account — used for testing / backfill. No gateway
token; call the service directly.

```bash
curl -s -X POST \
  "http://localhost:8084/api/campaign-management/v1/admin/campaigns/td-lucky-draw/create-codes" \
  -H "Content-Type: application/json" \
  -d '{
    "requestId": "REQ-TEST-01",
    "accountId": "<TD_ACCOUNT_ID>",
    "principal": 100000000,
    "tenorAmount": 6,
    "tenorUnit": "MONTH",
    "acquisitionChannel": "ONLINE"
  }'
```

Body fields:
- `requestId` — idempotency key for the manual request
- `accountId` — target TD account
- `principal` — deposit principal in VND (e.g. `100000000`)
- `tenorAmount` + `tenorUnit` — deposit term (e.g. `6` + `MONTH`)
- `acquisitionChannel` — `ONLINE` | branch channels
