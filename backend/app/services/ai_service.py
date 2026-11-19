import base64
import logging
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from app.core.config import settings
from app.services.text_extractor import ExtractedContent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Você é a Ju, assistente jurídica inteligente da Jus Digital. "
    "Sua função é analisar o documento enviado pelo usuário seguindo rigorosamente "
    "a instrução fornecida. Responda sempre em português do Brasil, de forma clara, "
    "objetiva e bem estruturada, baseando-se apenas nas informações presentes no documento."
)


class AIAnalysisError(Exception):
    """Domain error encapsulating user-friendly OpenAI failure messages."""

    pass


class AIService:
    """Integrates with OpenAI GPT-4o-mini for text and image document analysis."""

    def __init__(self) -> None:
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if not settings.OPENAI_API_KEY:
            raise AIAnalysisError(
                "Chave da API OpenAI não configurada no servidor."
            )
        if self._client is None:
            self._client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=45.0,
                max_retries=1,
            )
        return self._client

    def analyze_document(
        self,
        title: str,
        instruction: str,
        content: ExtractedContent,
    ) -> str:
        """
        Send the extracted document text (or base64 image) and user instruction
        to GPT-4o-mini and return the generated analysis text.
        """
        client = self._get_client()

        if content.kind == "image" and content.image_bytes is not None:
            b64 = base64.b64encode(content.image_bytes).decode("ascii")
            user_content: str | list[dict] = [
                {
                    "type": "text",
                    "text": (
                        f"Título do documento: {title}\n"
                        f"Instrução do usuário: {instruction}\n\n"
                        "Analise a imagem anexa conforme a instrução acima."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{content.mime_type};base64,{b64}",
                    },
                },
            ]
        else:
            user_content = (
                f"Título do documento: {title}\n"
                f"Instrução do usuário: {instruction}\n\n"
                "Conteúdo do documento:\n"
                "---\n"
                f"{content.text or ''}\n"
                "---"
            )

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                temperature=0.2,
                max_tokens=1500,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            )
            answer = (response.choices[0].message.content or "").strip()
            if not answer:
                raise AIAnalysisError(
                    "A IA retornou uma resposta vazia. Tente novamente."
                )
            return answer
        except APITimeoutError as exc:
            raise AIAnalysisError(
                "Tempo limite excedido ao aguardar resposta da OpenAI. Tente novamente."
            ) from exc
        except RateLimitError as exc:
            raise AIAnalysisError(
                "Limite de uso ou cota da API OpenAI atingido. Aguarde e tente novamente."
            ) from exc
        except AuthenticationError as exc:
            raise AIAnalysisError(
                "Falha de autenticação com a API OpenAI. Verifique a chave configurada."
            ) from exc
        except APIConnectionError as exc:
            raise AIAnalysisError(
                "Erro de conexão ao comunicar com a API OpenAI. Tente novamente."
            ) from exc
        except APIError as exc:
            logger.exception("OpenAI API error while analyzing document")
            raise AIAnalysisError(
                "Erro na API OpenAI ao processar o documento. Tente novamente em instantes."
            ) from exc


ai_service = AIService()
