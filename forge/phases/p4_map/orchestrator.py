"""
Map Orchestrator - Phase 4: GEOINT.

Manages entity coordinates and map visualization data.

Responsibilities:
- Filter entities with non-null coordinates
- Update entity coordinates (from map marker drags)
- Group entities by layer for map controls
- Handle custom map image overlays (fantasy worlds)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.core.models.entity import Entity
    from forge.systems.storage.database import DatabaseManager

logger = get_logger("phases.p4_map")


@dataclass
class MapConfig:
    """Configuration for the map view."""
    
    # Map source type
    source_type: str = "osm"  # "osm" (OpenStreetMap) or "image" (custom)
    
    # For custom image overlays
    image_path: Path | None = None
    image_bounds: tuple[tuple[float, float], tuple[float, float]] | None = None
    
    # Default center and zoom
    center: tuple[float, float] = (0.0, 0.0)
    default_zoom: int = 2
    
    # Layer visibility defaults
    visible_layers: set[str] | None = None


@dataclass
class MapMarker:
    """A marker for the map view."""
    
    entity_id: str
    name: str
    entity_type: str
    coordinates: tuple[float, float]
    layer: str
    description: str = ""
    icon: str = "default"
    popup_html: str = ""


class MapOrchestrator:
    """Orchestrator for Phase 4: Cartography/Map visualization.
    
    Manages entity locations and provides data for the Leaflet map.
    """
    
    def __init__(
        self,
        db_manager: "DatabaseManager",
        project_path: Path | None = None,
    ) -> None:
        """Initialize the MapOrchestrator.
        
        Args:
            db_manager: Database manager for entity queries
            project_path: Optional project path for custom map images
        """
        self.db = db_manager
        self.project_path = Path(project_path) if project_path else None
        self._config: MapConfig | None = None
        
        logger.debug("MapOrchestrator initialized")
    
    # ========== Entity Queries ==========
    
    def get_map_entities(self) -> list["Entity"]:
        """Get all entities that have coordinates.
        
        Returns:
            List of entities with non-null coordinates
        """
        all_entities = self.db.get_all_entities()
        
        return [
            e for e in all_entities
            if e.coordinates is not None and len(e.coordinates) == 2
        ]
    
    def get_entities_by_layer(self) -> dict[str, list["Entity"]]:
        """Get entities grouped by their layer.
        
        Returns:
            Dictionary mapping layer names to entity lists
        """
        entities = self.get_map_entities()
        
        layers: dict[str, list["Entity"]] = {}
        for entity in entities:
            layer = entity.layer.value if hasattr(entity.layer, "value") else str(entity.layer)
            if layer not in layers:
                layers[layer] = []
            layers[layer].append(entity)
        
        return layers
    
    def get_entities_by_type(self) -> dict[str, list["Entity"]]:
        """Get map entities grouped by entity type.
        
        Returns:
            Dictionary mapping type names to entity lists
        """
        entities = self.get_map_entities()
        
        types: dict[str, list["Entity"]] = {}
        for entity in entities:
            etype = entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type)
            if etype not in types:
                types[etype] = []
            types[etype].append(entity)
        
        return types
    
    def get_layers(self) -> list[str]:
        """Get list of all layers with entities.
        
        Returns:
            List of layer names
        """
        return list(self.get_entities_by_layer().keys())
    
    # ========== Coordinate Management ==========
    
    def update_entity_coordinates(
        self,
        entity_id: str,
        lat: float,
        lng: float,
    ) -> "Entity":
        """Update an entity's coordinates.
        
        Called when a map marker is dragged to a new position.
        
        Args:
            entity_id: ID of the entity to update
            lat: New latitude
            lng: New longitude
            
        Returns:
            Updated entity
            
        Raises:
            ValueError: If entity not found
        """
        entity = self.db.get_entity_by_id(entity_id)
        if not entity:
            raise ValueError(f"Entity not found: {entity_id}")
        
        entity.coordinates = (lat, lng)
        self.db.save_entity(entity)
        
        logger.info(f"Updated coordinates for {entity.name}: ({lat}, {lng})")
        return entity
    
    def set_entity_layer(
        self,
        entity_id: str,
        layer: str,
    ) -> "Entity":
        """Set an entity's map layer.
        
        Args:
            entity_id: ID of the entity
            layer: Layer name (e.g., 'TERRESTRIAL', 'ORBITAL')
            
        Returns:
            Updated entity
        """
        from forge.core.models.entity import LocationLayer
        
        entity = self.db.get_entity_by_id(entity_id)
        if not entity:
            raise ValueError(f"Entity not found: {entity_id}")
        
        try:
            entity.layer = LocationLayer(layer.upper())
        except ValueError:
            entity.layer = LocationLayer.TERRESTRIAL
        
        self.db.save_entity(entity)
        
        logger.info(f"Set layer for {entity.name}: {layer}")
        return entity
    
    def clear_entity_coordinates(self, entity_id: str) -> "Entity":
        """Remove coordinates from an entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            Updated entity
        """
        entity = self.db.get_entity_by_id(entity_id)
        if not entity:
            raise ValueError(f"Entity not found: {entity_id}")
        
        entity.coordinates = None
        self.db.save_entity(entity)
        
        logger.info(f"Cleared coordinates for {entity.name}")
        return entity
    
    # ========== Map Markers ==========
    
    def get_markers(self) -> list[MapMarker]:
        """Get all map markers for the UI.
        
        Returns:
            List of MapMarker objects ready for rendering
        """
        entities = self.get_map_entities()
        markers = []
        
        for entity in entities:
            etype = entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type)
            layer = entity.layer.value if hasattr(entity.layer, "value") else str(entity.layer)
            
            # Generate popup HTML
            popup = f"""
