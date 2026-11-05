# Task 02 · Workbench·Custom Image·Git·S3

기존 `risk-lab`의 PVC·자원·재현성 문제는 그대로 유지한다. 여기에 번호형 실습의 Custom Workbench Image, Workbench size, 기존 Workbench 수정, JupyterLab Git 협업, S3 data connection, idle culling을 추가한다.

`ai267 start 02`는 불완전한 `git-experiments`, 10Gi/2Gi PVC, 합성 실험 코드, Containerfile/requirements, 전용 MinIO bucket/credential을 준비한다. Custom Image build/import, `risk-lab`, Git 작업, S3 연결은 응시자가 수행한다. Task 시작 시 기존 cluster-wide culler 설정을 백업하며 `finish/reset`이 복원한다.

## 수행 목표

1. `inputs/custom-image`를 사용해 `custom-workbench:1.0`을 build한다. 이미지 안에 `seaborn==0.12.2`, `python-json-logger==2.0.7`이 실제 설치되어야 한다.
2. `resources/custom-image-build-starter.yaml`의 ImageStream/BuildConfig를 완성하고 binary build를 실행한다. ImageStream에는 RHOAI notebook image 라벨, package/version metadata, 실제 image reference를 넣는다.
3. RHOAI **Settings → Workbench images**에서 `custom-workbench`를 확인하고 이 이미지를 쓰는 `risk-lab` Workbench를 만든다. 10Gi `risk-lab-storage`를 `/opt/app-root/src`에 mount한다.
4. `risk-lab`의 request는 CPU 1, memory 1Gi, limit는 CPU 2, memory 2Gi로 한다. RHOAI 3.3의 `HardwareProfile`로 `MediumSmall`(CPU 1–2, memory 16Gi 고정)과 `My-medium`(CPU 1–2, memory 1–2Gi)을 만든다. V2.13의 Large/XLarge 제거는 3.3에서 이 두 namespace profile만 노출하는 방식으로 대체한다.
5. `redhat-ods-applications/notebook-controller-culler-config`에서 culling을 켜고 `CULL_IDLE_TIME=240`, `IDLENESS_CHECK_PERIOD=1`, 라벨 `ex267.practice/task=02`를 적용한 뒤 endpoint/동작을 확인한다. 공유 환경에 영향을 주므로 Task가 끝나면 반드시 `ai267 finish/reset 02`로 원래 값을 복원한다.
6. 제공된 기존 `git-experiments` Workbench의 image를 설치 환경의 CUDA Workbench image로 바꾼다. `git-experiments-env` ConfigMap에 `RANDOM_SIZE=40`을 만들고 `envFrom`으로 연결한다. 시작/검증 후 Workbench를 중지한다.
7. JupyterLab에서 `https://github.com/RedHatTraining/AI26X-apps`를 clone하고 `RHOAI3.3` branch를 checkout한다. `experiment1.ipynb`를 만들고 `experiment` 또는 `experiment2` feature branch에서 commit한 다음 `RHOAI3.3`에 merge한다. clean worktree와 두 commit SHA, notebook SHA-256을 기록한다.
8. `projects-data-connection`을 `exam-provided-minio` 값으로 완성해 `risk-lab`에 연결한다. Workbench 안의 새 프로세스에서 object를 upload/download하고 checksum을 확인한다.
9. `exam-provided-workbench-inputs/create_experiment_runs.py`로 TensorBoard run을 두 개 이상 만들고 Workbench 재시작 뒤 PVC 파일이 유지되는지 확인한다.
10. `custom-image-evidence`, `workbench-admin-evidence`, `git-collaboration-evidence`, `workbench-s3-evidence`, `workbench-evidence`의 모든 값을 실제 관찰값으로 갱신한다. image digest/SHA는 64자리 SHA-256, Git commit은 40자리 SHA여야 한다.

## Console 위치

- Build: OpenShift **Builds → BuildConfigs → custom-workbench → Start build** 또는 제공 binary build 명령
- Workbench image catalog: RHOAI **Settings → Workbench images**
- HardwareProfile: RHOAI **Settings → Hardware profiles**; 지원되지 않는 UI에서는 OpenShift **Administration → CustomResourceDefinitions → HardwareProfile → Instances**
- Workbench 생성/수정/중지: RHOAI **Projects → ex267-t02-workbench → Workbenches**
- Data connection 연결: 같은 project의 **Connections**에서 생성한 뒤 Workbench **Actions → Edit workbench → Connections**
- Git: Workbench를 열고 JupyterLab 왼쪽 **Git** 아이콘
- Culling: RHOAI **Settings → Cluster settings** 및 OpenShift **Workloads → ConfigMaps**, project `redhat-ods-applications`

Starter YAML의 `REPLACE_*`는 적용 전에 모두 바꾼다.

```bash
ai267 grade 02
ai267 finish 02
```

