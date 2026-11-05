# Security

Do not commit kubeconfig files, OpenShift tokens, object-storage credentials, model registry credentials, raw sensitive datasets, or model binaries.

The seed manifests intentionally contain placeholder Secret keys only. Learners must enter real values in their own OpenShift environment and must not add those values back to this repository.

Report a suspected credential exposure by contacting the repository owner privately and rotate the affected credential immediately.
