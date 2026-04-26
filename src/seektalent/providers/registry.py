from __future__ import annotations

from seektalent.config import AppSettings
from seektalent.core.retrieval.provider_contract import ProviderAdapter
from seektalent.providers.cts import CTSProviderAdapter


def get_provider_adapter(settings: AppSettings) -> ProviderAdapter:
    # Phase one is intentionally static; a later task will make provider selection configurable.
    return CTSProviderAdapter(settings)
