from app.agent import DataAnalysisAgent

async def main():
    agent = DataAnalysisAgent()
    result = await agent.analyze(
        project_id="123",
        query="What is the average sales by product category?"
    )
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())