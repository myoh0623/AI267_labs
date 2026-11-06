# Task 09 · Guardrailed RAG

`prepare`는 AI267 v3.3 Chapter 09의 mock LLM, read-only 도구, RAG 애플리케이션을 이 문제의 namespace에 배치한다. 기본 앱의 Ready/Route는 제공 환경이므로 채점하지 않으며, 응시자는 이 baseline을 권한·증적 관점에서 강화한다.

문서 source/revision/ACL/embedding 입력 계약은 `exam-provided-rag-inputs`에 별도로 제공된다. 계산한 index digest와 권한·보안 시험 결과는 응시자가 기록한다.

## 수행 목표

1. source ID/revision/ACL/embedding revision/index digest를 `rag-evidence`에 기록한다.
2. retrieval 전에 ACL을 적용하고 unauthorized retrieval이 0건임을 확인한다.
3. streaming 응답과 구조적 citation의 digest를 기록한다.
4. `rag-app` ServiceAccount용 최소 Role/RoleBinding과 NetworkPolicy를 만든다.
5. tool을 read-only typed schema, timeout, step limit, audit로 제한한다.
6. direct/indirect injection, unauthorized document, malformed argument, outage, false positive 6개 시험을 모두 PASS로 기록한다.

```bash
../../exam-lab.sh grade 09
```

