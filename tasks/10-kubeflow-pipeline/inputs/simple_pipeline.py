"""AI267 Task 10 starter pipeline, adapted to KFP 2.15.2."""

from pathlib import Path

from kfp import compiler, dsl


@dsl.component(base_image="registry.access.redhat.com/ubi9/python-312:latest")
def generate_message(name: str) -> str:
    return f"Hello {name}, welcome to Red Hat OpenShift AI pipelines"


@dsl.component(base_image="registry.access.redhat.com/ubi9/python-312:latest")
def print_message(message: str) -> None:
    print(message)


@dsl.pipeline(name="tas1-devops-wala")
def simple_pipeline(name: str = "Student") -> None:
    message_task = generate_message(name=name)
    print_message(message=message_task.output)


if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=simple_pipeline,
        package_path=str(Path(__file__).with_name("simple_rhoai_pipeline.yaml")),
    )
