import asyncio

from orchestrator.dag import DAG
from orchestrator.task import Task
from orchestrator.scheduler import Scheduler

async def market():
    print("Market started")
    await asyncio.sleep(2)
    print("Market completed")
    return "market result"


async def tech():
    print("Tech started")
    await asyncio.sleep(1)
    print("Tech completed")
    return "tech result"


async def finance():
    print("Finance started")
    await asyncio.sleep(1)
    print("Finance completed")
    return "finance result"


async def pitch():
    print("Pitch started")
    await asyncio.sleep(1)
    print("Pitch completed")
    return "pitch result"


async def main():

    dag  = DAG()

    dag.add_task(Task("market", market))
    dag.add_task(Task("tech", tech, dependencies = ["market"]))
    dag.add_task(Task("finance", finance, dependencies = ["market"]))
    dag.add_task(Task("pitch", pitch, dependencies = ["tech", "finance"]))

    scheduler = Scheduler(dag)
    await scheduler.execute()


if __name__ == "__main__":
    asyncio.run(main())