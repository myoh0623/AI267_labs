# Task 07 — Git Notebook 협업

원문 `06-01 Collaboration with Jupyter Notebooks.md`의 범위인 새 Notebook 추적과 feature branch 병합을 RHOAI 3.3 `workbench-working` 환경에서 수행한다. `ai267 07`이 `lab start workbench-working`을 실행한다.

## 요구 사항

1. Workbench `model-training`에서 `https://github.com/RedHatTraining/AI26X-apps.git`을 복제한다.
2. 원격 `RHOAI3.3`을 기준으로 로컬 브랜치 `RHOAI3.3`을 만든다.
3. `RHOAI3.3`이 아닌 원하는 이름으로 feature branch를 만든다.
4. 저장소 안의 원하는 위치에 새 `.ipynb` Notebook을 만든다. 원격 `RHOAI3.3`에 이미 있는 Notebook을 수정하는 것만으로는 새 Notebook을 추적한 것이 아니다.
5. JupyterLab **Git** panel에서 새 Notebook을 track하고 feature branch에 commit한다.
6. feature branch를 로컬 `RHOAI3.3`에 병합한다.
7. 최종 checkout branch를 `RHOAI3.3`으로 두고 worktree를 clean 상태로 만든다.

feature branch와 Notebook 파일 이름은 자유다. 채점기는 원격 `RHOAI3.3` 이후의 commit이 있는 로컬 feature branch, 그 branch에서 새로 추가된 `.ipynb`, 로컬 `RHOAI3.3`으로의 병합 상태를 Git 이력으로 확인한다. 이 원문 문제는 Notebook 실행 결과 저장을 요구하지 않으므로 cell 실행 여부는 채점하지 않는다.

입력 차원 수정, `Dense(2e6)` 변경, OOM 진단은 3.3 EPUB의 별도 `workbench-working` Guided Exercise 내용이며 이 원문 문제의 요구가 아니므로 채점하지 않는다.

완료 후 다음을 실행한다.

```bash
ai267 grade 07
ai267 finish 07
```
