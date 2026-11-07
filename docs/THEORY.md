# RHOAI 3.3 Workbench와 Model Serving

이 문서는 첨부된 `00-01 Theory.md`의 핵심 개념을 RHOAI 3.3 기준으로 정리한다. Workbench와 model-serving Pod의 역할, KServe·vLLM·OpenVINO, 단일·다중 모델 배치의 차이, 저장소·보안·모니터링을 실습에서 사용하는 용어로 설명한다.

## Workbench Pod

Workbench는 데이터 과학자가 데이터를 탐색하고 코드를 작성하며 모델을 학습·평가하는 개발 환경이다. RHOAI Dashboard에서 Workbench를 만들면 `Notebook` CR을 중심으로 Pod, PVC, Service와 인증 구성 요소가 생성된다. 사용자는 공유 Gateway를 거쳐 JupyterLab 또는 code-server에 접속한다.

Workbench에서 주로 수행하는 작업은 다음과 같다.

- 데이터 로드, 정제와 시각화
- Notebook·Python 코드 작성과 Git 협업
- 모델 학습, 평가와 실험
- 학습된 모델 artifact 생성
- S3-compatible object storage에 데이터와 모델 저장
- Elyra 또는 KFP SDK를 이용한 Pipeline 작성

Workbench 크기와 node placement는 구형 `notebookSizes` 목록이 아니라 `HardwareProfile`로 선택한다. `/opt/app-root/src`에 연결된 PVC는 Workbench Pod가 재생성되어도 Notebook과 Git 저장소를 유지한다.

## Model-serving Pod

Model-serving Pod는 완성된 모델을 메모리에 적재하고 추론 API로 제공한다. 개발용 Workbench가 없어도 S3나 OCI storage에 준비된 모델 artifact가 있으면 배포할 수 있다. RHOAI 3.3 predictive serving은 KServe `InferenceService`와 `ServingRuntime`을 중심으로 구성되며, 배포 상태·Route·autoscaling과 runtime Pod를 플랫폼이 관리한다.

Workbench와 serving Pod의 차이는 다음과 같다.

| 구분 | Workbench Pod | Model-serving Pod |
| --- | --- | --- |
| 목적 | 개발, 데이터 처리, 학습과 실험 | 운영 추론 요청 처리 |
| 사용자 접근 | JupyterLab, code-server | V2 HTTP/gRPC 또는 OpenAI-compatible inference endpoint |
| 주요 입력 | Dataset, Notebook, source code | 학습된 model artifact |
| 주요 저장소 | PVC와 S3 Connection | S3 또는 OCI model storage |
| 확장 기준 | 개발자 자원 요구 | 요청량, latency, CPU/GPU와 replica |

간단히 말하면 Workbench는 모델을 **만드는 곳**이고, serving Pod는 모델이 **요청에 응답하는 곳**이다.

## End-to-end 흐름

```text
Workbench
  → 데이터 준비와 모델 학습
  → 모델 평가
  → model artifact 생성
  → S3 또는 OCI storage에 게시
  → InferenceService / ServingRuntime 배포
  → 인증이 설정된 또는 의도적으로 공개한 inference endpoint
  → application의 inference 요청
  → monitoring과 scaling
```

실습에서는 Connection Secret이 endpoint, bucket과 자격 증명을 Workbench 또는 Pipeline에 주입한다. Secret 값을 Notebook 출력이나 Git commit에 남기지 않는다.

## KServe, vLLM과 OpenVINO

세 이름은 같은 계층의 제품이 아니다.

| 구성 요소 | 역할 | 대표 사용 사례 |
| --- | --- | --- |
| KServe | Kubernetes에서 model deployment 수명 주기, endpoint와 scaling을 관리하는 serving 계층 | Predictive model과 generative model의 배포 관리 |
| vLLM | Transformer 계열 LLM의 token generation에 최적화된 runtime | Chat, 요약, 질의응답, 높은 처리량의 text generation |
| OpenVINO Model Server | ONNX 등 predictive model을 CPU 중심으로 효율적으로 제공하는 runtime | 분류, 회귀, computer vision과 전통적 ML inference |

### KServe

KServe `InferenceService`는 model storage 위치, runtime, resource와 공개 방법을 선언한다. Controller는 필요한 Deployment, Service와 Route를 조정한다. RHOAI 3.3의 OpenVINO 실습은 KServe V2 protocol의 metadata와 infer endpoint를 사용한다.

### vLLM

vLLM은 LLM의 긴 prompt와 다수의 동시 generation 요청을 효율적으로 처리하는 runtime이다. RHOAI 3.3에서는 KServe ServingRuntime으로 배포하고 `/v1/chat/completions` 등 model·runtime이 지원하는 OpenAI-compatible API를 사용한다. PagedAttention은 KV cache를 고정 크기 block으로 관리해 memory 조각화와 낭비를 줄이고, continuous batching은 완료 시점이 다른 요청을 실행 중인 batch에서 계속 교체한다. 실제 처리량은 model 크기, context 길이, GPU 종류와 replica 수에 좌우된다. vLLM 배포에는 model weights뿐 아니라 tokenizer, configuration과 chat template 파일도 필요할 수 있다.

### OpenVINO

OpenVINO는 Intel CPU를 포함한 지원 hardware에서 predictive model inference를 최적화한다. 이 연습의 `diabetes` model처럼 ONNX artifact를 숫자 version directory에 배치하고 V2 inference API로 검증할 수 있다.

