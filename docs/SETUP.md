# RHOAI 3.3 사전조건

이 문서는 채점 문제가 아니다. AI267 3.3 과정 Lab을 실행할 수 있는 학습 클러스터가 준비되어 있는지만 확인한다.

## 버전 기준

- AI267 3.3 EPUB의 공식 course baseline: OpenShift `4.20`
- 이 연습 저장소가 지원하는 교실 환경: OpenShift `4.19.9` 이상 중 RHOAI 3.3 지원 조합

교재의 화면과 공식 Guided Exercise 설명은 4.20을 기준으로 한다. 현재 연습 클러스터처럼 4.19.9를 사용하는 경우에도 아래 API와 RHOAI 3.3 구성 요소가 실제로 제공되어야 한다. 단순히 OpenShift 버전 숫자만으로 호환성을 판단하지 않는다.

## 요구 환경

- Red Hat OpenShift AI Operator `stable-3.x`
- `rhods-operator` 3.3.x CSV `Succeeded`
- `DataScienceCluster` v2 `Ready`
- AI267 3.3 course와 `lab` CLI
- `oc`, `python3`, `git`, `podman` 또는 `docker`, `uv`
- 교실 registry와 MinIO 접근

RHOAI 3.3의 기본 predictive serving 연습은 KServe RawDeployment다. 구형 문서처럼 Serverless Operator나 ModelMesh를 이 문제 묶음 때문에 추가 설치하지 않는다.

## 확인

```bash
lab list
lab version
oc whoami
oc get csv -A | grep rhods-operator
oc get datasciencecluster -A
oc get auth.services.platform.opendatahub.io auth
oc api-resources | grep -E 'HardwareProfile|Notebook|InferenceService|DataSciencePipelinesApplication'
```

Dashboard 주소는 고정 문자열이 아니라 현재 cluster domain의 `data-science-gateway` Route를 사용한다.

```bash
oc get route -A | grep data-science-gateway
```

## 연습 도구 설치

```bash
git clone https://github.com/myoh0623/AI267_labs.git
cd AI267_labs
bash install-ai267.sh
ai267 list
```

로그인 kubeconfig가 `$HOME/.auth/lab-kubeconfig`에 있으면 wrapper가 자동으로 사용한다. 다른 위치라면 `KUBECONFIG`를 명시한다.
