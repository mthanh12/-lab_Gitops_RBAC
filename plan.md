# Plan chay va kiem thu 1 kich ban

## Muc tieu

Chay full demo GitOps/Kubernetes va chi kiem thu 1 kich ban:

- deploy thanh cong
- `ERROR_RATE = "0"`
- rollout di het 10% -> 50% -> 100%
- `AnalysisRun` pass

Toi chon kich ban nay vi no it rui ro nhat, de xac nhan toan bo duong chay co ban da dung:

- Argo CD sync duoc repo
- Argo Rollouts hoat dong
- Prometheus scrape duoc metrics
- AnalysisTemplate danh gia thanh cong

## Dieu kien dau vao

Can co san:

- Docker Desktop
- `minikube`
- `kubectl`
- `git`
- mang ra ngoai de keo chart/image/repo

Repo da duoc chot:

- `https://github.com/nguyentoan02/Gitops_RBAC.git`
- branch `master`

Email alert da cau hinh local:

- `app-alert/email-secret.yaml`

## Cach bat lai sau khi tat may / tat Docker / tat minikube

Neu ban da chay thanh cong truoc do va chi can mo lai moi truong, khong can cai lai tu dau.

Thu tu chay:

1. Mo Docker Desktop va cho Docker len on dinh
2. Bat lai minikube profile `w10`
3. Chuyen `kubectl` ve dung context
4. Kiem tra cluster va app
5. Neu can xem UI thi port-forward lai Argo CD

Lenh can chay:

```powershell
minikube start -p w10 --driver=docker
kubectl config use-context w10
kubectl get nodes
kubectl get applications -n argocd
kubectl get pods -n demo
kubectl get pods -n monitoring
```

Neu rollout dang dung image local rieng:

```powershell
minikube image load gitops-rbac-api:0.0.1 -p w10
```

Luu y:

- Image local trong Docker cua may ban co the can load lai vao `minikube` sau khi bat lai moi truong
- Neu app `api` bi loi image sau khi bat lai, build va load lai:

```powershell
docker build -t gitops-rbac-api:0.0.1 src/api
minikube image load gitops-rbac-api:0.0.1 -p w10
kubectl apply -f app-api/service.yaml
kubectl apply -f app-api/servicemonitor.yaml
kubectl apply -f app-api/rollout.yaml
```

Neu muon mo lai Argo CD UI:

```powershell
kubectl -n argocd port-forward svc/argocd-server 8080:443
```

Sau do vao:

- `https://localhost:8080`

## Kich ban duy nhat can chay

### Buoc 1 - Tao cluster

```bash
minikube start -p w10 --driver=docker
kubectl config use-context w10
kubectl get nodes
```

Ket qua mong doi:

- cluster `w10` len thanh cong
- `kubectl get nodes` tra ve node `Ready`

### Buoc 2 - Cai Argo CD

```bash
kubectl create ns argocd
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd rollout status deploy/argocd-server
```

Ket qua mong doi:

- `argocd-server` chay `successfully rolled out`

### Buoc 3 - Mo Argo CD UI de xem

Port-forward:

```bash
kubectl -n argocd port-forward svc/argocd-server 8080:443
```

Lay mat khau admin ban dau:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
```

Decode dung tren PowerShell:

```powershell
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String((kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}")))
```

Mo trinh duyet:

- URL: `https://localhost:8080`
- user: `admin`
- password: gia tri vua decode

Trong UI, can xem:

- app `root`
- cac child app `common`, `kube-prometheus-stack`, `argo-rollouts`, `analysis`, `alert`, `api`
- trang thai `Synced` va `Healthy`

### Buoc 4 - Deploy App of Apps

```bash
kubectl apply -f argocd/root.yaml
```

Ket qua mong doi:

- cac app `common`, `kube-prometheus-stack`, `argo-rollouts`, `analysis`, `alert`, `api` duoc tao

Theo doi:

```bash
kubectl get applications -n argocd
kubectl get pods -n argo-rollouts
kubectl get pods -n monitoring
kubectl get pods -n demo
```

### Buoc 5 - Apply secret email

```bash
kubectl apply -f app-alert/email-secret.yaml
```

Neu namespace `monitoring` chua ton tai, cho app `kube-prometheus-stack` sync xong roi moi apply lai lenh tren.

Ket qua mong doi:

- secret `alertmanager-email` duoc tao trong namespace `monitoring`

### Buoc 6 - Xac nhan rollout thanh cong

File [app-api/rollout.yaml](D:\W10\temp\app-api\rollout.yaml:1) hien dang de:

- `ERROR_RATE = "0"`

Kiem tra rollout va analysis:

```bash
kubectl get rollout api -n demo
kubectl get rollout api -n demo -w
kubectl get analysisrun -n demo
kubectl get pods -n demo -l app=api
```

Ket qua mong doi:

- rollout tang qua cac step canary
- `AnalysisRun` co trang thai thanh cong
- rollout dat trang thai `Healthy`
- pod API chay on dinh

Trong Argo CD UI, co the mo app `api` de xem:

- resource `Rollout/api`
- resource `Service/api`
- resource `ServiceMonitor/api`
- timeline sync va health

### Buoc 7 - Kiem tra metrics

```bash
kubectl run test-query --image=curlimages/curl:latest --rm -i --restart=Never -n monitoring -- curl -s "http://kube-prometheus-stack-prometheus.monitoring.svc:9090/api/v1/query?query=api:success_rate:5m"
```

Ket qua mong doi:

- query tra ve gia tri gan `1`

## Tieu chi pass

Buoi chay duoc coi la pass khi:

1. Argo CD tao day du child applications
2. Rollout `api` len thanh cong trong namespace `demo`
3. `AnalysisRun` pass
4. Prometheus query `api:success_rate:5m` tra ve ket qua hop le

## Neu co loi, check theo thu tu nay

1. `kubectl get applications -n argocd`
2. `kubectl get pods -n argocd`
3. `kubectl get pods -n argo-rollouts`
4. `kubectl get pods -n monitoring`
5. `kubectl get pods -n demo`
6. `kubectl describe rollout api -n demo`
7. `kubectl describe analysisrun -n demo <ten-analysisrun>`

## Ket luan

Khong can chay nhieu kich ban luc nay. Chi can chay 1 kich ban thanh cong voi `ERROR_RATE = "0"` de xac nhan duong nen cua he thong da dung. Sau khi kich ban nay pass, moi nen chuyen sang test rollback hoac alert SLO.
