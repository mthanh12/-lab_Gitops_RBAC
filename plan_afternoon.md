# Plan Afternoon Runbook

## Muc tieu

Tai lieu nay ghi lai cach lam va cach validate cho bai lab afternoon, de:

- review lai nhung gi da implement
- chay lai sau nay neu can
- biet ro phan nao da xong, phan nao can thao tac tay

Noi dung gom 2 phan:

- Part 1: AWS Secrets Manager + External Secrets Operator
- Part 2: Supply chain security voi Trivy + Cosign + Sigstore Policy Controller

# Part 1 - Secrets Manager + External Secrets

## Muc tieu

Hoan thanh phan 1 cua bai lab:

- Secret DB khong nam trong Git
- Secret duoc lay tu AWS Secrets Manager qua External Secrets Operator
- App doc secret qua mounted volume `/secrets/password`
- Khi secret doi tren AWS, Kubernetes secret `db-secret` cap nhat lai trong `<= 60s`
- App thay duoc secret moi ma khong can hard-code password

## File lien quan

### Manifest ESO

- `k8s-eso/secret-store.yaml`
- `k8s-eso/external-secret.yaml`
- `argocd/apps/eso.yaml`

### App va rollout

- `src/api/app.py`
- `app-api/rollout.yaml`

## Logic da duoc implement

### App

Trong `src/api/app.py`:

- Them `DB_PASSWORD_PATH`, mac dinh la `/secrets/password`
- Route `/` tra them:
  - `db_status`
  - `db_password_loaded`
- Route `/db-secret` de debug viec app co doc duoc secret hay khong

### Rollout

Trong `app-api/rollout.yaml`:

- Mount secret `db-secret` vao `/secrets`
- Set `DB_PASSWORD_PATH=/secrets/password`
- App doc password tu mounted file

### ESO

Trong `k8s-eso/`:

- `SecretStore` doc AWS Secrets Manager o region `ap-southeast-1`
- `ExternalSecret` dong bo secret `prod/db/password` thanh K8s secret `db-secret`
- `refreshInterval: 1m`

## Dieu kien truoc khi chay

Ban can co:

- Cluster dang chay
- `kubectl` dang tro dung context
- ArgoCD da chay
- External Secrets Operator da chay trong cluster
- AWS CLI co quyen voi Secrets Manager

## Cach chay Part 1

### B1 - Kiem tra cluster va ArgoCD

```powershell
kubectl get ns
kubectl get applications -n argocd
```

Ky vong:

- co namespace `demo`, `argocd`
- app `eso` ton tai

### B2 - Kiem tra controller External Secrets Operator

```powershell
kubectl get pods -A | findstr external-secrets
kubectl get crd | findstr external-secrets
```

Ky vong:

- controller external-secrets dang `Running`
- co CRD `secretstores.external-secrets.io`
- co CRD `externalsecrets.external-secrets.io`

### B3 - Tao hoac update AWS secret

Neu may co proxy loi:

```powershell
$env:HTTP_PROXY=$null
$env:HTTPS_PROXY=$null
```

Tao secret:

```powershell
aws secretsmanager create-secret `
  --name prod/db/password `
  --secret-string "MyS3cr3tP@ss" `
  --region ap-southeast-1
```

Neu da ton tai, update:

```powershell
aws secretsmanager update-secret `
  --secret-id prod/db/password `
  --secret-string "MyS3cr3tP@ss" `
  --region ap-southeast-1
```

Kiem tra:

```powershell
aws secretsmanager get-secret-value `
  --secret-id prod/db/password `
  --region ap-southeast-1 `
  --query SecretString `
  --output text
```

### B4 - Tao secret AWS credentials trong Kubernetes

```powershell
kubectl create secret generic aws-credentials `
  --namespace demo `
  --from-literal=access-key-id=YOUR_AWS_ACCESS_KEY_ID `
  --from-literal=secret-access-key=YOUR_AWS_SECRET_ACCESS_KEY
```

Kiem tra:

```powershell
kubectl get secret aws-credentials -n demo
```

### B5 - De ArgoCD sync phan ESO

```powershell
kubectl get applications -n argocd
```

Ky vong:

- `eso` la `Synced`
- `eso` la `Healthy`

## Cach validate Part 1

### Test 1 - ESO sync secret thanh cong

```powershell
kubectl get secretstore,externalsecret,secret -n demo
```

Pass khi:

- `aws-store` la `Valid`
- `db-password` la `SecretSynced`
- co `secret/db-secret`

### Test 2 - K8s secret co dung gia tri

```powershell
$b64 = kubectl get secret db-secret -n demo -o jsonpath="{.data.password}"
[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))
```

Pass khi gia tri giai ma ra dung password AWS hien tai.

### Test 3 - App doc duoc secret qua mounted file

```powershell
$pod = (kubectl get pods -n demo -l app=api -o jsonpath="{.items[0].metadata.name}")
$pod

