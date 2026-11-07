# Task 02 — RHOAI 사용자·그룹 접근 제어

원문 `01-0302 Usermanagement.md`를 RHOAI 3.3의 `Auth` 리소스와 Dashboard **User management** 화면에 맞게 재구성했다. `ai267 02`는 `lab start intro-projects`를 실행하고 현재 전역 설정을 백업하며, 누락된 연습용 User 객체만 준비한다. `Auth`와 Group은 자동으로 변경하지 않는다.

start가 만드는 OpenShift `User` 객체는 Group/RBAC subject로 참조하기 위한 객체일 뿐이다. OAuth identity, HTPasswd 항목, 로그인 암호는 만들지 않는다. 이 문제의 `Auth`와 Group 설정은 현재 `admin` 세션으로 수행하며, 실제 Dashboard 로그인 확인은 클러스터에 이미 로그인 identity가 있는 `developer` 계정만 가능하다. `suraj`, `rajan`, `punit`, `raja`, `andrew`는 별도 identity가 제공되지 않는 한 로그인 시험 대상이 아니다.

## 요구 사항

1. 그룹 `devops-wala`의 구성원을 정확히 다음 세 명으로 만든다.
   - `developer`
   - `rajan`
   - `punit`
2. 그룹 `ai267-admins`의 구성원을 정확히 다음 세 명으로 만든다.
   - `suraj`
   - `raja`
   - `andrew`
3. `Auth/auth`의 RHOAI 일반 사용자 그룹은 `devops-wala`만, 관리자 그룹은 `ai267-admins`만 사용하도록 설정한다.
4. `system:authenticated` 같은 모든 로그인 사용자 허용 그룹을 제거한다.
5. `developer`, `rajan`, `punit`은 `devops-wala` 외의 **어떤 OpenShift Group에도 속하지 않아야 하며**, 직접 또는 그룹을 통해 `cluster-admin` ClusterRoleBinding의 subject가 아니어야 한다.

## Console 위치

**Settings → User management**에서 일반 사용자 그룹과 관리자 그룹을 설정한다. OpenShift 그룹 구성원은 OpenShift Console의 **User Management → Groups** 또는 `oc adm groups`로 관리할 수 있다.

`cluster-admin` 권한이 있는 사용자는 RHOAI의 별도 관리자 예외다. 이 문제의 “관리자만 허용”은 `Auth.spec.adminGroups`와 평가 대상 그룹에 대한 요구다.

완료 후 다음을 실행한다.

```bash
ai267 grade 02
ai267 finish 02
```

`finish` 또는 `reset`은 시작 전에 백업한 `Auth`, 대상 사용자들의 전체 Group membership, 관련 ClusterRoleBinding subject를 원래 상태로 복원한다. start는 이 전역 설정을 변경하지 않는다.
