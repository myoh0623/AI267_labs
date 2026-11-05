# Task 02 · Workbench·PVC·실험 증적

`risk-lab-storage` 10Gi PVC와 승인 image digest 계약만 제공된다. OpenShift AI Console에서 `risk-lab` Workbench를 완성한다.

## 수행 목표

1. `workbench-contract`의 digest 이미지를 사용하는 `risk-lab` Notebook을 만든다.
2. PVC를 `/opt/app-root/src`에 mount한다.
3. CPU·memory request/limit을 모두 명시한다.
4. Git/data/seed/image/artifact 정보를 `workbench-evidence`에 기록한다.
5. 재시작 뒤 파일 영속성을 확인하고 TensorBoard run 2개 이상을 기록한다.

CLI starter는 `resources/notebook-starter.yaml`이다. `REPLACE_*`를 모두 바꾸기 전에는 적용하지 않는다.

```bash
../../exam-lab.sh grade 02
```