kubectl exec -n demo $pod -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/').read().decode())"
kubectl exec -n demo $pod -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/db-secret').read().decode())"
kubectl exec -n demo $pod -- cat /secrets/password
```

Pass khi:

- `/` tra `db_password_loaded=true`
- `/` tra `db_status=connected`
- `/db-secret` tra `password_found=true`
- `cat /secrets/password` ra dung password hien tai

### Test 4 - Secret rotation trong <= 60s

```powershell
$env:HTTP_PROXY=$null
$env:HTTPS_PROXY=$null

aws secretsmanager update-secret `
  --secret-id prod/db/password `
  --secret-string "AnotherP@ss456" `
  --region ap-southeast-1

Start-Sleep -Seconds 70

$b64 = kubectl get secret db-secret -n demo -o jsonpath="{.data.password}"
[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))

$pod = (kubectl get pods -n demo -l app=api -o jsonpath="{.items[0].metadata.name}")
kubectl exec -n demo $pod -- cat /secrets/password
kubectl exec -n demo $pod -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/db-secret').read().decode())"
```

Pass khi:

- K8s secret doi sang `AnotherP@ss456`
- file `/secrets/password` trong pod doi theo
- `/db-secret` van tra `password_found=true`

## Ket qua da verify

Da verify thanh cong:

- `eso` la `Synced/Healthy`
- `SecretStore aws-store` la `Valid`
- `ExternalSecret db-password` la `SecretSynced`
- `db-secret` da duoc tao
- app doc duoc secret thanh cong
- secret rotation da hoat dong

## Tieu chi pass Part 1

Pass khi tat ca dieu kien sau dung:

- Secret plain text khong nam trong Git
- `SecretStore` va `ExternalSecret` deploy thanh cong
- `db-secret` duoc tao trong namespace `demo`
- app doc duoc secret tu `/secrets/password`
- khi AWS secret doi, K8s secret cap nhat lai trong khoang 1 phut
- app van doc duoc secret moi sau rotation

# Part 2 - Supply Chain Security

## Muc tieu

Hoan thanh phan 2 cua bai lab:

- CI build image len GHCR
- CI scan image bang Trivy va fail neu co CVE `HIGH/CRITICAL`
- CI sign image bang Cosign
- Cluster chi accept signed image thong qua Sigstore Policy Controller
- unsigned image bi reject, signed image deploy duoc

## File lien quan

### Workflow va repo

- `.github/workflows/build-push.yml`
- `.github/workflows/validate.yml`
- `.gitignore`
- `README.md`
- `runbook.md`

### Policy va ArgoCD

- `k8s-policies/cluster-image-policy.yaml`
- `k8s-policies/README.md`
- `argocd/apps/policies.yaml`
- `scripts/install_policy_controller.ps1`

### App rollout

- `app-api/rollout.yaml`

## Logic da duoc implement

### Build pipeline

Trong `.github/workflows/build-push.yml`:

- build image len GHCR
- scan image bang Trivy
- fail neu co `HIGH/CRITICAL`
- sign image bang Cosign
- update `app-api/rollout.yaml`
- commit version moi ve repo

### Sigstore policy

Trong `k8s-policies/cluster-image-policy.yaml`:

- require image `ghcr.io/nguyentoan02/w10-api*` phai co signature hop le
- verify bang public key trong `cosign.pub`

### ArgoCD

Trong `argocd/apps/policies.yaml`:

- sync policy manifests tu `k8s-policies/`

### Policy controller

Trong `scripts/install_policy_controller.ps1`:

- install Sigstore Policy Controller bang Helm vao namespace `cosign-system`

## Dieu kien truoc khi chay

Ban can co:

- repo GitHub dang dung GHCR
- GitHub Actions dang chay duoc
- cluster co the pull image tu GHCR
- `cosign` da duoc cai local
- Helm da duoc cai local

## Gia tri dang dung tren may nay

- private key local: `D:\W10\temp\cosign.key`
- public key local: `D:\W10\temp\cosign.pub`
- password Cosign:

```text
W10-Lab-Cosign-2026!
```

Luu y:

- khong commit `cosign.key`
- co the commit `cosign.pub`

## Cach chay Part 2

### B1 - Tao GitHub Secrets

Vao:

- GitHub repo
- `Settings`
- `Secrets and variables`
- `Actions`
- `Repository secrets`

Tao 2 secret:

1. `COSIGN_PRIVATE_KEY`
   - value: toan bo noi dung file `D:\W10\temp\cosign.key`
2. `COSIGN_PASSWORD`
   - value: `W10-Lab-Cosign-2026!`

Khong dung `Environment secrets`.

### B2 - Push code Part 2

Push tat ca thay doi Part 2 len branch `master`.

### B3 - Trigger workflow build-push

Workflow dang dung:

- `Build Scan Sign Push Image`

Trigger:

- push len `master`
- hoac vao tab `Actions` roi `Run workflow`

Workflow se lam:

1. checkout
2. tinh version
3. login GHCR
4. build image
5. scan Trivy
6. push image
7. resolve digest
8. install Cosign
9. sign image
10. update `app-api/rollout.yaml`
11. commit rollout moi
12. push git tag

