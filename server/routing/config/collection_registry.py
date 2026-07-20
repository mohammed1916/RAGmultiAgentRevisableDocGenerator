"""Collection registry - manages available knowledge source collections."""

import yaml
from pathlib import Path
from typing import List, Dict, Optional

from ..models import CollectionMetadata
from ...base.logger import setup_logger

logger = setup_logger(__name__)


class CollectionRegistry:
    """Registry for managing available collections.

    Loads collection metadata from YAML config and provides query interface.
    Singleton pattern to ensure single instance across application.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.collections: Dict[str, CollectionMetadata] = {}
        self.active_collections: List[str] = []
        self._load_collections()
        self._initialized = True

    def _load_collections(self) -> None:
        """Load collection metadata from YAML config file."""
        config_path = Path(__file__).parent / "collections.yaml"

        if not config_path.exists():
            logger.error(f"Collections config not found: {config_path}")
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config or "collections" not in config:
                logger.warning("No collections found in config")
                return

            for col_data in config["collections"]:
                col = CollectionMetadata(**col_data)
                self.collections[col.name] = col

                if col.active:
                    self.active_collections.append(col.name)
                    logger.info(f"Registered active collection: {col.display_name}")
                else:
                    logger.debug(f"Registered inactive collection: {col.display_name}")

            logger.info(f"Loaded {len(self.collections)} collections, {len(self.active_collections)} active")

        except Exception as e:
            logger.error(f"Failed to load collections config: {e}")

    def get_collection(self, name: str) -> Optional[CollectionMetadata]:
        """Get collection metadata by name.

        Args:
            name: Collection name

        Returns:
            CollectionMetadata or None if not found
        """
        return self.collections.get(name)

    def get_active_collections(self) -> List[CollectionMetadata]:
        """Get all active collections.

        Returns:
            List of active CollectionMetadata
        """
        return [self.collections[name] for name in self.active_collections]

    def get_all_collections(self) -> List[CollectionMetadata]:
        """Get all collections (active and inactive).

        Returns:
            List of all CollectionMetadata
        """
        return list(self.collections.values())

    def get_by_source_type(self, source_type: str) -> List[CollectionMetadata]:
        """Get collections by source type.

        Args:
            source_type: Source type (e.g., 'cbse', 'jee', 'neet')

        Returns:
            List of matching CollectionMetadata
        """
        return [col for col in self.collections.values() if col.source_type == source_type]

    def get_by_tag(self, tag: str) -> List[CollectionMetadata]:
        """Get collections by tag.

        Args:
            tag: Tag name

        Returns:
            List of collections with this tag
        """
        return [col for col in self.collections.values() if tag in col.tags]

    def get_by_keywords(self, keyword: str) -> List[CollectionMetadata]:
        """Get collections matching keyword.

        Args:
            keyword: Keyword to search

        Returns:
            List of collections containing this keyword
        """
        keyword_lower = keyword.lower()
        return [
            col for col in self.collections.values()
            if any(keyword_lower in kw.lower() for kw in col.keywords)
        ]

    def get_description_text(self) -> str:
        """Get formatted description of all active collections for LLM prompt.

        Returns:
            Formatted text describing available collections
        """
        active = self.get_active_collections()

        if not active:
            return "No active collections available."

        text = "Available Collections:\n"
        for col in active:
            text += f"\n- {col.display_name} ({col.name})\n"
            text += f"  Description: {col.description}\n"
            text += f"  Type: {col.source_type}\n"
            if col.document_count:
                text += f"  Documents: {col.document_count}\n"
            if col.keywords:
                text += f"  Keywords: {', '.join(col.keywords[:5])}\n"

        return text

    def reload(self) -> None:
        """Reload collections from config file.

        Useful for hot-reloading during development or when config changes.
        """
        logger.info("Reloading collections config...")
        self.collections.clear()
        self.active_collections.clear()
        self._load_collections()
