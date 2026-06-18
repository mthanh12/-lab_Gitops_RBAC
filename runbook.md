# Runbook

## Muc tieu

Chay lai demo voi image backend rieng cua repo nay va kiem tra rollout thanh cong.

## Dieu kien

- Docker Desktop dang chay
- `minikube` profile `w10` dang dung
- `kubectl` dang tro vao context `w10`

## 1. Build image local

```powershell
docker build -t gitops-rbac-api:0.0.1 src/api
minikube image load gitops-rbac-api:0.0.1 -p w10
```

## 2. Xac nhan rollout dung image local

File [app-api/rollout.yaml](D:\W10\temp\app-api\rollout.yaml:1) can giu:

- `image: gitops-rbac-api:0.0.1`
- `imagePullPolicy: Never`

## 3. Apply app API

```powershell
kubectl apply -f app-api/service.yaml
kubectl apply -f app-api/servicemonitor.yaml
kubectl apply -f app-api/rollout.yaml
```

## 4. Theo doi rollout

```powershell
kubectl get pods -n demo
kubectl get analysisrun -n demo
kubectl get rollout api -n demo
kubectl get applications -n argocd
```

## 5. Tieu chi pass

Pass khi tat ca dieu kien sau dung:

- `kubectl get applications -n argocd`
  - app `api` la `Synced` va `Healthy`
- `kubectl get analysisrun -n demo`
  - run moi nhat la `Successful`
- `kubectl get rollout api -n demo`
  - `DESIRED = CURRENT = UP-TO-DATE = AVAILABLE = 4`
- `kubectl get pods -n demo`
  - 4 pod `api-*` moi deu `1/1 Running`

## 6. Kiem tra metric

```powershell
kubectl run test-query --image=curlimages/curl:latest --rm -i --restart=Never -n monitoring -- curl -s "http://kube-prometheus-stack-prometheus.monitoring.svc:9090/api/v1/query?query=api:success_rate:5m"
```

Ket qua mong doi:

- tra ve `1` hoac gia tri gan `1`

## 7. Ghi chu

- `AnalysisRun` cu bi `Failed` van co the con trong namespace `demo`, dieu nay binh thuong va khong anh huong neu run moi nhat la `Successful`
- ReplicaSet cu cung co the con trong lich su voi `DESIRED 0`, dieu nay binh thuong
- Neu Argo CD tu sync lai image cu, kiem tra xem file `app-api/rollout.yaml` da duoc push len repo `master` chua

## 8. Part 2

Part 2 dung:

- `/.github/workflows/build-push.yml` de build -> Trivy scan -> push -> Cosign sign
- `k8s-policies/cluster-image-policy.yaml` de verify signed image

Chi tiet trien khai va validate xem trong `plan_afternoon.md`
