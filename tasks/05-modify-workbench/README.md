# Task 05 — 기존 Workbench 수정

원문 `03-03 ModifyWorkbench.md`를 RHOAI 3.3의 공식 `workbench-working` 환경으로 옮겼다. `ai267 05`가 `lab start workbench-working`을 실행하며 기존 Workbench `model-training`을 제공한다. Workbench를 삭제하고 새로 만들면 안 된다.

## 요구 사항

1. `model-training`을 중지하고 편집한다.
2. 이미지를 `Jupyter | PyTorch | CUDA | Python 3.12`로 변경한다.
3. ConfigMap 환경 변수 이름을 `model-training-env`로 만들고 `RANDOM_SIZE=40`을 설정한다.
4. Workbench를 다시 시작한다.
5. JupyterLab에서 `https://github.com/RedHatTraining/AI26X-apps.git`을 복제한다.
6. `RHOAI3.3` 브랜치를 checkout하고 `workbench/working/train_model.ipynb`가 있는지 확인한다.
7. 변경 사항을 확인한 뒤 원문 지시대로 `model-training` Workbench를 **중지**한다. 상태가 **Stopped**가 된 다음 채점한다.

채점기는 중지 상태와 Pod 부재를 확인한 뒤 Workbench PVC를 read-only로 연결한 일회성 검증 Job에서 Git remote, branch, 파일만 확인하고 즉시 Job을 삭제한다. Workbench를 다시 시작하거나 PVC 내용을 변경하지 않는다.

## Console 위치

**Projects → workbench-working → Workbenches → model-training → Stop → Edit workbench**

완료 후 다음을 실행한다.

```bash
ai267 grade 05
ai267 finish 05
```
