# Security

- kubeconfig, OpenShift token, registry token, 실제 S3 credential, 모델 binary와 민감한 dataset을 commit하지 않는다.
- Task 02는 HTPasswd/OAuth Secret을 수정하지 않는다. 연습용 OpenShift User 객체, Group과 RHOAI `Auth`만 사용한다.
- Task 02 시작 전에 `Auth.spec`, 전체 Group 목록, ClusterRoleBinding을 검증된 JSON으로 로컬 state directory에 원자적으로 백업하고 `finish/reset`에서 관련 변경을 복원한다. 완전한 백업 표식이 없으면 cleanup은 전역 리소스를 변경하지 않는다.
- Task 01·02는 start가 실제 생성한 User 이름을 task별 `created-users.txt`에 기록하고 각 문제의 허용된 이름만 삭제한다. 기존 User, identity, HTPasswd 항목은 삭제하지 않는다.
- Task 05 채점의 일회성 Job은 Workbench가 중지된 경우에만 PVC를 read-only로 mount한다. Workbench ServiceAccount를 상속하지 않고 ServiceAccount token 자동 mount를 끈다. image pull에 필요한 Secret 이름만 전달하며, task-owned label을 확인한 exact Job만 삭제하고 저장 파일은 변경하지 않는다.
- Task 08·09·11에서 fixture가 새로 만든 S3 bucket은 로컬에 보관한 무작위 token과 bucket 안의 ownership object가 정확히 일치할 때만 전체 삭제한다. 누락·불일치 시 cleanup은 bucket을 변경하지 않고 중단한다.
- Task 10은 예약한 exact 가상환경 경로 안의 ownership marker를 먼저 확인한 뒤에만 recursive delete한다. symlink나 marker가 다른 경로는 삭제하지 않는다.
- Task 12의 compatibility Secret은 공식 Lab의 S3 Secret에서 필요한 네 값만 복제하고 Dashboard Connection으로 노출하는 annotation은 추가하지 않는다. cleanup은 task-owned label이 일치하는 exact Secret만 삭제한다.
- 문서의 `minio/minio123`과 교실 registry 로그인은 AI267 공식 학습 환경에서 제공되는 연습 값이다. 다른 환경의 실제 비밀값으로 교체해 저장소에 commit하지 않는다.

노출이 의심되면 저장소 소유자에게 비공개로 알리고 해당 credential을 즉시 회전한다.
