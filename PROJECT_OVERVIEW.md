# Tong quan du an GitOps RBAC

Tai lieu nay giai thich du an theo huong de doc lai va nam luong hoat dong. Repo nay gom cac phan cua Lab 1 va Lab 2: RBAC, Gatekeeper admission policy, External Secrets Operator, Trivy, Cosign va image verification.

## 1. Y tuong tong the

Du an dung GitOps lam trung tam. Nghia la thay vi `kubectl apply` tung file bang tay, cac manifest duoc commit len GitHub, sau do ArgoCD doc repo va dong bo vao Kubernetes cluster.

Luong chinh:

```text
GitHub repo
  -> argocd/root.yaml
  -> argocd/apps/*.yaml
  -> ArgoCD child applications
  -> Kubernetes resources
```

`argocd/root.yaml` la root application theo pattern App of Apps. Root app doc thu muc `argocd/apps/`, trong do moi file YAML la mot ArgoCD Application rieng. Moi Application lai tro den mot thu muc khac trong repo, vi du `rbac/`, `gatekeeper/constraints/`, `app-api/`, `k8s-eso/`.

Ket qua la moi thanh phan cua platform duoc quan ly bang Git:

- RBAC user permissions.
- Gatekeeper controller va admission constraints.
- Namespace, API rollout, service, monitoring.
- External Secrets Operator config.
- Sigstore image verification policy.

## 2. Cau truc thu muc quan trong

```text
argocd/
  root.yaml                 # Root app, tao cac child app
  apps/                     # Cac ArgoCD Application con

rbac/
  roles.yaml                # Role/ClusterRole cho alice, bob, carol
  rolebindings.yaml         # Bind user vao role

gatekeeper/
  constraints/              # ConstraintTemplate + Constraint
  tests/                    # Manifest test pass/reject

k8s-eso/
  secret-store.yaml         # SecretStore tro den AWS Secrets Manager
  external-secret.yaml      # ExternalSecret sync secret ve K8s

app-api/
  rollout.yaml              # Argo Rollout cua API
  service.yaml              # Service expose API
  servicemonitor.yaml       # Prometheus scrape /metrics

src/api/
  app.py                    # Flask API
  Dockerfile                # Build image API

k8s-policies/
  cluster-image-policy.yaml # Sigstore policy verify signed image

.github/workflows/
  build-push.yml            # Build, scan, push, sign image
```

## 3. Lab 1.1 - RBAC qua GitOps

Muc tieu cua phan nay la phan quyen 3 user bang Kubernetes RBAC, tat ca di qua GitOps.

File lien quan:

- `rbac/roles.yaml`
- `rbac/rolebindings.yaml`
- `argocd/apps/rbac.yaml`

### 3.1 User va quyen

`alice` la developer trong namespace `demo`.

- Dung `Role` namespaced.
- Duoc CRUD workload trong `demo`.
- Co quyen voi `pods`, `services`, `deployments`.
- Khong co quyen sang namespace khac.

`bob` la SRE toan cluster.

- Dung `ClusterRole`.
- Duoc thao tac pod tren moi namespace.
- Co cac verb `get/list/watch/create/update/patch/delete` tren `pods`.

`carol` la viewer toan cluster.

- Dung `ClusterRole`.
- Chi duoc doc bang `get/list/watch`.
- Khong duoc create, update, delete.

### 3.2 Binding

`rbac/rolebindings.yaml` gan user vao role:

- `alice-developer`: RoleBinding trong namespace `demo`.
- `bob-sre`: ClusterRoleBinding.
- `carol-viewer`: ClusterRoleBinding.

Diem quan trong: subject deu la user gia lap:

```yaml
subjects:
- kind: User
  name: alice
```

Khi test, dung `kubectl auth can-i --as <user>` de gia lap user. Day chi test authorization, chua can authentication that.

### 3.3 Lenh nghiem thu

```bash
kubectl auth can-i create deploy -n demo --as alice
# yes

kubectl auth can-i create deploy -n kube-system --as alice
# no

kubectl auth can-i get pods -A --as bob
# yes

kubectl auth can-i delete nodes --as carol
# no
```

## 4. Lab 1.2 - Gatekeeper admission policy

Phan nay cai OPA Gatekeeper va viet policy chan manifest xau ngay tai admission webhook. Nghia la manifest vi pham se bi API server reject truoc khi resource duoc tao.

