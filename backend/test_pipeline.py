import asyncio
from services.agents.pipeline_graph import build_pipeline_graph
from langgraph.checkpoint.memory import MemorySaver

async def main():
    graph = build_pipeline_graph().compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test"}}
    state = {"topic": "AI in healthcare", "user_id": "test"}
    
    async for output in graph.astream(state, config=config, stream_mode="updates"):
        print("OUTPUT TYPE:", type(output))
        print("OUTPUT:", output)
        for k, v in output.items():
            print(f"Key {k} is type {type(v)}")

if __name__ == "__main__":
    asyncio.run(main())
