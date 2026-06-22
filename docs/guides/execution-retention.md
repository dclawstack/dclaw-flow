# Execution History Retention (P0.4)

Execution history is retained for `EXECUTION_RETENTION_DAYS` (default **90**).
Cleanup is **not** automatic — there is no in-cluster scheduler — so trigger it
with the admin endpoint on a cron/`CronJob`.

## Endpoint

```
POST /api/v1/flows/executions/admin/cleanup?days=90
Header: X-Admin-Token: <ADMIN_TOKEN>
```

Deletes executions whose `started_at` is older than `days` (and their step
logs, via `ON DELETE CASCADE`). Returns `{"deleted": <count>}`. Without a valid
`X-Admin-Token` it returns `401`. Omit `days` to use `EXECUTION_RETENTION_DAYS`.

## Example: daily crontab

```cron
# 03:15 daily — purge executions older than the retention window
15 3 * * * curl -fsS -X POST \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  "http://localhost:8088/api/v1/flows/executions/admin/cleanup"
```

## Example: Kubernetes CronJob (sketch)

```yaml
apiVersion: batch/v1
kind: CronJob
metadata: { name: flow-retention }
spec:
  schedule: "15 3 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: cleanup
              image: curlimages/curl
              args:
                - -fsS
                - -X
                - POST
                - -H
                - "X-Admin-Token: $(ADMIN_TOKEN)"
                - "http://flow-backend:8088/api/v1/flows/executions/admin/cleanup"
              env:
                - name: ADMIN_TOKEN
                  valueFrom:
                    secretKeyRef: { name: flow-secrets, key: admin-token }
```

> A built-in scheduler (APScheduler in the FastAPI lifespan, or Temporal) is a
> P1 enhancement.
