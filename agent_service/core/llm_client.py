from re import match
from loguru import logger
import os
import aiohttp
from typing import Dict, Any, List

from agent_service.core.model_router import ModelRouter


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

TOKEN_LIMITS = {

    "architect": 8000,
    "finance": 8000,
    "evaluator": 8000,
    "market": 4000,
    "product": 4000,
    "execution": 4000,
    "ml": 4000
}

# DEBUG: Check if API key exists
from loguru import logger
if not OPENROUTER_API_KEY:
    logger.error("LLM Client: Global OPENROUTER_API_KEY is NOT set in environment!")
else:
    logger.info(f"LLM Client: Global OPENROUTER_API_KEY is set (starts with {OPENROUTER_API_KEY[:4]}...)")


class LLMclient:

    async def generate(
        self, 
        agent_name: str,
        messages: List[Dict[str, str]],
        temperature : float = 0.3,
        api_key: str = None,
        capability: str = None
    ) -> str:

        # Use personal API key if provided, otherwise fallback to system key
        current_api_key = api_key if api_key else OPENROUTER_API_KEY
        
        if not current_api_key or current_api_key == "your_key_here":
            raise Exception("No valid OpenRouter API Key provided. Please add your key in Settings.")

        models_to_try = [
            ModelRouter.get_model(capability=capability, agent_name=agent_name)
        ]
        
        max_tokens = TOKEN_LIMITS.get(
            agent_name,
            1500
        )
        
        for model in models_to_try:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        OPENROUTER_URL,
                        headers = {
                            "Authorization" : f"Bearer {current_api_key}",
                            "Content-Type" : "application/json"
                        },
                        json = {
                            "model": model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        }
                    ) as response:


                        if response.status != 200:
                            error_text = await response.text()
                            from loguru import logger
                            logger.error(f"OpenRouter API error {response.status}: {error_text}")
                            continue

                        data = await response.json()

                        return data["choices"][0]["message"]["content"]

            except Exception as e:
                from loguru import logger
                logger.error(f"Error calling LLM: {str(e)}")
                continue

        raise Exception("All models failed. Please check the logs above for OpenRouter API errors.")    

    async def generate_structured(
        self,
        agent_name: str,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        temperature: float = 0.0,
        api_key: str = None,
        capability: str = None
    ) -> Dict[str, Any]:
        """Ensures the LLM returns a response that matches the provided JSON schema."""
        import json
        import re
        import asyncio

        # Add JSON mode instruction to system prompt
        if not any("json" in m.get("content", "").lower() for m in messages):
            messages[0]["content"] += f"""

            REQUIRED JSON SCHEMA:
            {json.dumps(schema, indent=2)}

            CRITICAL: Return ONLY valid JSON matching this schema. 
            Do NOT include any conversational text, explanations, or notes before or after the JSON.
            """
        current_api_key = api_key if api_key else OPENROUTER_API_KEY
        
        if not current_api_key or current_api_key == "your_key_here":
            raise Exception("No valid OpenRouter API Key provided. Please add your key in Settings.")
        
        primary_model = ModelRouter.get_model(
            capability=capability,
            agent_name=agent_name
        )
        # Diverse fallback: each model has its own rate limit
        ALL_MODELS = [
            "google/gemini-2.0-flash:free",
            "google/gemini-2.0-flash-lite-preview-02-05:free",
            "openai/gpt-4o-mini",
            "z-ai/glm-4.5-air:free",
            "openai/gpt-oss-120b:free",
            "openrouter/free",
            "google/gemma-2-9b-it:free",
            "meta-llama/llama-3.1-8b-instruct"
        ]
        
        models_to_try = [primary_model]
        for m in ALL_MODELS:
            if m not in models_to_try:
                models_to_try.append(m)
        models_to_try = models_to_try[:4]
        
        max_tokens = TOKEN_LIMITS.get(
            agent_name,
            1500
        )

        # 180 second timeout for heavy reasoning models
        timeout_seconds = 180 if agent_name in [
            "architect",
            "finance",
            "evaluator"
        ] else 120

        timeout = aiohttp.ClientTimeout(
            total=timeout_seconds
        )
        
        # Global Retry Loop (2 attempts at the entire model list)
        for global_attempt in range(2):
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for model in models_to_try:
                    try:
                        logger.info(f"LLM Attempt: {agent_name} using {model} (Global Attempt {global_attempt + 1})")
                        payload = {
                            "model": model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "response_format": {
                                "type": "json_object"
                            }
                        }
                    
                        async with session.post(
                            OPENROUTER_URL,
                            headers={"Authorization": f"Bearer {current_api_key}", "Content-Type": "application/json"},
                            json=payload
                        ) as response:
                            
                            # Handle Rate Limit on first attempt
                            if response.status == 429:
                                try:
                                    error_data = await response.json()
                                except:
                                    error_data = {}
                                
                                retry_after = error_data.get("error", {}).get("metadata", {}).get("retry_after_seconds", 10)
                                logger.warning(f"⏳ Rate limited for {agent_name} on {model}. Waiting {retry_after}s...")
                                await asyncio.sleep(min(float(retry_after), 8))
                                continue

                            if response.status != 200:
                                # Retry without response_format if it failed (some models don't support it)
                                # BUT only if it wasn't a rate limit
                                logger.info(f"Retrying {model} without JSON mode...")
                                del payload["response_format"]
                                async with session.post(
                                    OPENROUTER_URL,
                                    headers={"Authorization": f"Bearer {current_api_key}", "Content-Type": "application/json"},
                                    json=payload
                                ) as retry_res:
                                    
                                    if retry_res.status != 200:
                                        try:
                                            error_data = await retry_res.json()
                                        except:
                                            error_data = {}

                                        if retry_res.status == 429:
                                            retry_after = error_data.get("error", {}).get("metadata", {}).get("retry_after_seconds", 10)
                                            logger.warning(f"⏳ Rate limited for {agent_name} on {model} (retry). Waiting {retry_after}s...")
                                            await asyncio.sleep(min(float(retry_after), 8))
                                            continue

                                        raise Exception(f"API Error {retry_res.status}: {error_data}")
                                    data = await retry_res.json()
                            else:
                                data = await response.json()

                            choices = data.get("choices", [])

                            if not choices:
                                logger.warning(f"No choices returned from {model}")
                                continue
                    
                            message_data = choices[0].get("message", {})

                            raw_content = message_data.get("content")

                            if raw_content is None:
                                logger.warning(f"Empty content returned from {model}")
                                continue

                            if not isinstance(raw_content, str):

                                raw_content = str(raw_content)
                            
                            # Surgical extraction: Find the first { and the last }
                            try:
                                start = raw_content.find('{')
                                end = raw_content.rfind('}')
                                if start != -1 and end != -1 and end > start:
                                    clean_content = raw_content[start:end+1]
                                else:
                                    clean_content = raw_content.strip()
                                    clean_content = re.sub(r'^```(?:json|JSON)?\s*', '', clean_content)
                                    clean_content = re.sub(r'\s*```$', '', clean_content).strip()

                                parsed = json.loads(clean_content)

                                if not isinstance(parsed, dict):
                                    logger.warning(f"Non-dict JSON from {agent_name}")
                                    return {}

                                return parsed

                            except Exception as e:
                                logger.warning(
                                    f"Invalid JSON from {agent_name}. Attempting repair..."
                                )

                                # Attempt to find JSON object in the string
                                json_match = re.search(r'(\{.*)', clean_content, re.DOTALL)
                                if json_match:
                                    repaired_json = json_match.group(1).strip()

                                    # Fix unclosed string: Count non-escaped quotes
                                    quotes = len(re.findall(r'(?<!\\)"', repaired_json))
                                    if quotes % 2 != 0:
                                        repaired_json += '"'

                                    # Remove trailing commas
                                    repaired_json = re.sub(r",\s*([\]}])", r"\1", repaired_json)

                                    # Fix truncated JSON: balance braces and brackets
                                    open_braces = repaired_json.count('{') - repaired_json.count('}')
                                    open_brackets = repaired_json.count('[') - repaired_json.count(']')
                                    
                                    if open_braces > 0 or open_brackets > 0:
                                        repaired_json = repaired_json.rstrip().rstrip(',')
                                        repaired_json += ']' * max(0, open_brackets) + '}' * max(0, open_braces)

                                    try:
                                        return json.loads(repaired_json)
                                    except Exception as repair_error:
                                        # Final attempt: try to slice at the last valid comma-separated block
                                        last_good = max(repaired_json.rfind('},'), repaired_json.rfind('],'))
                                        if last_good > 0:
                                            try:
                                                final_attempt = repaired_json[:last_good+1] + ('}' * open_braces)
                                                return json.loads(final_attempt)
                                            except:
                                                pass
                                        logger.error(f"JSON Repair Failed: {repair_error}")

                                logger.warning(
                                    f"Agent {agent_name} produced invalid JSON: "
                                    f"{raw_content[:500]}"
                                )
                                continue

                    except asyncio.TimeoutError:
                        logger.warning(f"⏱️ LLM Timeout for {agent_name} using {model}")
                        continue
                    except Exception as e:
                        logger.warning(f"❌ Error with {model}: {e}")
                        continue
            
            # If we get here, all models in the current global attempt failed
            if global_attempt == 0:
                logger.warning(f"⚠️ All models failed in first global attempt for {agent_name}. Waiting 30s before trying again...")
                await asyncio.sleep(30)
            else:
                logger.error(f"❌ All models failed after 2 global attempts for {agent_name}. Returning None.")
                return None