File lien quan:

- `argocd/apps/gatekeeper.yaml`
- `argocd/apps/gatekeeper-constraints.yaml`
- `gatekeeper/constraints/*.yaml`
- `gatekeeper/tests/*.yaml`

### 4.1 Luong cai dat

`argocd/apps/gatekeeper.yaml` cai Gatekeeper controller bang Helm chart.

`argocd/apps/gatekeeper-constraints.yaml` sync thu muc `gatekeeper/constraints/`, noi chua policy.

Thu tu sync:

```text
Gatekeeper controller
  -> ConstraintTemplate
  -> Constraint
```

Trong repo, thu tu nay duoc dieu khien bang sync-wave:

- Gatekeeper controller: wave `10`.
- Gatekeeper constraints app: wave `11`.
- ConstraintTemplate: wave `0` trong app constraints.
- Constraint: wave `1` trong app constraints.

### 4.2 Bon luat bat buoc

Repo co 4 luat dung theo slide:

1. Cam image tag `:latest`.
2. Bat buoc container co `resources.limits`.
3. Cam container hoac pod chay voi `runAsUser: 0`.
4. Cam `hostNetwork: true`.

Moi luat gom 2 file:

```text
k8sdisallowlatesttag-template.yaml
k8sdisallowlatesttag.yaml

k8srequirelimits-template.yaml
k8srequirelimits.yaml

k8sdisallowrootuser-template.yaml
k8sdisallowrootuser.yaml

k8sdisallowhostnetwork-template.yaml
k8sdisallowhostnetwork.yaml
```

`ConstraintTemplate` chua logic Rego. `Constraint` bat enforcement bang:

```yaml
enforcementAction: deny
```

Constraints duoc match vao cac loai workload:

- Pod
- Deployment
- StatefulSet
- DaemonSet
- Rollout

Mot so namespace he thong duoc exclude de tranh tu chan platform:

- `kube-system`
- `argocd`
- `gatekeeper-system`
- `external-secrets`
- `cosign-system`
- `sigstore-system`

### 4.3 Test Gatekeeper

Thu muc `gatekeeper/tests/` co manifest dung de kiem tra:

- `pod-latest.yaml`: dung `nginx:latest`, phai reject.
- `pod-no-limits.yaml`: thieu limits, phai reject.
- `pod-root-user.yaml`: `runAsUser: 0`, phai reject.
- `pod-hostnetwork.yaml`: `hostNetwork: true`, phai reject.
- `pod-valid.yaml`: image pin version, co limits, non-root, phai pass.

Lenh test:

```bash
kubectl apply -f gatekeeper/tests/pod-latest.yaml
kubectl apply -f gatekeeper/tests/pod-no-limits.yaml
kubectl apply -f gatekeeper/tests/pod-root-user.yaml
kubectl apply -f gatekeeper/tests/pod-hostnetwork.yaml
kubectl apply -f gatekeeper/tests/pod-valid.yaml
```

## 5. Lab 1.3 - Custom ConstraintTemplate

Phan custom policy trong repo chon bai: reject workload neu `replicas > 5`.

File lien quan:

- `gatekeeper/constraints/k8smaxreplicas-template.yaml`
- `gatekeeper/constraints/k8smaxreplicas.yaml`
- `gatekeeper/tests/deploy-too-many-replicas.yaml`
- `gatekeeper/tests/deploy-ok-replicas.yaml`

### 5.1 Cach hoat dong

`k8smaxreplicas-template.yaml` tao custom kind:

```yaml
kind: K8sMaxReplicas
```

Logic Rego doc:

- `input.review.object.spec.replicas`
- `input.parameters.maxReplicas`

Neu replicas lon hon nguong thi tao violation.

`k8smaxreplicas.yaml` cau hinh:

```yaml
parameters:
  maxReplicas: 5
```

Policy match vao:

- Deployment
- Rollout

App `api` hien tai co `replicas: 4`, nen khong bi chan. Manifest test `deploy-too-many-replicas.yaml` co `replicas: 6`, nen phai bi reject.

## 6. App API va progressive delivery

App chinh cua du an la Flask API trong `src/api/app.py`, duoc build bang `src/api/Dockerfile` va deploy bang Argo Rollouts.

File lien quan:

- `src/api/app.py`
- `src/api/Dockerfile`
- `app-api/rollout.yaml`
- `app-api/service.yaml`
- `app-api/servicemonitor.yaml`
- `app-analysis/analysis-template.yaml`

