# Troubleshooting

Common issues and solutions for DClaw Flow.

## Quick Diagnostics

```bash
# Check app pods
kubectl get pods -n dclaw-flow

# Check logs
kubectl logs -n dclaw-flow deployment/dclaw-flow-backend

# Check database
kubectl get clusters -n dclaw-flow
```

## Sections

- [Common Issues](./common-issues)
- [FAQ](./faq)
