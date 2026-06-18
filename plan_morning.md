# Plan W10 Morning: RBAC + Admission Policy

## Muc tieu tong

Hoan thanh 3 phan bat buoc cua lab:

1. RBAC: tao 3 role cho `alice`, `bob`, `carol` qua GitOps.
2. Gatekeeper: cai OPA Gatekeeper va enforce 4 constraint chan manifest xau.
3. Custom policy: tu viet 1 `ConstraintTemplate` + 1 `Constraint` bang Rego.

Tat ca phai di qua git va ArgoCD, khong `kubectl apply` tay de nop bai.

## Buoc 0: Chuan bi

- Fork repo platform.
- Sua `argocd/root.yaml` de `repoURL` tro ve repo fork cua ban.
- Kiem tra cac file trong `argocd/apps/`:
  - Moi `Application` deu co `spec.source.repoURL` rieng.
  - Neu ban fork repo thi cac child app nay cung phai tro ve repo fork cua ban, neu khong ArgoCD van lay manifest tu repo cu.
- Xac nhan platform W9 dang `Synced/Healthy` truoc khi them RBAC va Gatekeeper.

## Phan 1: RBAC qua GitOps

### Muc tieu can dat

- `alice` duoc CRUD workload chi trong namespace `demo`.
- `bob` duoc xem va thao tac pod toan cum.
- `carol` chi duoc doc toan cum.
- Moi thay doi di qua git + ArgoCD, khong apply tay.

### File can tao / sua

- Tao thu muc `rbac/`
- Tao `rbac/roles.yaml`
- Tao `rbac/rolebindings.yaml`
- Tao `argocd/apps/rbac.yaml`

### Cach lam tung buoc

#### Buoc 1: Xac dinh loai role can dung

- `alice` chi song trong `demo` nen dung `Role` namespaced.
- `bob` va `carol` la quyen toan cum nen dung `ClusterRole`.
- User that su duoc gan quyen thong qua `RoleBinding` hoac `ClusterRoleBinding`.

#### Buoc 2: Tao `rbac/roles.yaml`

Trong file nay khai bao 3 role:

- `Role` ten `developer` trong namespace `demo`
  - Cho phep `get/list/watch/create/update/patch/delete`
  - Tren:
    - `pods`
    - `services`
    - `deployments.apps`
- `ClusterRole` ten `sre`
  - Cho phep thao tac tren `pods` toan cum
  - Quyen dung:
    - `get/list/watch/create/update/patch/delete`
- `ClusterRole` ten `viewer`
  - Chi doc toan cum
  - Quyen dung:
    - `get/list/watch`
  - Co the cap cho:
    - `pods`
    - `services`
    - `namespaces`
    - `deployments`
    - `replicasets`

#### Buoc 3: Tao `rbac/rolebindings.yaml`

Trong file nay khai bao 3 binding:

- `RoleBinding` ten `alice-developer` trong namespace `demo`
  - `subjects.kind: User`
  - `subjects.name: alice`
  - `roleRef` tro toi `Role/developer`
- `ClusterRoleBinding` ten `bob-sre`
  - bind user `bob` vao `ClusterRole/sre`
- `ClusterRoleBinding` ten `carol-viewer`
  - bind user `carol` vao `ClusterRole/viewer`

#### Buoc 4: Tao `argocd/apps/rbac.yaml`

Tao 1 child app de ArgoCD doc thu muc `rbac/`:

- `metadata.name: rbac`
- `spec.source.path: rbac`
- `spec.source.repoURL`: trung voi repo dang dung
- `destination.namespace: demo`
- bat `automated.prune` va `selfHeal`

Neu ban dang lam tren repo fork, file nay cung phai tro dung `repoURL` cua repo fork.

#### Buoc 5: Commit va push

- `git add rbac argocd/apps/rbac.yaml plan_morning.md`
- `git commit -m "Add RBAC lab manifests"`
- `git push`

#### Buoc 6: ArgoCD sync

- Mo ArgoCD va kiem tra app `root`
- Xac nhan child app `rbac` duoc tao
- Cho `rbac` ve trang thai `Synced/Healthy`

Neu `rbac` khong xuat hien:

- Kiem tra `root` da sync lai chua
- Kiem tra `argocd/apps/rbac.yaml` da nam trong branch dung chua
- Kiem tra `repoURL` co dang tro sai repo khong

#### Buoc 7: Test quyen bang impersonation

Sau khi ArgoCD sync xong, chay 4 lenh `kubectl auth can-i` de xac nhan authorization.

