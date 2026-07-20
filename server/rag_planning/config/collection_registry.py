"""Collection registry - loads available collections from configuration."""

import yaml
from pathlib import Path
from typing import Dict, List, Optional

from ..models import CollectionMetadata
from ...base.logger import setup_logger

logger = setup_logger(__name__)


class CollectionRegistry:
    """Registry for available collections.

    Singleton that loads collection metadata from YAML config.
    Provides query interface for planners and retrievers.
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
        self._load_collections()
        self._initialized = True

    def _load_collections(self) -> None:
        """Load collection metadata from YAML config."""
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
                logger.info(f"Registered collection: {col.display_name} ({col.name})")

            logger.info(f"Loaded {len(self.collections)} collections")

        except Exception as e:
            logger.error(f"Failed to load collections config: {e}")
            raise

    def get_collection(self, name: str) -> Optional[CollectionMetadata]:
        """Get collection by name.

        Args:
            name: Collection name

        Returns:
            CollectionMetadata or None if not found
        """
        return self.collections.get(name)

    def get_all_collections(self) -> List[CollectionMetadata]:
        """Get all available collections.

        Returns:
            List of all CollectionMetadata
        """
        return list(self.collections.values())

    def get_collection_names(self) -> List[str]:
        """Get list of all collection names.

        Returns:
            List of collection names
        """
        return list(self.collections.keys())

    def to_physical_collections(self, names: List[str]) -> List[str]:
        """Translate logical/routing collection names to physical Milvus names.

        The planner reasons about logical names (e.g. 'cbse_class_12'); the
        retriever needs the physical Milvus collection name (e.g.
        'documents_class_12'). Unknown names are dropped.

        Args:
            names: Logical collection names

        Returns:
            Physical Milvus collection names
        """
        physical = []
        for name in names:
            col = self.collections.get(name)
            if col:
                physical.append(col.physical_collection)
            else:
                logger.warning(f"Unknown collection '{name}' - cannot map to physical name")
        return physical

    def validate_collections(self, names: List[str]) -> List[str]:
        """Validate that requested collections exist.

        Args:
            names: List of collection names to validate

        Returns:
            List of valid collection names
        """
        valid = [name for name in names if name in self.collections]
        invalid = set(names) - set(valid)

        if invalid:
            logger.warning(f"Invalid collections requested: {invalid}")

        return valid

    def validate_metadata_filter(self, collection_name: str, field: str) -> bool:
        """Validate that a metadata field exists in a collection.

        Args:
            collection_name: Collection name
            field: Metadata field name

        Returns:
            True if field is valid for this collection
        """
        col = self.get_collection(collection_name)
        if not col:
            return False

        if not col.metadata_fields:
            return True  # No metadata schema defined, allow any field

        return field in col.metadata_fields

    def get_description_text(self) -> str:
        """Get formatted description of all collections for LLM prompt.

        Returns:
            Formatted text describing available collections
        """
        if not self.collections:
            return "No collections available."

        text = "Available Collections:\n"
        for col in self.collections.values():
            text += f"\n- {col.display_name} (collection name: {col.name})\n"
            text += f"  Description: {col.description}\n"
            if col.document_count:
                text += f"  Documents: {col.document_count:,}\n"
            if col.metadata_fields:
                fields_str = ", ".join(col.metadata_fields.keys())
                text += f"  Metadata fields: {fields_str}\n"

        return text

    def reload(self) -> None:
        """Reload collections from config file.

        Useful for dynamic updates during development.
        """
        logger.info("Reloading collections config...")
        self.collections.clear()
        self._load_collections()
