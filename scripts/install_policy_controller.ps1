$ErrorActionPreference = "Stop"

$env:HTTP_PROXY = $null
$env:HTTPS_PROXY = $null

kubectl create namespace cosign-system --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -k github.com/sigstore/policy-controller/config?ref=main

Write-Host "Policy Controller install command submitted."
