# Task 09 — OpenVINO `diabetes` 모델 배포

원문 `07-03 Modal.md`의 `tiger` 프로젝트와 `diabetes` 모델 요구를 유지한다. RHOAI 3.3에서 제거된 ModelMesh **Multi-model server만** KServe RawDeployment 단일 모델 방식으로 바꾼다. `ai267 09`는 공식 `lab start serving-openvino`을 실행하고, 문제 입력인 작은 ONNX 모델을 MinIO에 준비한다.

## 제공 환경

- 공식 참고 Workbench: `serving-openvino/serving-openvino-wb`
- MinIO endpoint: `https://minio-api-minio.apps.lab.example.com`
- Access key / Secret key: `minio` / `minio123`
- Region: `us-east-1`
- Bucket: `models-bucket`
- 제공 모델: `models/diabetes/1/model.onnx`

제공 모델은 배포 절차 연습용 합성 이진 분류 모델이다. `1/`은 OpenVINO가 요구하는 숫자 버전 디렉터리다.

## 요구 사항

1. Data Science Project `tiger`를 만든다.
2. `tiger`의 **Connections**에서 S3 연결 `rhoaiserving-using`을 만든다.
   - 위에 제공된 endpoint, 자격 증명, region을 사용한다.
   - Bucket은 `models-bucket`이다.
3. **Deployments**에서 다음 단일 predictive model을 배포한다.
   - Existing connection: `rhoaiserving-using`
   - Path: `models/diabetes`
   - Model type: `Predictive model`
   - Deployment name: `diabetes`
   - Framework: `onnx - 1`
   - External route: 활성화
   - Token authentication: **비활성화**
4. 배포 상태가 `Started`인지 확인한다.
5. 외부 route의 `/v2/models/diabetes` metadata endpoint에서 입력 정보를 확인한다.
   - input name: `float_input`
   - datatype: `FP32`
   - shape: `[-1, 5]`
6. `/v2/models/diabetes/infer`에 다음 형식의 요청을 인증 토큰 없이 보내고 정상 응답을 확인한다.

```json
{
  "inputs": [
    {
      "name": "float_input",
      "shape": [1, 5],
      "datatype": "FP32",
      "data": [[0.2, -0.1, 0.5, 1.0, -0.4]]
    }
  ]
}
```

원문의 프로젝트·모델·연결 이름과 인증 비활성 요구는 그대로다. 3.3에서 지원되지 않는 `multimodel-server` 리소스만 만들지 않는다.

완료 후 다음을 실행한다.

```bash
ai267 grade 09
ai267 finish 09
```

`finish/reset`은 `tiger` 프로젝트와 이 문제에서 제공한 합성 S3 객체를 정리하고, 시작 전에 같은 객체가 있었다면 원본을 복원한다.
