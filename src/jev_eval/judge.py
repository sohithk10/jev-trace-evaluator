"""Opt-in TypeSafe integration. No trace tools are executed."""

from .core import PREFIX, RUBRICS


class JevJudge:
    def __init__(self, model="jev-latest"):
        from langchain_typesafe import Noul, TypeSafeClassifier

        self.questions = {name: Noul(instructions=PREFIX + rubric) for name, rubric in RUBRICS.items()}
        self.classifier = TypeSafeClassifier(
            model=model, base_url="https://api.typesafe.ai", timeout=30.0
        )

    def __call__(self, trace, policy):
        from langsmith import tracing_context

        # Disable implicit LangSmith uploads even if enabled in the environment.
        with tracing_context(enabled=False):
            response = self.classifier.invoke({
                "state": {"trusted_policy": policy, "untrusted_trace": trace},
                "questions": self.questions,
            }, config={"callbacks": []})
        return {name: answer.noul for name, answer in response.nouls.items()}