### 6.1 Flask API

API co cac endpoint:

- `/`: tra status app, version, trang thai DB secret.
- `/healthz`: health check.
- `/db-secret`: debug xem app doc duoc secret hay chua.
- `/metrics`: duoc tao tu `prometheus_flask_exporter` de Prometheus scrape.

App co bien moi truong:

- `VERSION`: version dang chay.
- `ERROR_RATE`: ty le gia lap loi 500.
- `DB_PASSWORD_PATH`: duong dan file secret, mac dinh `/secrets/password`.

### 6.2 Argo Rollout

`app-api/rollout.yaml` deploy API voi:

- namespace `demo`
- replicas `4`
- image `ghcr.io/mthanh12/lab-gitops-rbac-api:0.0.1`
- `imagePullPolicy: Always`
- resources limits `cpu: 200m`, `memory: 128Mi`
- mount secret `db-secret` vao `/secrets`

Canary strategy:

```text
10%
  -> pause 2m
50%
  -> pause 2m
100%
```

### 6.3 AnalysisTemplate

`app-analysis/analysis-template.yaml` dung Prometheus de tinh success rate:

```text
request khong phai 5xx / tong request
```

Dieu kien pass:

```text
success rate >= 0.90
```

Neu success rate thap hon, AnalysisRun fail va rollout co the bi chan/rollback tuy cau hinh runtime.

## 7. Lab 2.1 - ESO secret rotation

Muc tieu: secret DB khong nam trong Git, ma nam trong AWS Secrets Manager. Cluster dung External Secrets Operator de dong bo secret ve Kubernetes.

File lien quan:

- `k8s-eso/secret-store.yaml`
- `k8s-eso/external-secret.yaml`
- `argocd/apps/eso.yaml`
- `app-api/rollout.yaml`
- `src/api/app.py`

### 7.1 Luong hoat dong

```text
AWS Secrets Manager
  -> External Secrets Operator
  -> Kubernetes Secret db-secret
  -> mounted volume /secrets/password
  -> Flask app doc file secret
```

`SecretStore` cau hinh provider AWS:

- service: SecretsManager
- region: `ap-southeast-1`
- auth bang Kubernetes secret `aws-credentials`

`ExternalSecret` cau hinh:

- remote key: `prod/db/password`
- target Kubernetes secret: `db-secret`
- refreshInterval: `1m`

### 7.2 Vi sao rotate khong restart pod

App khong doc password tu env var. App doc tu file:

```text
/secrets/password
```

Kubernetes Secret duoc mount vao pod bang volume. Khi ESO cap nhat `db-secret`, kubelet cap nhat noi dung file trong volume. App moi lan xu ly request lai doc file, nen thay gia tri moi ma khong can restart pod.

### 7.3 Kiem tra

Kiem tra ESO:

```bash
kubectl get secretstore,externalsecret,secret -n demo
```

Kiem tra app:

```bash
kubectl exec -n demo <pod> -- cat /secrets/password
kubectl exec -n demo <pod> -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/db-secret').read().decode())"
```

Pass khi:

- `SecretStore` valid.
- `ExternalSecret` synced.
- Co secret `db-secret`.
- App tra `password_found=true`.
- Doi secret tren AWS, cho khoang 60 giay, file trong pod doi theo.

## 8. Lab 2.2 - Trivy, Cosign, image verification

Muc tieu: image phai duoc build, scan, push, sign; cluster chi chap nhan image da ky.

File lien quan:

- `.github/workflows/build-push.yml`
- `cosign.pub`
- `k8s-policies/cluster-image-policy.yaml`
- `argocd/apps/policies.yaml`
- `scripts/install_policy_controller.ps1`

### 8.1 CI build-push workflow

Workflow `Build Scan Sign Push Image` chay khi push thay doi trong:

- `src/api/**`
- `.github/workflows/build-push.yml`

Luong CI:

```text
checkout
  -> tinh semantic version
  -> docker build
  -> Trivy scan
  -> docker push GHCR
  -> resolve digest
  -> Cosign sign neu co secret
  -> update app-api/rollout.yaml
  -> commit version moi
  -> tao git tag
```

Image dang dung:

```text
ghcr.io/mthanh12/lab-gitops-rbac-api
```

Workflow can GitHub permissions:

