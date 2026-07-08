from .base_workflow import BaseWorkflow


class CodingWorkflow(BaseWorkflow):

    async def run(self, code: str):

        print("[Workflow] Checking syntax...")

        result = await self.orchestrator.run_capability(
            "check_syntax",
            {
                "code": code
            }
        )

        return result