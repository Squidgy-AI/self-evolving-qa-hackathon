"""BAND agents for the Evolution Loop system.

Four role-based agents that collaborate in a BAND room:
- @Grader: Asks deepwiki and scores answers (calls engine.loop.grade)
- @Researcher: Recalls fixes or researches new ones (calls engine.loop.research)
- @Verifier: Validates citations and measures improvement (calls engine.loop.verify)
- @Publisher: Publishes to Senso and remembers outcomes (calls engine.loop.promote)

Each agent calls exactly one function from engine.loop. The BAND room provides the
audit trail — judges watch the @-mentions happen live instead of reading logs.
"""

__all__ = [
    "grader_agent",
    "researcher_agent",
    "verifier_agent",
    "publisher_agent",
]
