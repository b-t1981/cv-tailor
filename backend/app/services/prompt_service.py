import json
from pathlib import Path

from app.config import settings
from app.models.schemas import PromptConfig


class PromptService:
    def __init__(self) -> None:
        self._path = settings.prompts_path
        self._template_path = self._path.parent / "default_prompts.template.json"

    def load(self) -> PromptConfig:
        if not self._path.exists():
            return self.reset()
        with open(self._path, encoding="utf-8") as file:
            data = json.load(file)
        config = PromptConfig(**data)
        combined = f"{config.system_prompt}\n{config.user_prompt}".lower()
        if "json" not in combined or len(config.system_prompt.strip()) < 80:
            return self.reset()
        return config

    def save(self, config: PromptConfig) -> PromptConfig:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as file:
            json.dump(config.model_dump(), file, ensure_ascii=False, indent=2)
        return config

    def reset(self) -> PromptConfig:
        with open(self._template_path, encoding="utf-8") as file:
            data = json.load(file)
        config = PromptConfig(**data)
        return self.save(config)

    def exists(self) -> bool:
        return self._path.exists()


prompt_service = PromptService()
