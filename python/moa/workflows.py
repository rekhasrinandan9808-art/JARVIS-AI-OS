class Workflows:

    @staticmethod
    async def research(orchestrator, topic):

        # Step 1
        plan = await orchestrator.run(
            "research",
            "plan",
            {
                "topic": topic
            }
        )

        return plan