# Task 05 · vLLM·GPU 배치 진단

`support-llm` Deployment는 잘못된 selector와 GPU request 누락으로 의도적으로 불완전하다.

## 수행 목표

1. Events, node label/taint, quota, allocatable GPU, PVC topology를 확인하고 최초 실패를 `vllm-evidence`에 기록한다.
2. `accelerator=nvidia-a10` selector와 `nvidia.com/gpu=present:NoSchedule` toleration을 설정한다.
3. `nvidia.com/gpu: 1`과 CPU·memory request를 설정한다.
4. 환경에서 사용 가능한 vLLM image digest와 고정 model revision으로 workload를 교체한다.
5. streaming 요청과 동시성·latency·throughput·GPU·queue·error 기준선을 기록한다.

GPU가 없는 클러스터에서는 리소스 구조와 Pending 진단까지만 연습하고, 전체 채점은 GPU가 있는 RHOAI 실습 환경에서 수행한다.

```bash
../../exam-lab.sh grade 05
```