<div class="map-popup">
    <h4>{entity.name}</h4>
    <p class="type">{etype}</p>
    <p class="desc">{entity.description[:200] if entity.description else 'No description'}...</p>
</div>
            """.strip()
            
            # Determine icon based on type
            icon = self._get_icon_for_type(etype)
            
            markers.append(MapMarker(
                entity_id=entity.id,
                name=entity.name,
                entity_type=etype,
                coordinates=entity.coordinates,
                layer=layer,
                description=entity.description or "",
                icon=icon,
                popup_html=popup,
            ))
        
        return markers
    
    def _get_icon_for_type(self, entity_type: str) -> str:
        """Get an icon name for an entity type.
        
        Args:
            entity_type: Entity type string
            
        Returns:
            Icon identifier
        """
        icons = {
            "ACTOR": "person",
            "POLITY": "flag",
            "LOCATION": "place",
            "REGION": "terrain",
            "RESOURCE": "inventory",
            "EVENT": "event",
            "ABSTRACT": "category",
        }
        return icons.get(entity_type.upper(), "place")
    
    # ========== Map Configuration ==========
    
    def get_config(self) -> MapConfig:
        """Get the current map configuration.
        
        Returns:
            MapConfig object
        """
        if self._config:
            return self._config
        
        # Load from project settings or use defaults
        self._config = MapConfig()
        
        # Check for custom map image
        if self.project_path:
            map_image = self.project_path / "map.png"
            if map_image.exists():
                self._config.source_type = "image"
                self._config.image_path = map_image
        
        return self._config
    
    def set_config(self, config: MapConfig) -> None:
        """Update the map configuration.
        
        Args:
            config: New configuration
        """
        self._config = config
        logger.info(f"Map config updated: source_type={config.source_type}")
    
    def set_custom_map_image(
        self,
        image_path: Path,
        bounds: tuple[tuple[float, float], tuple[float, float]] | None = None,
    ) -> None:
        """Set a custom map image overlay.
        
        For fantasy/fictional worlds using CRS.Simple coordinates.
        
        Args:
            image_path: Path to the image file
            bounds: Optional ((south, west), (north, east)) bounds
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Map image not found: {image_path}")
        
        config = self.get_config()
        config.source_type = "image"
        config.image_path = image_path
        config.image_bounds = bounds
        
        self._config = config
        logger.info(f"Set custom map image: {image_path}")
    
    # ========== Bounds Calculation ==========
    
    def calculate_bounds(self) -> dict[str, Any]:
        """Calculate the bounding box for all entities.
        
        Returns:
            Dictionary with min/max lat/lng and center
        """
        entities = self.get_map_entities()
        
        if not entities:
            return {
                "min_lat": -90,
                "max_lat": 90,
                "min_lng": -180,
                "max_lng": 180,
                "center": (0, 0),
            }
        
        lats = [e.coordinates[0] for e in entities]
        lngs = [e.coordinates[1] for e in entities]
        
        return {
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lng": min(lngs),
            "max_lng": max(lngs),
            "center": (sum(lats) / len(lats), sum(lngs) / len(lngs)),
        }
    
    def get_ui_data(self) -> dict[str, Any]:
        """Get all data needed for the map UI.
        
        Returns:
            Dictionary with markers, config, and metadata
        """
        markers = self.get_markers()
        config = self.get_config()
        bounds = self.calculate_bounds()
        
        return {
            "markers": [
                {
                    "id": m.entity_id,
                    "name": m.name,
                    "type": m.entity_type,
                    "lat": m.coordinates[0],
                    "lng": m.coordinates[1],
                    "layer": m.layer,
                    "icon": m.icon,
                    "popup": m.popup_html,
                }
                for m in markers
            ],
            "config": {
                "source_type": config.source_type,
                "center": list(bounds["center"]),
                "zoom": config.default_zoom,
                "image_path": str(config.image_path) if config.image_path else None,
            },
            "layers": self.get_layers(),
            "entity_count": len(markers),
        }
