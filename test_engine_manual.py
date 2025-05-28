import asyncio

from ocode_python.core.engine import OCodeEngine


async def main():
    # Use large values to test chunking and continuation
    engine = OCodeEngine(verbose=True, max_continuations=3, chunk_size=1024)
    prompt = (
        "What is this project about? Give me a brief overview of the main components."
    )
    print("\n--- BEGIN RESPONSE ---\n")

    # Process the query once - the engine will handle continuations internally
    async for chunk in engine.process(prompt):
        print(f"[CHUNK] {chunk}")

    print("\n--- END RESPONSE ---\n")


if __name__ == "__main__":
    asyncio.run(main())
