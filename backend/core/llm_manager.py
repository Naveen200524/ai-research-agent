import os
import asyncio
import aiohttp
import google.generativeai as genai
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    GEMINI_FLASH = "gemini-2.0-flash"
    HUGGINGFACE_MIXTRAL = "mixtral-8x7b"

class LLMManager:
    """Manage multiple LLM providers with automatic fallback"""
    
    def __init__(self):
        self.providers = self._initialize_providers()
        self.usage_tracker = {}
        
    def _initialize_providers(self) -> Dict:
        """Initialize available LLM providers"""
        providers = {}
        
        # Initialize Gemini
        if os.getenv("GOOGLE_AI_API_KEY"):
            genai.configure(api_key=os.getenv("GOOGLE_AI_API_KEY"))
            providers[LLMProvider.GEMINI_FLASH] = {
                "available": True,
                "priority": 1,
                "cost_per_million": 0
            }
            logger.info("✓ Initialized Gemini Flash")
        
        # Initialize Hugging Face
        if os.getenv("HUGGINGFACE_API_KEY"):
            providers[LLMProvider.HUGGINGFACE_MIXTRAL] = {
                "available": True,
                "priority": 3,
                "cost_per_million": 0,
                "api_key": os.getenv("HUGGINGFACE_API_KEY")
            }
            logger.info("✓ Initialized Hugging Face")
        
        return providers
    
    async def generate_summary(
        self,
        query: str,
        contents: List[Dict],
        style: str = "comprehensive"
    ) -> Dict:
        """
        Generate research summary using best available LLM
        
        Args:
            query: Research query
            contents: Extracted content from sources
            style: Summary style (comprehensive, brief, technical)
            
        Returns:
            Summary with metadata
        """
        # Prepare context
        context = self._prepare_context(contents)
        prompt = self._create_prompt(query, context, style)
        
        # Try providers in order of priority
        sorted_providers = sorted(
            self.providers.items(),
            key=lambda x: x[1]["priority"]
        )
        
        last_error = None
        
        for provider, config in sorted_providers:
            if not config["available"]:
                continue
            
            try:
                logger.info(f"Trying {provider.value}...")
                
                if provider == LLMProvider.GEMINI_FLASH:
                    result = await self._call_gemini(prompt)
                elif provider == LLMProvider.HUGGINGFACE_MIXTRAL:
                    result = await self._call_huggingface(prompt, config["api_key"])
                else:
                    continue
                
                # Parse and structure the summary
                return self._parse_summary(
                    result["text"],
                    contents,
                    provider.value,
                    result.get("tokens", 0),
                    config.get("cost_per_million", 0)
                )
                
            except Exception as e:
                last_error = f"{provider.value}: {str(e)}"
                logger.error(last_error)
                
                # Temporarily disable failed provider
                config["available"] = False
                continue

        # If all providers failed, return error summary
        return self._create_error_summary(last_error or "No LLM providers available")

    def _prepare_context(self, contents: List[Dict]) -> str:
        """Prepare context from extracted contents"""
        context_parts = []

        for i, content in enumerate(contents[:10]):  # Limit to top 10 sources
            if not content.get("success"):
                continue

            title = content.get("title", f"Source {i+1}")
            text = content.get("text", "").strip()

            if text:
                # Limit text length per source
                if len(text) > 2000:
                    text = text[:2000] + "..."

                context_parts.append(f"## {title}\n{text}")

        return "\n\n".join(context_parts)

    def _create_prompt(self, query: str, context: str, style: str) -> str:
        """Create prompt for LLM based on style"""
        base_prompt = f"""You are an expert research analyst. Based on the following sources, provide a {style} summary of: {query}

Sources:
{context}

"""

        if style == "comprehensive":
            return base_prompt + """
Please provide a comprehensive analysis including:
1. Executive Summary (2-3 paragraphs)
2. Key Findings (bullet points)
3. Detailed Analysis (organized by topic)
4. Sources and Methodology
5. Future Implications (if applicable)

Format your response with clear section headers and be thorough but concise."""
        elif style == "brief":
            return base_prompt + """
Please provide a brief summary including:
1. Main conclusion (1-2 paragraphs)
2. Key supporting points (3-5 bullet points)
3. Most relevant source

Keep it concise and focused."""
        elif style == "technical":
            return base_prompt + """
Please provide a technical analysis including:
1. Technical specifications and details
2. Implementation considerations
3. Performance characteristics
4. Comparative analysis
5. Technical recommendations

Use precise technical language and focus on implementation details."""
        else:
            return base_prompt + """
Please provide a balanced summary covering the main points from the sources."""

    async def _call_gemini(self, prompt: str) -> Dict:
        """Call Google Gemini API"""
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        response = await model.generate_content_async(prompt)

        return {
            "text": response.text,
            "tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
        }

    async def _call_huggingface(self, prompt: str, api_key: str) -> Dict:
        """Call Hugging Face API"""
        url = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 4000,
                "temperature": 0.3,
                "return_full_text": False
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    raise Exception(f"Hugging Face API error: {response.status}")

                result = await response.json()

                # Handle different response formats
                if isinstance(result, list) and result:
                    text = result[0].get("generated_text", "")
                else:
                    text = result.get("generated_text", "")

                return {
                    "text": text,
                    "tokens": len(text.split()) * 1.3  # Rough estimate
                }

    def _parse_summary(self, text: str, contents: List[Dict],
                      model: str, tokens: int, cost_per_million: float) -> Dict:
        """Parse and structure the LLM response"""
        # Extract sections from the response
        sections = self._extract_sections(text)

        # Calculate cost
        cost = (tokens / 1_000_000) * cost_per_million if cost_per_million > 0 else 0.0

        # Get source information
        sources = []
        for content in contents:
            if content.get("success") and content.get("url"):
                sources.append({
                    "title": content.get("title", "Unknown"),
                    "url": content.get("url"),
                    "reliability_score": content.get("reliability_score", 0.5)
                })

        return {
            "summary": text,
            "sections": sections,
            "sources": sources,
            "generated_at": datetime.now().isoformat(),
            "word_count": len(text.split()),
            "model_used": model,
            "provider": model.split("-")[0] if "-" in model else model,
            "cost": round(cost, 4)
        }

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract sections from LLM response"""
        sections = {}
        current_section = "Overview"
        current_content = []

        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for section headers
            if line.startswith("#") or (len(line) < 100 and ":" in line and not line.startswith("http")):
                # Save previous section
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                    current_content = []

                # Extract new section name
                if line.startswith("#"):
                    current_section = line.lstrip("#").strip()
                else:
                    current_section = line.split(":")[0].strip()
            else:
                current_content.append(line)

        # Save last section
        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _create_error_summary(self, error: str) -> Dict:
        """Create error summary when all providers fail"""
        return {
            "summary": f"Unable to generate summary due to: {error}",
            "sections": {
                "Error": f"Summary generation failed: {error}",
                "Suggestion": "Please check API keys and network connectivity"
            },
            "sources": [],
            "generated_at": datetime.now().isoformat(),
            "word_count": 0,
            "model_used": "none",
            "provider": "error",
            "cost": 0.0
        }