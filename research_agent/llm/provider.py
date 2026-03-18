# llm/provider.py
"""
LLM factory — single place to configure the model provider.
Swap out ChatGroq for any other LangChain-compatible LLM here.
"""
import boto3
from pydantic import BaseModel
from research_agent.config import LLMConfig
from langchain_aws import ChatBedrockConverse


def get_llm_with_structure(
    output_model: type[BaseModel],
    temperature: float = LLMConfig.DEFAULT_TEMPERATURE,
):
    """
    Return a LangChain LLM bound to *output_model* for structured output.

    Parameters
    ----------
    output_model : Pydantic BaseModel subclass
        The expected response schema.
    temperature : float
        Sampling temperature (default from LLMConfig).

    Returns
    -------
    A runnable that returns an instance of *output_model*.
    """
    llm = ChatBedrockConverse(
                            model_id=LLMConfig.MODEL,
                            region_name= "us-east-1",
                            temperature=temperature

                        )
    return llm.with_structured_output(output_model)






