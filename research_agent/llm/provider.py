# llm/provider.py

from pydantic import BaseModel
from langchain_aws import ChatBedrockConverse
from research_agent.config import LLMConfig




def get_llm_with_structure(
    output_model: type[BaseModel],
    temperature:  float = LLMConfig.DEFAULT_TEMPERATURE,
):
    """Primary LLM with structured output."""
    llm = ChatBedrockConverse(
        model_id=LLMConfig.MODEL,
        region_name=LLMConfig.AWS_REGION,
        temperature=temperature,
    )
    return llm.with_structured_output(output_model)


def get_fallback_llm(
    output_model: type[BaseModel],
    temperature:  float = LLMConfig.DEFAULT_TEMPERATURE,
):
    """Fallback LLM with structured output — used when primary fails or returns None."""
    llm = ChatBedrockConverse(
        model_id=LLMConfig.FALLBACK_MODEL,
        region_name=LLMConfig.AWS_REGION,
        temperature=temperature,
    )
    return llm.with_structured_output(output_model)