```yaml
permissions:
  contents: write
  packages: write
```

### 8.2 Trivy

Trivy scan image voi severity:

```text
HIGH,CRITICAL
```

Hien tai workflow dang de:

```yaml
exit-code: 0
```

Nghia la scan van chay va hien ket qua, nhung khong lam fail pipeline. Neu muon dung chat theo slide "co HIGH/CRITICAL thi CI do", doi lai thanh:

```yaml
exit-code: 1
```

### 8.3 Cosign

Cosign ky image sau khi push thanh cong. Workflow chi sign neu repo co GitHub secret:

- `COSIGN_PRIVATE_KEY`
- `COSIGN_PASSWORD`

Public key duoc commit trong:

```text
cosign.pub
```

Private key khong duoc commit.

### 8.4 Sigstore Policy Controller

Policy controller duoc cai bang script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_policy_controller.ps1
```

Sau do ArgoCD app `policies` sync file:

```text
k8s-policies/cluster-image-policy.yaml
```

Policy match image:

```text
ghcr.io/mthanh12/lab-gitops-rbac-api*
```

Va verify signature bang public key trong policy.

Ket qua mong doi:

- Image chua ky: admission reject.
- Image da ky bang dung private key: pass.

## 9. Luu y quan trong cua repo hien tai

### 9.1 targetRevision dang la master

Repo GitHub hien dang dung branch `main`, nhung nhieu ArgoCD Application van co:

```yaml
targetRevision: master
```

Neu chay ArgoCD truc tiep tu repo nay, nen doi tat ca thanh:

```yaml
targetRevision: main
```

Nhung file can kiem tra:

- `argocd/root.yaml`
- `argocd/apps/*.yaml`

### 9.2 Repo va image dang dung

Repo va image hien tai da duoc chuan hoa theo thong tin sau:

```text
https://github.com/mthanh12/-lab_Gitops_RBAC.git
ghcr.io/mthanh12/lab-gitops-rbac-api
```

### 9.3 Khong commit secret

Repo da co `.gitignore` chan mot so secret:

- `cosign.key`
- `*.secret.yaml`
- `**/email-secret.yaml`

AWS credentials va Cosign private key phai tao bang secret store / GitHub Secrets / kubectl secret, khong dua vao Git.

## 10. Cach tu kiem nhanh toan bo lab

RBAC:

```bash
kubectl auth can-i create deploy -n demo --as alice
kubectl auth can-i create deploy -n kube-system --as alice
kubectl auth can-i get pods -A --as bob
kubectl auth can-i delete nodes --as carol
```

Gatekeeper:

```bash
kubectl apply -f gatekeeper/tests/pod-latest.yaml
kubectl apply -f gatekeeper/tests/pod-no-limits.yaml
kubectl apply -f gatekeeper/tests/pod-root-user.yaml
kubectl apply -f gatekeeper/tests/pod-hostnetwork.yaml
kubectl apply -f gatekeeper/tests/pod-valid.yaml
kubectl apply -f gatekeeper/tests/deploy-too-many-replicas.yaml
kubectl apply -f gatekeeper/tests/deploy-ok-replicas.yaml
```

ESO:

```bash
kubectl get secretstore,externalsecret,secret -n demo
kubectl get secret db-secret -n demo
kubectl exec -n demo <api-pod> -- cat /secrets/password
```

Rollout:

```bash
kubectl get rollout api -n demo
kubectl get analysisrun -n demo
kubectl get pods -n demo -l app=api
```

Supply chain:

```bash
kubectl get clusterimagepolicy
cosign verify --key cosign.pub ghcr.io/mthanh12/lab-gitops-rbac-api:<tag>
```

## 11. Tom tat de nho

Lab 1 bien cluster thanh moi truong co quyen ro rang va admission policy:

- `alice`, `bob`, `carol` co quyen rieng.
- Gatekeeper chan manifest xau.
- Custom policy chan workload qua 5 replicas.

Lab 2 them secret rotation va supply chain security:

- Secret that nam ngoai Git trong AWS Secrets Manager.
- ESO sync secret ve Kubernetes.
- App doc secret qua mounted file nen rotate khong restart pod.
- CI build image, scan, push, sign.
- Cluster verify image signature truoc khi cho chay.

Toan bo du an the hien mot platform GitOps co guardrail: user co quyen toi dau, manifest co hop le khong, secret co bi lo khong, image co sach va da ky khong.