## Single-model과 Multi-model

Single-model 방식은 하나의 deployment가 하나의 model을 전담한다. model별로 CPU/GPU, replica와 scaling을 독립적으로 조정할 수 있어 큰 model, 높은 트래픽, 격리가 필요한 운영 workload에 적합하다.

Multi-model 방식은 하나의 serving 계층이 여러 작은 model을 공유해 resource 사용량을 줄이는 개념이다. 과거 RHOAI의 ModelMesh 기반 Multi-model server가 이 방식을 제공했지만 RHOAI 3.3 문제에서는 그 제거된 API를 사용하지 않는다. Task 09는 원문의 model·project·Connection·외부 Route 요구를 유지하면서 KServe RawDeployment/OpenVINO 단일 모델 배포로 수행한다.

| 비교 | Single-model | Multi-model 개념 |
| --- | --- | --- |
| 격리 | model별 deployment | runtime resource 공유 가능 |
| scaling | model별 독립적 | 공유 server 단위가 될 수 있음 |
| 적합한 workload | 큰 model, GPU, 중요 API | 작은 model이 많고 요청이 간헐적인 경우 |
| 이 저장소의 3.3 실습 | KServe RawDeployment 사용 | ModelMesh 리소스는 사용하지 않음 |

## Storage

Workbench PVC에는 Notebook, source code, 임시 dataset과 실험 결과를 둔다. Pod 자체 filesystem은 교체될 수 있으므로 보존할 파일은 PVC 아래에 둔다.

S3-compatible object storage에는 공유 dataset, Pipeline artifact와 배포할 model을 둔다. ServingRuntime은 Connection이 가리키는 bucket/path에서 model을 읽는다. model 경로는 runtime이 기대하는 layout을 따라야 하며, OpenVINO 예제는 `models/diabetes/1/model.onnx`처럼 숫자 version directory를 사용한다.

운영 환경에서는 다음을 확인한다.

- bucket과 object path가 정확한가
- Connection Secret의 endpoint, region과 credentials가 일치하는가
- Workbench나 serving ServiceAccount에 필요한 최소 권한만 있는가
- model artifact의 format과 runtime이 호환되는가
- Pipeline output과 배포 입력 사이에 checksum 또는 version 추적이 가능한가

## 접근과 보안

Workbench는 사용자 OAuth 인증과 project RBAC을 통해 접근한다. Model endpoint는 workload 요구에 따라 token 인증을 켜거나, 의도적으로 인증을 끈 external Route로 제공할 수 있다. 인증을 끄는 것은 실습 요구가 명시된 경우에만 수행한다.

기본 보안 원칙은 다음과 같다.

- 사용자·Group에는 최소 권한을 부여한다.
- S3 credentials는 Connection Secret으로 관리하고 Notebook, Pipeline 파일과 Git에 기록하지 않는다.
- TLS Route와 필요한 NetworkPolicy를 사용한다.
- 외부 Route와 token 인증 설정을 배포 후 다시 확인한다.
- 신뢰할 수 있는 image와 고정된 version 또는 digest를 사용한다.
- 로그에 prompt, 개인정보, Secret과 원본 dataset이 노출되지 않는지 확인한다.

## Monitoring과 Scaling

운영 model은 단순히 Pod가 `Running`인지만 확인해서는 안 된다. Dashboard, OpenShift metrics와 model server metrics에서 다음 항목을 관찰한다.

- 요청 수, 성공률과 오류율
- request latency와 timeout
- CPU, memory와 GPU 사용량
- Pod health, restart와 replica 수
- model load 실패와 S3 접근 오류
- LLM의 경우 time to first token(TTFT), inter-token latency(ITL), tokens per second(TPS), 대기 요청 수와 GPU memory

요청량이 증가하면 replica를 늘리거나 더 큰 Hardware Profile을 사용할 수 있다. GPU model은 GPU 수와 memory를 model 크기에 맞춰야 한다. 작은 predictive model은 CPU OpenVINO runtime이 더 경제적일 수 있다. 먼저 latency와 resource 병목을 측정한 뒤 scaling 정책을 조정한다.

## 예시

Fraud detection workflow에서는 Workbench에서 transaction data를 정리하고 classification model을 학습한 뒤 `.joblib` 또는 ONNX artifact를 S3에 저장한다. OpenVINO ServingRuntime이 model을 읽어 거래 특성을 입력받고 fraud 여부를 반환한다.

LLM workflow에서는 사전 학습된 model weights, tokenizer와 configuration을 object storage 또는 지원되는 model source에 준비한다. vLLM runtime이 GPU에 model을 적재하고 text-generation endpoint를 제공한다. Application은 prompt를 보내고 생성된 token을 받으며, 운영자는 latency, token throughput과 GPU memory를 관찰한다.

## RHOAI 3.3에서 기억할 점

- Workbench 개별 Route 대신 공유 Gateway를 통해 IDE에 접근한다.
- Workbench resource 선택에는 `HardwareProfile`을 사용한다.
- Connection은 protocol annotation이 있는 Kubernetes Secret으로 저장된다.
- Pipeline Server는 project별 `DataSciencePipelinesApplication`으로 구성된다.
- KFP 2.15.2 CLI 실습은 Python 3.13 가상환경에서 재현한다.
- Predictive serving 실습은 KServe `InferenceService`와 지원 `ServingRuntime`을 사용한다.
- 제거된 ModelMesh Multi-model server를 새 3.3 리소스처럼 만들지 않는다.
