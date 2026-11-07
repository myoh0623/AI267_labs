# Task 01 — 프로젝트 권한과 Workbench

원문 `01-0301 UserPermission.md`의 프로젝트 이름·권한·Workbench 요구를 유지하고 이미지와 자원 선택만 RHOAI 3.3 방식으로 수행한다. `ai267 01`은 공식 `lab start workbench-creating`으로 의존 기능을 준비하지만 답안 프로젝트는 만들지 않는다.

## 제공 환경

- 생성할 RHOAI 프로젝트: `my-lab-pro`
- 사용자 객체: `suraj`, `rajan`, `punit`
- 전역 Hardware Profile: `Task 01 - 2 CPU, 8 GiB`
- 저장소: `https://github.com/RedHatTraining/AI26X-apps.git`

start가 만드는 User 객체는 RBAC subject용이며 암호나 OAuth identity를 만들지 않는다. 현재 `admin` 세션으로 프로젝트와 권한을 구성한다. `suraj`, `rajan`, `punit`의 실제 로그인을 요구하지 않는다.

## 요구 사항

1. Data Science Project `my-lab-pro`를 직접 만든다.
2. `my-lab-pro`의 **Permissions**에서 `rajan`과 `punit`을 **Admin**, `suraj`를 **Contributor**로 추가한다.
3. `my-lab-pro`에 Workbench `myworkbench-wb`를 만든다.
4. 이미지는 `Jupyter | PyTorch | CUDA | Python 3.12`의 **버전 `2025.2`**(PyTorch 2.7, Python 3.12)를 선택하고, Hardware Profile은 제공된 `Task 01 - 2 CPU, 8 GiB`를 선택한다.
5. 영구 스토리지 `myworkbench-wb-storage`를 `2 GiB`로 만든다.
6. ConfigMap 방식 환경 변수 이름을 `myworkbench-env`로 만들고 `var=devops-wala`를 설정한다.
7. Workbench를 시작하고 JupyterLab에서 `AI26X-apps` 저장소를 복제한다.

## Console 위치

- 프로젝트 생성: **Projects → Create project → my-lab-pro**
- 프로젝트 권한: **Projects → my-lab-pro → Permissions**
- Workbench: **Projects → my-lab-pro → Workbenches**
- 환경 변수: Workbench 생성 화면의 **Environment variables → ConfigMap**

완료 후 다음을 실행한다.

```bash
ai267 grade 01
ai267 finish 01
```

`finish`는 만점일 때만 `my-lab-pro`와 task가 제공한 profile/User 객체를 정리한 뒤 공식 `lab finish workbench-creating`을 실행한다.
