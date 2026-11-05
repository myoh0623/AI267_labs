# 전용 빈 클러스터용 RHOAI 3.3 설치 연습

이 문서는 **폐기 가능한 빈 전용 클러스터**에서만 사용한다. 기존 실습/공유 클러스터에서 Operator, CRD, namespace를 제거하지 않는다. Task 01의 기본 흐름은 설치를 변경하지 않고 현재 상태를 검증하는 것이다.

## Web Console 절차

1. cluster-admin으로 OpenShift Console에 로그인한다.
2. **Operators → OperatorHub**에서 `Red Hat OpenShift AI`를 검색한다.
3. 지원되는 3.x channel과 기본 설치 namespace를 선택해 설치하고 CSV가 `Succeeded`가 될 때까지 기다린다.
4. 설치된 Operator의 **Data Science Cluster** 탭에서 `default-dsc`를 만든다. 필요한 구성 요소는 `Managed`로 둔다.
5. `oc get datasciencecluster -o yaml`에서 Ready 조건과 각 component의 관리 상태를 확인한다.
6. 앱 실행기의 **Red Hat OpenShift AI**를 열어 Dashboard 로그인이 되는지 확인한다.
7. Serverless/Service Mesh가 필요한 advanced serving 과제를 별도로 연습할 때만 해당 Operator를 설치한다. 이 연습 묶음의 Task 04는 RHOAI 3.3 `RawDeployment`이므로 Task 01을 위해 임의 설치하지 않는다.

## 읽기 전용 검증

```bash
oc get subscription,csv -n redhat-ods-operator
oc get datasciencecluster -o wide
oc get datasciencecluster -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'
oc get pods -n redhat-ods-applications
oc get routes -n redhat-ods-applications
```

설치/제거 자체는 `ai267 reset`의 관리 범위가 아니다. 설치 검증 결과만 Task 01의 `platform-evidence`에 기록한다.

