# Task 03 — Hardware Profile과 Git 작업

원문 `02-01-workbench-size.md`와 `02-03 Workbenchsize.md`를 통합했다. RHOAI 3.3에서는 `OdhDashboardConfig.spec.notebookSizes`를 수정하지 않고 `HardwareProfile`을 사용한다. `ai267 03`은 `lab start workbench-creating`과 함께 연습용 `Large`, `X Large` 프로필을 준비한다.

## 요구 사항

1. 제공된 `Large`, `X Large` 프로필을 삭제하거나 `opendatahub.io/disabled: "true"`로 비활성화한다.
2. 프로젝트 범위 Hardware Profile `medium-small`을 만든다.
   - 표시 이름: `MediumSmall`
   - CPU: 최소 1, 기본 1, 최대 2
   - 메모리: 최소·기본·최대 모두 `16Gi`
3. 프로젝트 범위 Hardware Profile `my-medium`을 만든다.
   - 표시 이름: `My-medium`
   - CPU: 최소 1, 기본 1, 최대 2
   - 메모리: 최소 1Gi, 기본 1Gi, 최대 2Gi
4. Workbench `manage-resources-wb`를 `Jupyter | Data Science | CPU | Python 3.12` 이미지와 사용 가능한 **Small** profile로 만든다. `my-medium`은 새 선택지로 제공되는지만 확인하며 이 Workbench에 적용할 필요는 없다.
5. `https://github.com/RedHatTraining/AI26X-apps.git`을 복제하고 `RHOAI3.3` 브랜치를 checkout한다.
6. `AI26X-apps/workbench/working/experiment1.ipynb`를 만들고 원문과 동일한 다음 코드로 `y=x²` 산점도를 표시한다. Cell을 실행해 `fig.show()`의 출력도 Notebook에 저장한다.

```python
import numpy as np
import plotly.express as px

# x-axis data points
x = np.linspace(start=-50, stop=50)

# y-axis data points
y = x ** 2

# define the plot
fig = px.scatter(x=x, y=y)

fig.show()
```

7. feature branch `experiment`에서 파일을 commit한 뒤 로컬 `RHOAI3.3` 브랜치에 병합하고 worktree를 clean 상태로 만든다.

## Console 위치

- Profile: **Settings → Hardware profiles** 또는 프로젝트의 **Settings → Hardware profiles**
- Workbench: **Projects → workbench-creating → Workbenches**
- Git: JupyterLab 왼쪽의 **Git** 패널

완료 후 다음을 실행한다.

```bash
ai267 grade 03
ai267 finish 03
```