### Luu y ky thuat

- `alice` bi gioi han trong 1 namespace nen dung `Role`.
- `bob` va `carol` la pham vi toan cum nen dung `ClusterRole`.
- `viewer` tuyet doi khong duoc co `create/update/delete`.
- Binding cho user thi dung `subjects.kind: User`.
- `kubectl auth can-i --as <user>` chi kiem authorization, khong can authentication that.
- Trong repo nay cac app ArgoCD dang hardcode `repoURL`, day la diem de sai nhat khi fork repo.

### Nghiem thu RBAC

4 lenh sau phai cho ket qua dung:

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

### Ket qua hien tai da duoc tao trong repo nay

- `rbac/roles.yaml`
- `rbac/rolebindings.yaml`
- `argocd/apps/rbac.yaml`

Khi review lai sau nay, chi can doi chieu 3 file tren voi muc tieu role va 4 lenh nghiem thu la du.

## Phan 2: Gatekeeper + 4 constraint

### Muc tieu can dat

- Cai OPA Gatekeeper qua GitOps.
- Co 4 constraint chan manifest xau tai admission.
- Thu deploy resource vi pham phai bi reject.
- Platform hien tai van dung duoc sau khi bat enforce.

### File can tao / sua

- Tao `argocd/apps/gatekeeper.yaml`
- Tao `argocd/apps/gatekeeper-constraints.yaml`
- Tao thu muc `gatekeeper/constraints/`
- Tao 4 `ConstraintTemplate`
- Tao 4 `Constraint`

### Cach lam tung buoc

#### Buoc 1: Kiem tra workload hien tai truoc khi enforce

Truoc khi viet policy, doc workload dang chay cua platform de tranh tu khoa chan chinh minh.

Trong repo nay, file can check dau tien la:

- `app-api/rollout.yaml`

Nhung diem can doi:

- image co dang dung `:latest` khong
- co `resources.limits` khong
- co `runAsUser: 0` khong
- co `hostNetwork: true` khong

Trong repo hien tai:

- image la `gitops-rbac-api:0.0.1` -> khong dung `:latest`
- da co `resources.limits`
- khong thay `runAsUser: 0`
- khong thay `hostNetwork: true`

Tuc la app `api` hien tai khong bi 4 luat nay chan.

#### Buoc 2: Cai Gatekeeper controller qua ArgoCD

Tao `argocd/apps/gatekeeper.yaml` de ArgoCD cai controller.

Nhung diem quan trong trong file nay:

- `metadata.name: gatekeeper`
- `spec.source.repoURL`: Helm repo cua Gatekeeper
- `spec.source.chart: gatekeeper`
- `destination.namespace: gatekeeper-system`
- `sync-wave` dat truoc constraints

Trong repo nay, app controller dang duoc dat:

- sync-wave `10`
- chart `gatekeeper`
- chart version `3.16.3`

Neu ve sau chart version nay khong con phu hop voi cluster cua ban, day la file dau tien can doi.

#### Buoc 3: Tao app de ArgoCD quan ly constraints

Tao `argocd/apps/gatekeeper-constraints.yaml`.

Muc dich:

- cho ArgoCD doc thu muc `gatekeeper/constraints/`
- tách phan policy khoi phan controller
- cho de sync lai policy ma khong dong vao install Gatekeeper

Nhung diem can co:

- `metadata.name: gatekeeper-constraints`
- `spec.source.path: gatekeeper/constraints`
- `destination.namespace: gatekeeper-system`
- `sync-wave` lon hon app controller

Trong repo nay, app nay dang la sync-wave `11`.

#### Buoc 4: Tao 4 ConstraintTemplate

Trong repo nay, toi da tao 4 template sau:

- `gatekeeper/constraints/k8sdisallowlatesttag-template.yaml`
- `gatekeeper/constraints/k8srequirelimits-template.yaml`
- `gatekeeper/constraints/k8sdisallowrootuser-template.yaml`
- `gatekeeper/constraints/k8sdisallowhostnetwork-template.yaml`

Moi template:

- la `ConstraintTemplate`
- co sync-wave `0`
- chua logic Rego de Gatekeeper sinh ra CRD tuong ung

Luu y:

- Slide goi y co the lay tu `gatekeeper-library`
- Trong repo nay toi chon viet template local de repo tu chua, de review va hoc lai de hon
- Vi dang dung `apiVersion: templates.gatekeeper.sh/v1`, moi `ConstraintTemplate` nen co `spec.crd.spec.validation.openAPIV3Schema` hop le
- Neu thieu schema nay, API server co the tu choi tao `ConstraintTemplate`

