"""GPU Telemetry Service using nvidia-ml-py."""

from __future__ import annotations

import asyncio
import logging
import os
import platform
from typing import Optional

try:
    import pynvml
except ImportError:
    pynvml = None  # type: ignore[assignment]

from forge.core.event_bus import EventBus, EventPayload
from forge.core.events import TOPIC_TELEMETRY_UPDATE, create_telemetry_event

logger = logging.getLogger(__name__)


def _is_wsl2() -> bool:
    """Check if running in WSL2."""
    try:
        with open("/proc/version", "r") as f:
            version_info = f.read().lower()
            return "microsoft" in version_info or "wsl" in version_info
    except Exception:
        return False


class GPUTelemetryService:
    """Service that monitors GPU metrics and publishes telemetry updates."""

    def __init__(self, event_bus: EventBus, update_interval: float = 1.0) -> None:
        """Initialize the GPU telemetry service.

        Args:
            event_bus: The event bus to publish telemetry updates to
            update_interval: How often to update telemetry (in seconds)
        """
        self._event_bus = event_bus
        self._update_interval = update_interval
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None
        self._initialized = False

    def _initialize_nvml(self) -> bool:
        """Initialize NVIDIA ML library if available."""
        if pynvml is None:
            logger.warning("pynvml not available - GPU telemetry disabled")
            return False

        try:
            pynvml.nvmlInit()
            # Check if any GPUs are available
            try:
                device_count = pynvml.nvmlDeviceGetCount()
                if device_count == 0:
                    logger.warning("No NVIDIA GPUs found - GPU telemetry disabled")
                    pynvml.nvmlShutdown()
                    return False
                logger.info(f"GPU telemetry initialized - {device_count} GPU(s) detected")
            except Exception as e:
                logger.warning(f"Failed to detect GPUs: {e}")
                pynvml.nvmlShutdown()
                return False
            self._initialized = True
            return True
        except pynvml.NVMLError as e:
            logger.warning(f"Failed to initialize GPU telemetry (NVMLError): {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to initialize GPU telemetry: {e}")
            return False

    def _get_gpu_metrics(self) -> tuple[float, float, float]:
        """Get current GPU metrics.

        Returns:
            Tuple of (gpu_util, vram_used_gb, vram_total_gb)
        """
        if not self._initialized or pynvml is None:
            return (0.0, 0.0, 0.0)

        try:
            # Get handle for the first GPU (device 0)
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)

            # Get GPU utilization
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_util = float(util.gpu)

            # Get memory info
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            vram_used_gb = float(mem_info.used) / (1024**3)  # Convert bytes to GB
            vram_total_gb = float(mem_info.total) / (1024**3)  # Convert bytes to GB

            return (gpu_util, vram_used_gb, vram_total_gb)
        except pynvml.NVMLError as e:
            # If we get an NVMLError, the GPU might have become unavailable
            # Log once and stop trying
            if self._running:
                logger.warning(f"GPU became unavailable: {e}. Stopping telemetry updates.")
                self._running = False
            return (0.0, 0.0, 0.0)
        except Exception as e:
            logger.error(f"Error reading GPU metrics: {e}")
            return (0.0, 0.0, 0.0)

    async def _update_loop(self) -> None:
        """Background task that periodically updates GPU telemetry."""
        while self._running:
            try:
                gpu_util, vram_used_gb, vram_total_gb = self._get_gpu_metrics()
                event = create_telemetry_event(gpu_util, vram_used_gb, vram_total_gb)
                await self._event_bus.publish(TOPIC_TELEMETRY_UPDATE, event)
            except Exception as e:
                logger.error(f"Error in telemetry update loop: {e}")

            await asyncio.sleep(self._update_interval)

    async def start(self) -> None:
        """Start the telemetry service."""
        if self._running:
            return

        if not self._initialized:
            if not self._initialize_nvml():
                # Initialization failed, don't start the service
                logger.info("GPU telemetry service not started (no GPU available)")
                return

        self._running = True
        self._task = asyncio.create_task(self._update_loop())
        logger.info("GPU telemetry service started")

    async def stop(self) -> None:
        """Stop the telemetry service."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._initialized and pynvml:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass

        logger.info("GPU telemetry service stopped")