### B4 - Cai Sigstore Policy Controller

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_policy_controller.ps1
kubectl get pods -n cosign-system
```

Pass khi:

- pod `policy-controller-webhook` la `Running`

### B5 - De ArgoCD sync app `policies`

```powershell
kubectl get applications -n argocd
```

Pass khi:

- co app `policies`
- `policies` la `Synced`
- `policies` la `Healthy`

### B6 - Xac nhan rollout cua api dung image signed tu GHCR

```powershell
kubectl get rollout api -n demo -o yaml
```

Kiem tra cac gia tri:

- `image: ghcr.io/nguyentoan02/w10-api:<version>`
- `imagePullPolicy: Always`

Neu rollout dang `Suspended`, day la do canary pause step, khong phai loi.

## Cach validate Part 2

### Test 1 - CI fail neu co CVE HIGH/CRITICAL

Sau khi push:

- vao GitHub Actions xem workflow

Pass khi:

- image sach thi workflow pass
- neu image co CVE `HIGH/CRITICAL` thi workflow fail

### Test 2 - Image duoc sign

```powershell
cosign verify --key .\cosign.pub ghcr.io/nguyentoan02/w10-api:<tag>
```

Neu `cosign` chua nhan do PATH chua refresh:

- mo PowerShell moi
- hoac dung full path toi file `cosign-windows-amd64.exe`

Pass khi:

- `cosign verify` thanh cong

### Test 3 - Policy Controller dang chay

```powershell
kubectl get pods -n cosign-system
```

Pass khi:

- pod policy controller dang `Running`

### Test 4 - ClusterImagePolicy active

```powershell
kubectl get clusterimagepolicy
kubectl get clusterimagepolicy require-signed-w10-api -o yaml
```

Pass khi:

- co policy `require-signed-w10-api`
- policy match image `ghcr.io/nguyentoan02/w10-api*`

### Test 5 - Unsigned image bi reject

```powershell
kubectl run test-unsigned --image=ghcr.io/nguyentoan02/w10-api:unsigned-test -n demo
```

Pass khi:

- webhook reject request
- thong diep loi lien quan den verify signature

### Test 6 - Signed image deploy duoc

```powershell
kubectl run test-signed --image=ghcr.io/nguyentoan02/w10-api:<tag> -n demo
```

Pass khi:

- pod duoc tao thanh cong

### Test 7 - Kiem tra app `api` sau rollout

```powershell
kubectl get pods -n demo -l app=api -o wide
kubectl get rollout -n demo api
kubectl get svc -n demo
```

Pass khi:

- pod moi cua `api` len `Running`
- service `api` van ton tai
- rollout khong con bi `ErrImageNeverPull`

## Van de da gap va cach xu ly

### Trivy action version sai

Da gap:

- `aquasecurity/trivy-action@0.24.0` khong ton tai

Da sua:

- doi sang `aquasecurity/trivy-action@v0.36.0`

### Rollout bi `ErrImageNeverPull`

Nguyen nhan:

- workflow doi image sang GHCR
- nhung rollout lai de `imagePullPolicy: Never`

Da sua:

- workflow duoc cap nhat de doi `imagePullPolicy: Always`
- live rollout tren cluster da duoc patch lai

### ArgoCD hien `Suspended`

Nguyen nhan:

- rollout dung canary strategy co pause step

Day khong phai loi neu pod moi van chay duoc.

Neu can promote nhanh:

```powershell
kubectl argo rollouts promote api -n demo
```

### `kube-prometheus-stack` van `Progressing`

Day la van de rieng cua monitoring stack, khong phai loi cua Part 2.

Khong can sua no neu muc tieu la hoan thanh lab secrets va supply chain cho `api`.

## Thu tu thuc hien de tranh bi tac

Nen lam dung thu tu sau:

1. tao GitHub secrets
2. push code Part 2
3. de GitHub Actions build, scan, push, sign
4. verify image da sign
5. cai Policy Controller
6. de ArgoCD sync policy
7. test unsigned reject
8. test signed pass

Ly do:

- neu bat policy truoc khi image cua app da co signature, cluster co the tu chan chinh app cua ban

## Tieu chi pass Part 2

Pass khi tat ca dieu kien sau dung:

- CI scan image bang Trivy
- CI fail neu co CVE `HIGH/CRITICAL`
- image duoc push len GHCR
- image duoc Cosign sign thanh cong
- cluster co `ClusterImagePolicy`
- unsigned image bi reject
- signed image deploy duoc

## Trang thai hien tai

Tinh den luc viet file nay:

- Part 1 da lam xong va da verify
- Part 2 da implement xong tren repo
- GitHub Secrets da co the tao tay
- policy controller da co the install bang script
- ArgoCD app `policies` da co
- rollout `api` da chay duoc voi image GHCR signed

Neu can chay lai, uu tien lam theo cac buoc trong file nay thay vi thao tac nho le.
