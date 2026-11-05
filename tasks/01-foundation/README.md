# Task 01 · 플랫폼·사용자·프로젝트·S3

기존 프로젝트·RBAC·S3 문제를 유지하면서 V2.13 번호형 실습의 RHOAI 설치 확인, Dashboard 사용자/관리자 제한, 프로젝트 협업 권한을 같은 문제에 추가한다. `ai267 start 01`은 `ex267-fraud`와 합성 CSV, 전용 MinIO bucket/credential, 기존 `Auth/auth` 복원본만 준비한다. 그룹·권한·S3 답안은 자동으로 만들지 않는다.

> 공유 클러스터에서는 설치 제거를 하지 않는다. 이미 설치된 Operator와 `DataScienceCluster`를 검증한다. 빈 전용 클러스터에서 설치부터 연습할 때만 [FRESH-CLUSTER-INSTALL.md](FRESH-CLUSTER-INSTALL.md)를 사용한다.

## 시험 제공값

- `exam-provided-minio` Secret: Task 01 전용 endpoint, bucket, access key, secret key
- `fraud-input-contract` ConfigMap: `input/transactions.csv`로 올릴 합성 CSV
- `exam-provided-identity` ConfigMap: 그룹과 RBAC subject 계약
- `exam-provided-auth-backup` ConfigMap: `ai267 finish/reset 01`이 기존 Dashboard 접근 설정을 복원할 때만 사용
- `developer1`, `rajan`, `punit`, `suraj`, `raja`, `andrew`는 RBAC/Auth subject다. 로그인 계정을 만들거나 HTPasswd Secret을 수정하지 않는다.

## 수행 목표

1. 설치된 Red Hat OpenShift AI Operator의 CSV가 `Succeeded`인지 확인하고, 하나 이상의 `DataScienceCluster`가 Ready/Managed인지 확인한다. RHOAI Dashboard도 열어 본다. 실제 이름과 관리 구성 요소를 `platform-evidence`에 기록한다.
2. `devops-wala` Group을 만들고 멤버를 정확히 `developer,rajan,punit`으로 제한한다. `rhoai-exam-admins` Group의 멤버는 정확히 `raja,andrew`로 한다. `suraj`은 관리자 그룹이 아니라 아래 프로젝트 범위 `edit` 사용자다. 두 Group에 `ex267.practice/task=01` 라벨을 붙인다.
3. RHOAI 3.3의 `Auth/auth`에서 일반 사용자 그룹은 `devops-wala`, 관리자 그룹은 `rhoai-exam-admins`만 허용한다. `system:authenticated` 같은 전체 허용 그룹은 남기지 않는다.
4. `ex267-fraud`에 `team=northstar-risk`, `environment=exam` 라벨을 설정한다.
5. 프로젝트 범위에서 `developer1`과 `suraj`에는 `edit`, `rajan`과 `punit`에는 `admin`을 부여한다. 이 사용자들에게 `cluster-admin`은 부여하지 않는다.
6. `fraud-s3`를 S3 data connection으로 완성한다. annotation은 `opendatahub.io/connection-type-protocol=s3`이고, 값은 `exam-provided-minio`의 실제 제공값이어야 한다.
7. 제공 CSV를 `input/transactions.csv`로 업로드하고 고유 결과 object를 쓴다. 새 프로세스에서 두 object를 다시 읽어 각각 SHA-256을 계산한다.
8. `platform-evidence`, `identity-evidence`, `fraud-s3-evidence`의 TODO/false 값을 실제 관찰값으로 바꾼다.

## Console 위치

- Operator 상태: OpenShift Console **Operators → Installed Operators → Red Hat OpenShift AI**
- DataScienceCluster: **Operators → Installed Operators → Red Hat OpenShift AI → Data Science Cluster**
- RHOAI Dashboard: OpenShift Console 앱 실행기 **Red Hat OpenShift AI**
- Dashboard 접근 그룹: RHOAI **Settings → User management**에서 사용자/관리자 그룹 지정
- Group: OpenShift Console **User Management → Groups**
- 프로젝트 권한: RHOAI **Projects → ex267-fraud → Permissions** 또는 OpenShift **User Management → RoleBindings**
- S3 연결: RHOAI **Projects → ex267-fraud → Connections → Add connection → S3 compatible object storage**
- 제공 Secret/증적: OpenShift **Workloads → Secrets/ConfigMaps**, project `ex267-fraud`

CLI를 사용할 때도 결과는 같은 리소스여야 한다. `Auth` 편집 전에는 `oc explain auth.spec --api-version=services.platform.opendatahub.io/v1alpha1`로 현재 스키마를 확인한다.

```bash
ai267 grade 01
ai267 finish 01   # 만점이면 Auth를 복원하고 Group/namespace를 정리
```

채점기는 Secret의 평문을 출력하지 않는다.

