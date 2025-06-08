from pydantic import BaseModel, Field
from typing import Optional,List

class VectorSearchOutputSchema(BaseModel):
    """
    Defines the structured output for deriving vector search parameters.
    This schema is used by an LLM to specify how to query the vector database.
    """
    
    refined_query_for_vector_search: str = Field(
        description=(
            "A concise, semantically rich query string optimized for vector similarity search. "
            "This query should capture the core intent of the original user request, "
            "potentially rephrased or expanded with keywords for better retrieval from the notes."
        )
    )
    
    filter_by_filenames: Optional[List[str]] = Field(
        default=None,
        description=(
            "An optional list of one or more filenames to filter the vector search. "
            "The search will be restricted to chunks originating from these specified files. "
            "If multiple filenames are provided, it implies an OR condition (retrieve from fileA OR fileB OR ...). "
            "If the LLM identifies a single most relevant file, provide it as a list with one item (e.g., ['my_specific_note.md']). "
            "If no specific files can be confidently identified as exclusively relevant, leave this field null or an empty list."
        )
    )

        # filter_by_filenames: Optional[Union[str, List[str]]] = Field(
    #     default=None,
    #     description=(
    #         "An optional filename or list of filenames to filter the vector search. "
    #         "If a single string, filter by that one file. If a list, filter by any of the files in the list (OR condition). "
    #         "If no specific files can be confidently identified, leave this null."
    #     )
    # )
    