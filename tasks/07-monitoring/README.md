# Task 07 · TrustyAI·플랫폼 모니터링

1Gi PVC와 monitoring evidence 계약이 제공된다.

## 수행 목표

1. `resources/trustyai-starter.yaml`을 환경에 맞게 적용하고 capture path를 실제 요청으로 검증한다.
2. protected attribute, favorable outcome, groups, threshold, window, 최소 표본을 정의한다.
3. versioned reference dataset digest와 current window로 drift를 계산한다.
4. request latency/error와 CPU/memory/accelerator panel을 같은 시간 범위로 연결한다.
5. owner, rollback condition, redaction, retention, access policy를 기록한다.

모든 외부 증적은 URL/이름/digest만 `monitoring-evidence`에 저장한다.

```bash
../../exam-lab.sh grade 07
```

