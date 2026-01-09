"""
GEOINT Advisor - AI assistant for Phase 4: Map/Cartography.

Provides guidance for spatial relationships, geography, and location management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.agents.base import Agent, AgentRole, AgentResponse
from forge.agents.prompts import get_prompt_manager
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState
    from forge.core.models.entity import Entity

logger = get_logger("advisors.geoint")

# Get the default prompt manager
_prompt_manager = get_prompt_manager()


class GEOINTAdvisor(Agent):
    """AI advisor for the map phase (GEOINT).
    
    Provides intelligent assistance for geographical aspects,
    helping users manage locations, spatial relationships,
    and travel logistics.
    
    Usage:
        advisor = GEOINTAdvisor(state)
        response = await advisor.analyze_geography(locations, relationships)
        response = await advisor.plan_travel_route(origin, destination)
    """
    
    role = AgentRole.ADVISOR
    
    def get_system_prompt(self) -> str:
        """Get the system prompt from the prompt manager."""
        return _prompt_manager.get("geoint.system_prompt")
    
    async def analyze_geography(
        self,
        locations: list["Entity"],
        spatial_relationships: list[dict],
    ) -> AgentResponse:
        """Analyze geographical layout.
        
        Args:
            locations: Location entities
            spatial_relationships: Spatial relationships between locations
            
        Returns:
            Geography analysis response
        """
        loc_data = [
            {
                "name": loc.name,
                "description": loc.description
            }
            for loc in locations[:15]
        ]
        
        prompt = _prompt_manager.render(
            "geoint.analyze_geography_prompt",
            locations=loc_data,
            spatial_relationships=spatial_relationships[:20],
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Analyzed geography for {len(locations)} locations")
        
        return response
    
    async def suggest_location_details(
        self,
        location: "Entity",
        nearby_locations: list["Entity"] | None = None,
        inhabitants: list["Entity"] | None = None,
    ) -> AgentResponse:
        """Suggest geographical details for a location.
        
        Args:
            location: The location entity
            nearby_locations: Nearby locations for context
            inhabitants: Notable inhabitants
            
        Returns:
            Location detail suggestions
        """
        nearby_data = []
        if nearby_locations:
            nearby_data = [
                {"name": loc.name, "type": loc.type.value}
                for loc in nearby_locations[:5]
            ]
        
        inhabitant_data = []
        if inhabitants:
            inhabitant_data = [{"name": e.name} for e in inhabitants[:5]]
        
        prompt = _prompt_manager.render(
            "geoint.suggest_location_details_prompt",
            location_name=location.name,
            location_type=location.type.value,
            location_description=location.description,
            nearby_locations=nearby_data,
            inhabitants=inhabitant_data,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Suggested details for '{location.name}'")
        
        return response
    
    async def plan_travel_route(
        self,
        origin: "Entity",
        destination: "Entity",
        waypoints: list["Entity"] | None = None,
        traveler: "Entity" | None = None,
        constraints: str = "",
    ) -> AgentResponse:
        """Plan a travel route between locations.
        
        Args:
            origin: Starting location
            destination: End location
            waypoints: Optional waypoints to consider
            traveler: Who is traveling
            constraints: Travel constraints
            
        Returns:
            Route planning response
        """
        waypoint_data = []
        if waypoints:
            waypoint_data = [{"name": w.name} for w in waypoints[:5]]
        
        traveler_data = None
        if traveler:
            traveler_data = {"name": traveler.name, "type": traveler.type.value}
        
        prompt = _prompt_manager.render(
            "geoint.plan_travel_route_prompt",
            origin_name=origin.name,
            origin_description=origin.description,
            destination_name=destination.name,
            destination_description=destination.description,
            waypoints=waypoint_data,
            traveler=traveler_data,
            constraints=constraints,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Planned route: {origin.name} -> {destination.name}")
        
        return response
    
    async def identify_spatial_issues(
        self,
        locations: list["Entity"],
        relationships: list[dict],
    ) -> AgentResponse:
        """Identify spatial and geographical issues.
        
        Args:
            locations: Location entities
            relationships: All relationships
            
        Returns:
            Issue identification response
        """
        loc_data = [
            {"name": loc.name, "type": loc.type.value}
            for loc in locations[:20]
        ]
        
        prompt = _prompt_manager.render(
            "geoint.identify_spatial_issues_prompt",
            locations=loc_data,
            relationships=relationships[:30],
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log("Identified spatial issues")
        
        return response
    
    async def answer_question(
        self,
        question: str,
        context: str = "",
    ) -> AgentResponse:
        """Answer a question about geography.
        
        Args:
            question: User's question
            context: Optional context
            
        Returns:
            Response to the question
        """
        prompt = _prompt_manager.render(
            "geoint.answer_question_prompt",
            question=question,
            context=context,
        )
        
        response = await self._generate_structured(prompt)
        
        if response.success:
            self.log(f"Answered question: {question[:50]}...")
        
        return response