#### Buoc 5: Tao 4 Constraint

Trong repo nay, toi da tao 4 constraint sau:

- `gatekeeper/constraints/k8sdisallowlatesttag.yaml`
- `gatekeeper/constraints/k8srequirelimits.yaml`
- `gatekeeper/constraints/k8sdisallowrootuser.yaml`
- `gatekeeper/constraints/k8sdisallowhostnetwork.yaml`

Moi constraint:

- co `enforcementAction: deny`
- co sync-wave `1`
- match vao:
  - `Pod`
  - `Deployment`
  - `StatefulSet`
  - `DaemonSet`
  - `Rollout`
- exclude:
  - `kube-system`
  - `argocd`
  - `gatekeeper-system`

Ly do exclude namespace he thong:

- tranh Gatekeeper tu chan chinh no
- tranh chan ArgoCD/system components
- giam rui ro luc moi bat enforce

#### Buoc 6: Dam bao dung thu tu sync

Thu tu can dung:

1. app Gatekeeper controller duoc sync truoc
2. `ConstraintTemplate` duoc apply
3. `Constraint` duoc apply

Trong repo nay, thu tu duoc dat bang:

- `argocd/apps/gatekeeper.yaml` -> sync-wave `10`
- `argocd/apps/gatekeeper-constraints.yaml` -> sync-wave `11`
- `ConstraintTemplate` -> sync-wave `0`
- `Constraint` -> sync-wave `1`

Noi dung nay quan trong vi:

- neu constraint vao truoc template -> ArgoCD se loi vi CRD chua ton tai
- neu template/constraint vao truoc controller -> webhook va CRD co the chua san sang

#### Buoc 7: Commit va push

- `git add argocd/apps/gatekeeper.yaml argocd/apps/gatekeeper-constraints.yaml gatekeeper plan_morning.md`
- `git commit -m "Add Gatekeeper policies for admission control"`
- `git push`

#### Buoc 8: ArgoCD sync

Trong ArgoCD, kiem tra theo thu tu:

1. app `gatekeeper`
2. app `gatekeeper-constraints`

Ket qua mong doi:

- `gatekeeper` -> `Synced/Healthy`
- `gatekeeper-constraints` -> `Synced/Healthy`

Neu app `gatekeeper` van `OutOfSync` nhung pods van chay:

- kiem tra danh sach resource bi lech co phai la cac `CustomResourceDefinition` cua Gatekeeper khong
- day la truong hop rat hay gap voi Helm chart + CRD
- co the them `ignoreDifferences` trong `argocd/apps/gatekeeper.yaml` cho:
  - `/metadata/annotations`
  - `/metadata/managedFields`
  - `/status`
  - `/spec/conversion/webhook/clientConfig/caBundle`
  - `/spec/preserveUnknownFields`
- muc dich la bo qua cac field he thong/duoc inject sau khi apply, tranh app luc nao cung lech
- them `RespectIgnoreDifferences=true` de ArgoCD ton trong phan ignore nay trong qua trinh sync

Neu `gatekeeper-constraints` loi:

- kiem tra `gatekeeper` da len xong chua
- kiem tra template co apply thanh cong chua
- kiem tra `repoURL` cua app co tro dung repo fork khong
- neu ArgoCD bao loi kieu "resource type not found" voi `K8s...` constraint custom kind:
  - nguyen nhan thuong la `ConstraintTemplate` chua kip tao CRD luc ArgoCD dry-run
  - cach xu ly la them `SkipDryRunOnMissingResource=true` vao `argocd/apps/gatekeeper-constraints.yaml`
  - sync lai sau khi Gatekeeper controller da `Healthy`

#### Buoc 9: Test reject/pass

Sau khi sync xong, tao cac manifest test va thu apply:

- Pod dung image `nginx:latest` -> phai reject
- Pod khong co `resources.limits` -> phai reject
- Pod co `runAsUser: 0` -> phai reject
- Pod co `hostNetwork: true` -> phai reject
- Pod hop le -> phai pass

Trong repo nay da co san bo test:

- `gatekeeper/tests/pod-latest.yaml`
- `gatekeeper/tests/pod-no-limits.yaml`
- `gatekeeper/tests/pod-root-user.yaml`
- `gatekeeper/tests/pod-hostnetwork.yaml`
- `gatekeeper/tests/pod-valid.yaml`

