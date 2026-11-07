# Task 09 · Guardrailed RAG

`prepare`는 AI267 v3.3 Chapter 09의 mock LLM, 쓰기 가능한 `add_todo`를 포함한 미완성 도구, ACL/streaming이 없는 RAG 애플리케이션을 이 문제의 namespace에 배치한다. 기본 앱의 Ready/Route는 제공 환경이므로 채점하지 않으며, 응시자는 이 baseline을 직접 수정해 요구 계약을 완성한다.

문서 source/revision/ACL/embedding 입력 계약은 `exam-provided-rag-inputs`에 별도로 제공된다. 계산한 index digest와 권한·보안 시험 결과는 응시자가 기록한다.

## 수행 목표

1. source ID/revision/ACL/embedding revision/index digest를 `rag-evidence`에 기록한다.
2. retrieval 전에 ACL을 적용하고 unauthorized retrieval이 0건임을 확인한다.
3. streaming 응답과 구조적 citation의 digest를 기록한다.
4. `rag-reader` Role은 `rag-documents` ConfigMap의 `get`만 허용하고, RoleBinding은 `rag-app` ServiceAccount만 연결한다. `app=genai-app` Egress NetworkPolicy는 `mock-llm:8080`, `todo-tool:8080`, DNS 53만 허용한다.
5. `tool-service-code`와 `genai-app-code`를 수정해 tool을 read-only typed schema, timeout, step limit, audit로 제한한 뒤 `todo-tool`, `genai-app` Deployment를 rollout한다.
6. direct/indirect injection, unauthorized document, malformed argument, outage, false positive 6개 시험을 수행한다. 제공 verifier Job이 성공한 뒤 결과를 모두 PASS로 기록한다.

## 고정 동작 계약과 검증

`exam-provided-rag-inputs`의 authorized identity는 `security-reviewer`, unauthorized identity는 `external-user`다. `/rag`는 구조화된 `source_id`, `source_revision`, `document` citation을 반환하고 unauthorized 사용자의 restricted 문서를 검색하지 않아야 한다. `stream=true`는 SSE 또는 NDJSON으로 둘 이상의 event와 citation을 반환한다. `/agent`는 `add_todo`를 거부하고 argument schema, timeout, step limit, audit를 적용해야 한다. 자세한 요청/응답 계약은 변경할 수 없는 `exam-provided-rag-verifier`의 `verify_rag.py`에서 확인한다.

코드와 정책을 적용한 뒤 고정 verifier를 새로 실행한다.

```bash
oc rollout restart deployment/todo-tool deployment/genai-app -n ex267-t09-rag
oc rollout status deployment/todo-tool -n ex267-t09-rag
oc rollout status deployment/genai-app -n ex267-t09-rag
oc delete job rag-contract-verification -n ex267-t09-rag --ignore-not-found
oc apply -f tasks/09-rag/resources/verifier-job.yaml
oc wait --for=condition=complete job/rag-contract-verification -n ex267-t09-rag --timeout=180s
oc logs job/rag-contract-verification -n ex267-t09-rag
```

```bash
../../exam-lab.sh grade 09
```

