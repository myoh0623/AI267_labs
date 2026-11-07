# Task 06 — Custom Workbench Image

원문 `05-00 Create a Custom Notebook Image.md`와 `05-03 CustomImage.md`의 공통 이미지 build 과정은 합치고, 두 번째 문서에만 있는 설명·software·package metadata 요구도 유지했다. `ai267 06`은 공식 `lab start workbench-custom`을 실행한다.

## 요구 사항

1. 워크스테이션에서 `~/course/labs/workbench-custom`으로 이동한다.
2. 제공된 `requirements.txt`에 다음 두 패키지를 추가한다.
   - `seaborn==0.13.2`
   - `python-json-logger==2.0.7`
3. 제공된 Containerfile로 이미지를 한 번 build한 뒤, 두 원문에서 요구한 이름을 모두 같은 image에 tag하고 registry에 둘 다 push한다.
   - `registry.lab.example.com:8443/developer/custom-workbench:1.0`
   - `registry.lab.example.com:8443/developer/custom-workbench-image:1.0`
4. RHOAI 관리자 화면에서 이미지를 Workbench image로 가져온다.
   - Image location: `registry.lab.example.com:8443/developer/custom-workbench-image:1.0`
   - 표시 이름: `custom-workbench`
   - 설명: `The image provides the seaborn Python package.`
   - Software: `Python`, 버전 `3.12`
   - Package: `seaborn`, 버전 `0.13.2`
   - Package: `python-json-logger`, 버전 `2.0.7`
5. 프로젝트 `workbench-custom`에서 Workbench `custom-wb`를 이 이미지로 만든다.
6. Workbench 안에서 `seaborn.__version__`이 `0.13.2`이고 `importlib.metadata.version("python-json-logger")`가 `2.0.7`인지 실제로 확인한다.

`05-00`의 image 이름 `custom-workbench:1.0`과 `05-03`의 `custom-workbench-image:1.0`은 어느 하나를 버리지 않고 동일 image의 두 tag로 보존한다. `seaborn 0.13.2`와 `Python 3.12`는 공식 AI267 3.3 `workbench-custom` Containerfile·Lab에 필요한 버전 적응이다. 원문의 `Python v2.2.0` 표기는 Python 버전이 아니므로 3.3 기반 image의 실제 Python 버전으로 대체했다. 화면의 package metadata만 추가해서는 패키지가 설치되지 않으므로 두 패키지가 모두 `requirements.txt`에 있어야 한다.

## Console 위치

- 이미지 등록: **Settings → Environment setup → Workbench images**
- Workbench 생성: **Projects → workbench-custom → Workbenches**

완료 후 다음을 실행한다.

```bash
ai267 grade 06
ai267 finish 06
```