Lenh test mau:

```bash
kubectl apply -f gatekeeper/tests/pod-latest.yaml
kubectl apply -f gatekeeper/tests/pod-no-limits.yaml
kubectl apply -f gatekeeper/tests/pod-root-user.yaml
kubectl apply -f gatekeeper/tests/pod-hostnetwork.yaml
kubectl apply -f gatekeeper/tests/pod-valid.yaml
```

### 4 luat bat buoc enforce

1. Cam image tag `:latest`.
2. Bat buoc co `resources.limits`.
3. Cam `runAsUser: 0`.
4. Cam `hostNetwork: true`.

### Cach lam an toan

- Ban dau co the dat `enforcementAction: warn` de audit.
- Kiem tra resource hien tai cua platform co dang vi pham khong.
- Dac biet kiem tra rollout `api`:
  - image da pin version,
  - co `resources.limits`,
  - khong `runAsUser: 0`.
- Sua workload cua platform neu can.
- Sau khi sach loi moi chuyen sang `enforcementAction: deny`.

Trong repo nay, toi da dat san `deny` vi app `api` hien tai da vuot qua 4 dieu kien tren. Neu ban lam lai o repo khac thi nen bat dau bang `warn`.

### Nghiem thu Gatekeeper

Thu deploy cac manifest test, ket qua phai nhu sau:

- Pod dung image `:latest` -> reject
- Pod thieu `resources.limits` -> reject
- Pod co `runAsUser: 0` -> reject
- Pod co `hostNetwork: true` -> reject
- Pod hop le (version pinned + limits + non-root) -> pass

### Ket qua hien tai da duoc tao trong repo nay

- `argocd/apps/gatekeeper.yaml`
- `argocd/apps/gatekeeper-constraints.yaml`
- `gatekeeper/constraints/k8sdisallowlatesttag-template.yaml`
- `gatekeeper/constraints/k8sdisallowlatesttag.yaml`
- `gatekeeper/constraints/k8srequirelimits-template.yaml`
- `gatekeeper/constraints/k8srequirelimits.yaml`
- `gatekeeper/constraints/k8sdisallowrootuser-template.yaml`
- `gatekeeper/constraints/k8sdisallowrootuser.yaml`
- `gatekeeper/constraints/k8sdisallowhostnetwork-template.yaml`
- `gatekeeper/constraints/k8sdisallowhostnetwork.yaml`

Khi review lai sau nay, hay doi chieu 3 tang:

1. app controller co len duoc khong
2. template co duoc tao CRD khong
3. constraint co reject dung 4 truong hop khong

## Phan 3: Custom policy bat buoc

### Chon de bai trong repo nay

Toi chon policy:

- Reject workload neu `replicas > 5`

Ly do chon:

- de viet va de review
- an toan voi platform hien tai
- `app-api/rollout.yaml` dang `replicas: 4`, nen custom policy nay khong tu chan app cua ban

### Muc tieu can dat

- Tu viet 1 `ConstraintTemplate` bang Rego
- Tao 1 `Constraint` tu template do
- ArgoCD sync thanh cong
- Co 1 manifest bi reject va 1 manifest hop le duoc pass

### File can tao / sua

- `gatekeeper/constraints/k8smaxreplicas-template.yaml`
- `gatekeeper/constraints/k8smaxreplicas.yaml`
- `gatekeeper/tests/deploy-too-many-replicas.yaml`
- `gatekeeper/tests/deploy-ok-replicas.yaml`

### Cach lam tung buoc

#### Buoc 1: Chon policy khong pha platform

Truoc khi viet custom policy, check app hien tai co bi anh huong khong.

Trong repo nay:

- `app-api/rollout.yaml` co `spec.replicas: 4`

Neu ta dat nguong `maxReplicas: 5` thi:

- app `api` pass
- manifest test `replicas: 6` se bi reject

#### Buoc 2: Tao `ConstraintTemplate`

Tao file `gatekeeper/constraints/k8smaxreplicas-template.yaml`.

File nay can co:

- `apiVersion: templates.gatekeeper.sh/v1`
- `kind: ConstraintTemplate`
- `spec.crd.spec.names.kind: K8sMaxReplicas`
- `spec.crd.spec.validation.openAPIV3Schema`
- logic Rego doc:
  - `input.review.object.spec.replicas`
  - `input.parameters.maxReplicas`
  - reject neu replicas lon hon nguong

