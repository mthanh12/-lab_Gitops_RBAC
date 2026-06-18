# Part 2 - Sigstore Policy

## Files

- `cluster-image-policy.yaml`: require signed image for `ghcr.io/nguyentoan02/w10-api*`

## Before apply

1. Generate `cosign.key` and `cosign.pub`
2. Verify `cluster-image-policy.yaml` contains the real public key
3. Install Sigstore Policy Controller in cluster
4. Only then create or rename the ArgoCD app manifest for `k8s-policies/`

## Why not auto-apply immediately

This repo keeps the policy manifest separate so the cluster does not break before:

- image is signed in CI
- public key is real
- policy controller CRD exists
