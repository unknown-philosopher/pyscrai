"""
DuckDB Analytics Operations.

Deep analytics queries for dashboard and reporting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from forge.utils.logging import get_logger

logger = get_logger("systems.analytics")


def get_entity_growth_metrics(world_db_path: Path, time_bucket: str = "1 hour") -> Any:
    """Get entity growth metrics over time.
    
    Args:
        world_db_path: Path to world.db SQLite file
        time_bucket: Time bucket size (e.g., "1 hour", "1 day")
        
    Returns:
        DataFrame with time bucket and mutation count
    """
    try:
        con = duckdb.connect()
        
        # Attach SQLite database
        con.execute(f"ATTACH '{world_db_path}' AS world (TYPE SQLITE)")
        
        # Query events log for entity creation mutations
        # Note: Adjust query based on actual events_log schema
        query = f"""
            SELECT 
                date_trunc('{time_bucket}', timestamp) as time_bucket, 
                count(*) as mutations 
            FROM world.events_log 
            WHERE event_type LIKE 'entity_%'
            GROUP BY time_bucket
            ORDER BY time_bucket
        """
        
        df = con.execute(query).df()
        con.close()
        
        logger.debug(f"Retrieved {len(df)} time buckets for entity growth")
        return df
        
    except Exception as e:
        logger.error(f"Failed to get entity growth metrics: {e}")
        return None


def get_relationship_network_metrics(world_db_path: Path) -> dict[str, Any]:
    """Get relationship network metrics.
    
    Args:
        world_db_path: Path to world.db SQLite file
        
    Returns:
        Dictionary with network metrics (node_count, edge_count, density, etc.)
    """
    try:
        con = duckdb.connect()
        con.execute(f"ATTACH '{world_db_path}' AS world (TYPE SQLITE)")
        
        # Get counts
        node_count = con.execute("SELECT count(*) FROM world.entities").fetchone()[0]
        edge_count = con.execute("SELECT count(*) FROM world.relationships").fetchone()[0]
        
        # Calculate density (if possible)
        max_edges = node_count * (node_count - 1) if node_count > 1 else 0
        density = (edge_count / max_edges) if max_edges > 0 else 0.0
        
        # Get average degree
        avg_degree = (edge_count * 2.0 / node_count) if node_count > 0 else 0.0
        
        con.close()
        
        metrics = {
            "node_count": node_count,
            "edge_count": edge_count,
            "density": density,
            "avg_degree": avg_degree,
        }
        
        logger.debug(f"Retrieved network metrics: {metrics}")
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get network metrics: {e}")
        return {}


def get_centrality_distribution(world_db_path: Path) -> Any:
    """Get centrality distribution for entities.
    
    Args:
        world_db_path: Path to world.db SQLite file
        
    Returns:
        DataFrame with entity_id and centrality measures
    """
    try:
        con = duckdb.connect()
        con.execute(f"ATTACH '{world_db_path}' AS world (TYPE SQLITE)")
        
        # Calculate degree centrality (simple version)
        # Count relationships per entity
        query = """
            SELECT 
                e.id as entity_id,
                e.name,
                (SELECT count(*) FROM world.relationships r WHERE r.source_id = e.id OR r.target_id = e.id) as degree_centrality
            FROM world.entities e
            ORDER BY degree_centrality DESC
        """
        
        df = con.execute(query).df()
        con.close()
        
        logger.debug(f"Retrieved centrality for {len(df)} entities")
        return df
        
    except Exception as e:
        logger.error(f"Failed to get centrality distribution: {e}")
        return None


def find_isolated_subcommunities(world_db_path: Path, min_size: int = 2) -> list[dict[str, Any]]:
    """Find isolated subcommunities in the network.
    
    Args:
        world_db_path: Path to world.db SQLite file
        min_size: Minimum community size
        
    Returns:
        List of community dictionaries with entity_ids
    """
    try:
        # For now, return empty list - would require more complex graph analysis
        # This would typically use a graph library like networkx
        logger.debug("Subcommunity detection not yet implemented in DuckDB")
        return []
        
    except Exception as e:
        logger.error(f"Failed to find subcommunities: {e}")
        return []
