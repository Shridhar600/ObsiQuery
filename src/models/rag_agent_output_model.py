from pydantic import BaseModel, Field
from typing import Optional, List

class VectorSearchOutputSchema(BaseModel):
    """
    Defines the structured output for a Search Strategist agent.
    This schema translates a mission briefing into precise vector search parameters.
    """
    
    refined_query_for_vector_search: str = Field(
        ..., # The '...' makes this a required field
        description=(
            "Synthesize the 'User Intent' and 'Information Required' from the mission briefing "
            "into a single, powerful query optimized for semantic vector search."
        )
    )
    
    filenames_filter: Optional[List[str]] = Field(
        default=None,
        description=(
            "A list of exact filenames to narrow the search. CRUCIALLY, only include filenames "
            "if the briefing provides strong, direct evidence. If unsure, you MUST return `null`."
        )
    )

    filter_rationale: str = Field(
        ...,
        description=(
            "A concise, one-sentence explanation for your decision on the `filename_filter`. "
            "If you included files, state *why* (e.g., 'The briefing's 'Contextual Nuances' "
            "explicitly mentioned the Project Phoenix PRD.'). If you returned `null`, state why "
            "(e.g., 'The briefing was general and provided no evidence for specific files.')."
        )
    )