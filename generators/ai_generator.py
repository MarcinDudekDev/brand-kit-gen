"""AI-based logo generation using various providers."""
import io
import os
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import quote

import requests
from PIL import Image

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from models.brand_identity import BrandIdentity


class AIProvider(ABC):
    """Abstract base for AI image generation providers."""

    @abstractmethod
    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        """Generate image from prompt."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available (API key present, etc.)."""
        pass


class PollinationsProvider(AIProvider):
    """Pollinations.ai - FREE, no API key required!

    Uses GET request to https://image.pollinations.ai/prompt/{prompt}
    """

    BASE_URL = "https://image.pollinations.ai/prompt"

    def __init__(self, timeout: int = 90):
        self.timeout = timeout

    def is_available(self) -> bool:
        """Always available - no API key needed."""
        return True

    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        """Generate image via Pollinations API.

        Args:
            prompt: Text prompt for image generation
            width: Image width
            height: Image height

        Returns:
            PIL Image
        """
        # URL-encode the prompt
        encoded_prompt = quote(prompt)

        # Build URL with parameters
        url = f"{self.BASE_URL}/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true"

        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        return Image.open(io.BytesIO(response.content))


class OpenAIProvider(AIProvider):
    """OpenAI Images API (DALL-E / gpt-image-1) - high quality, paid.

    Best quality for OG images with text. Supports exact 1200x630 size.
    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(self, timeout: int = 120):
        self.timeout = timeout
        self.api_key = os.environ.get('OPENAI_API_KEY')

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        """Generate image via OpenAI Images API."""
        if not self.is_available():
            raise RuntimeError("OPENAI_API_KEY not set")

        import base64

        # Map dimensions to supported sizes
        size = self._get_supported_size(width, height)

        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-image-1",
                "prompt": prompt,
                "size": size,
                "n": 1,
            },
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        # Decode base64 image
        img_b64 = data['data'][0]['b64_json']
        img_bytes = base64.b64decode(img_b64)
        img = Image.open(io.BytesIO(img_bytes))

        # Resize if needed (API might return different size)
        if img.size != (width, height):
            img = img.resize((width, height), Image.Resampling.LANCZOS)

        return img

    def _get_supported_size(self, width: int, height: int) -> str:
        """Map requested dimensions to OpenAI supported sizes."""
        # gpt-image-1 supports: 1024x1024, 1536x1024 (landscape), 1024x1536 (portrait)
        # Also: 1792x1024, 1024x1792 for DALL-E 3
        if width > height:
            return "1536x1024"  # landscape
        elif height > width:
            return "1024x1536"  # portrait
        else:
            return "1024x1024"  # square


class GeminiProvider(AIProvider):
    """Google Gemini image generation - requires API key.

    Note: Image generation may be geo-restricted in some countries (e.g., Poland).
    Uses gemini-2.0-flash with IMAGE response modality.
    """

    # Models to try in order of preference
    MODELS = [
        'gemini-2.0-flash',
        'gemini-2.5-flash',
        'gemini-2.0-flash-exp',
    ]

    def __init__(self):
        self.api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        """Generate image via Gemini API using generate_content with IMAGE modality."""
        if not self.is_available():
            raise RuntimeError("GEMINI_API_KEY not set")

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            last_error = None
            for model in self.MODELS:
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_modalities=['IMAGE', 'TEXT'],
                        )
                    )

                    # Look for image in response
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            img_bytes = part.inline_data.data
                            return Image.open(io.BytesIO(img_bytes))

                    # No image found, try next model
                    last_error = RuntimeError(f"{model}: No image in response")

                except Exception as e:
                    error_str = str(e)
                    if 'not available in your country' in error_str:
                        raise RuntimeError(
                            "Gemini image generation is geo-restricted in your country. "
                            "Use --provider pollinations instead (free, no restrictions)."
                        )
                    elif 'RESOURCE_EXHAUSTED' in error_str:
                        raise RuntimeError(
                            "Gemini rate limit exceeded. Try again later or use "
                            "--provider pollinations (free, unlimited)."
                        )
                    last_error = e
                    continue

            raise last_error or RuntimeError("All Gemini models failed")

        except ImportError:
            raise RuntimeError(
                "google-genai package not installed. Run: pip install google-genai"
            )


class AIGenerator:
    """Main AI generator with provider fallback chain."""

    PROVIDERS = {
        'openai': OpenAIProvider,
        'pollinations': PollinationsProvider,
        'gemini': GeminiProvider,
    }

    def __init__(self, brand: BrandIdentity, provider: Optional[str] = None):
        """Initialize generator.

        Args:
            brand: BrandIdentity with colors and name
            provider: Force specific provider, or None for auto-detect
        """
        self.brand = brand
        self.requested_provider = provider

    def generate_logo(self, size: int = 512) -> Image.Image:
        """Generate logo using AI.

        Args:
            size: Image size (square)

        Returns:
            PIL Image (RGBA)
        """
        prompt = self._build_logo_prompt()
        provider = self._get_provider()

        print(f"  Using AI provider: {provider.__class__.__name__}")
        print(f"  Prompt: {prompt[:100]}...")

        img = provider.generate(prompt, size, size)

        # Ensure RGBA
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        return img

    def generate_og_image(self, width: int = 1200, height: int = 630) -> Image.Image:
        """Generate OG image using AI.

        Args:
            width: Image width
            height: Image height

        Returns:
            PIL Image
        """
        prompt = self._build_og_prompt()
        provider = self._get_provider()

        print(f"  Using AI provider: {provider.__class__.__name__}")

        img = provider.generate(prompt, width, height)

        if img.mode != 'RGB':
            img = img.convert('RGB')

        return img

    def _get_provider(self) -> AIProvider:
        """Get the best available provider."""
        if self.requested_provider:
            if self.requested_provider not in self.PROVIDERS:
                raise ValueError(f"Unknown provider: {self.requested_provider}")

            provider_class = self.PROVIDERS[self.requested_provider]
            provider = provider_class()

            if not provider.is_available():
                raise RuntimeError(f"Provider {self.requested_provider} is not available")

            return provider

        # Auto-detect: prefer quality first (OpenAI), then free (Pollinations), then Gemini
        for name in ['openai', 'pollinations', 'gemini']:
            provider_class = self.PROVIDERS[name]
            provider = provider_class()
            if provider.is_available():
                return provider

        raise RuntimeError("No AI providers available")

    def _build_logo_prompt(self) -> str:
        """Build prompt for logo generation."""
        return (
            f"Abstract minimalist logo ICON ONLY, NO TEXT NO LETTERS NO WORDS. "
            f"Simple geometric symbol using {self.brand.primary_color} and {self.brand.accent_color}. "
            f"{self.brand.theme} background ({self.brand.background_color}). "
            f"Clean vector style, suitable for 16x16 favicon. "
            f"Single centered shape, flat design, high contrast. "
            f"DO NOT include any text, letters, or brand name."
        )

    def _build_og_prompt(self) -> str:
        """Build prompt for OG image generation."""
        return (
            f"Professional banner image for '{self.brand.name}', "
            f"using colors {self.brand.primary_color}, {self.brand.accent_color}, "
            f"and {self.brand.background_color}, "
            f"{self.brand.theme} theme, modern abstract design, "
            f"suitable for social media preview, no text, "
            f"gradient elements, professional corporate style"
        )
