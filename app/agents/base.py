from .planner import create_plan
from .critic import review_plan
import asyncio


async def main():
    idea = "AI-powered personalized education platform"

    plan = await create_plan(idea)
    print(plan)

    review = await review_plan(idea, plan)
    print(review)

    if not review.valid:
        plan = await create_plan(f"""
        Fix this plan:
        {plan}
        Issues: {review.issues}
        Suggested_fix: {review.suggested_fix}
        """)

        print(plan)

if __name__ == "__main__":
    asyncio.run(main())
