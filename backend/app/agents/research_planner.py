
import re


class ResearchPlannerAgent:
    """
    Creates a structured research plan from a user-provided topic.

    This initial version uses rule-based planning.
    An LLM will be integrated in a later milestone.
    """

    def create_plan(self, topic: str) -> dict:
        topic = topic.strip()

        if len(topic) < 5:
            raise ValueError("Research topic must contain at least 5 characters.")

        if len(topic) > 500:
            raise ValueError("Research topic cannot exceed 500 characters.")

        # Clean extra spaces.
        clean_topic = re.sub(r"\s+", " ", topic)

        questions = [
            f"What is {clean_topic}, and what are its key concepts?",
            f"What is the background and history of {clean_topic}?",
            f"What are the major applications and use cases of {clean_topic}?",
            f"What technologies, methods, or approaches are used in {clean_topic}?",
            f"What are the benefits and potential opportunities of {clean_topic}?",
            f"What are the limitations, challenges, and risks of {clean_topic}?",
            f"What recent developments and research trends relate to {clean_topic}?",
            f"What are the future possibilities and research directions for {clean_topic}?",
        ]

        objectives = [
            "Understand the topic and establish its fundamental concepts.",
            "Identify important developments and relevant research.",
            "Explore applications, methods, and practical use cases.",
            "Evaluate benefits, limitations, and challenges.",
            "Summarize findings and identify future research opportunities.",
        ]

        search_queries = [
            clean_topic,
            f"{clean_topic} research papers",
            f"{clean_topic} applications and challenges",
            f"{clean_topic} recent developments",
            f"{clean_topic} future trends",
        ]

        return {
            "topic": clean_topic,
            "plan_title": f"Research Plan: {clean_topic}",
            "total_questions": len(questions),
            "research_questions": questions,
            "research_objectives": objectives,
            "suggested_search_queries": search_queries,
            "research_areas": [
                "Introduction and fundamentals",
                "Background and literature",
                "Applications and methodology",
                "Benefits and challenges",
                "Recent developments",
                "Future directions",
            ],
            "status": "plan_created",
            "planner_type": "rule_based"
        }


research_planner = ResearchPlannerAgent()