Trong repo nay, custom kind duoc tao ra la:

- `K8sMaxReplicas`

#### Buoc 3: Tao `Constraint`

Tao file `gatekeeper/constraints/k8smaxreplicas.yaml`.

Noi dung chinh:

- `kind: K8sMaxReplicas`
- `metadata.name: max-replicas-5`
- `enforcementAction: deny`
- `parameters.maxReplicas: 5`
- match vao:
  - `Deployment`
  - `Rollout`
- exclude:
  - `kube-system`
  - `argocd`
  - `gatekeeper-system`

#### Buoc 4: Commit va push

- `git add gatekeeper/constraints gatekeeper/tests plan_morning.md`
- `git commit -m "Add custom Gatekeeper max replicas policy"`
- `git push`

#### Buoc 5: ArgoCD sync

Khong can tao app moi vi `gatekeeper-constraints` da doc san thu muc `gatekeeper/constraints/`.

Can kiem tra:

- app `gatekeeper-constraints` van `Synced/Healthy`
- co them 2 resource moi:
  - `ConstraintTemplate/k8smaxreplicas`
  - `K8sMaxReplicas/max-replicas-5`

#### Buoc 6: Test reject/pass

Trong repo nay da co san:

- `gatekeeper/tests/deploy-too-many-replicas.yaml`
- `gatekeeper/tests/deploy-ok-replicas.yaml`

Lenh test:

```bash
kubectl apply -f gatekeeper/tests/deploy-too-many-replicas.yaml
kubectl apply -f gatekeeper/tests/deploy-ok-replicas.yaml
```

Ky vong:

- `deploy-too-many-replicas.yaml` -> reject
- `deploy-ok-replicas.yaml` -> pass

Luu y:

- sau khi vua tao xong `ConstraintTemplate` va `Constraint`, nen doi vai giay de Gatekeeper webhook nap rule moi
- neu request test dau tien khong bi chan, thu lai voi mot resource name moi de xac nhan hanh vi admission sau khi policy da on dinh

Neu can don dep manifest hop le sau khi test:

```bash
kubectl delete -f gatekeeper/tests/deploy-ok-replicas.yaml
```

### Nghiem thu custom policy

- `ConstraintTemplate` custom duoc tao thanh cong
- `Constraint` custom duoc tao thanh cong
- Manifest `replicas: 6` bi reject
- Manifest `replicas: 3` duoc pass

### Ket qua hien tai da duoc tao trong repo nay

- `gatekeeper/constraints/k8smaxreplicas-template.yaml`
- `gatekeeper/constraints/k8smaxreplicas.yaml`
- `gatekeeper/tests/deploy-too-many-replicas.yaml`
- `gatekeeper/tests/deploy-ok-replicas.yaml`

### Ket qua verify tren cluster hien tai

- custom template `k8smaxreplicas` da tao thanh cong
- constraint `max-replicas-5` da tao thanh cong
- manifest vi pham voi ten moi bi webhook chan voi loi:
  - `Deployment/... has replicas 6, exceeds allowed max 5`
- manifest hop le duoc tao thanh cong

## Deliverable can co trong repo

```text
rbac/                   # 3 role + 3 binding
gatekeeper/constraints/ # 4 constraint + custom policy
argocd/apps/*.yaml      # app cho rbac va gatekeeper
```

## Checklist nop bai

- [ ] `argocd/root.yaml` da tro ve repo fork cua minh
- [ ] Platform W9 van `Synced/Healthy`
- [ ] Da tao du 3 role va 3 binding qua GitOps
- [ ] 4 lenh `kubectl auth can-i` cho ket qua dung
- [ ] Gatekeeper da cai qua ArgoCD
- [ ] 4 constraint bat buoc da duoc enforce
- [ ] 4 manifest vi pham bi reject
- [ ] 1 manifest hop le duoc pass
- [ ] Da tu viet 1 custom `ConstraintTemplate`
- [ ] Custom policy co test reject va pass
- [ ] Moi thay doi da commit/push
- [ ] ArgoCD dang `Synced`

## Thu tu lam de nhanh nhat

1. Chot repo fork va xac nhan W9 xanh.
2. Lam RBAC va test bang `kubectl auth can-i`.
3. Cai Gatekeeper.
4. Bat `warn` cho 4 constraint, sua workload nao dang vi pham.
5. Chuyen sang `deny`, test reject/pass.
6. Lam custom policy.
7. Commit lan cuoi, sync ArgoCD, chup ket qua nghiem thu.
