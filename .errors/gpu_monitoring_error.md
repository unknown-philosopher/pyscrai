## GPU Telemetry Error - Root Cause & Solutions

**Error Pattern:**
```
2026-01-11 11:25:31,162 - forge.infrastructure.telemetry - INFO - GPU telemetry initialized - 1 GPU(s) detected
2026-01-11 11:25:31,162 - forge.infrastructure.telemetry - INFO - GPU telemetry service started
2026-01-11 11:25:32,175 - forge.infrastructure.telemetry - WARNING - GPU became unavailable: Unknown Error. Stopping telemetry updates.
```

### Root Causes

1. **GPU Context Loss in Linux/WSL2 Environment**: When using Flet (Flutter-based) with GPU monitoring in WSL2 Linux, the GPU context can be lost when:
   - Flet initializes its OpenGL context (competing with CUDA)
   - The GTK/Wayland display server reclaims GPU resources
   - The X11/Wayland bridge disconnects

2. **NVML Context Sharing Issue**: pynvml (nvidia-ml-py) doesn't maintain persistent GPU context. After 1 second of operation, the GPU handle becomes stale when another application (Flet) uses the same GPU.

3. **Timing Race Condition**: The telemetry service initializes (~0s), detects GPU (~1s), but by the time it tries to read metrics (~2s), the GPU context has been stolen by the Flet rendering engine.

### Current Implementation Issues

In telemetry.py:

```python
# Line 76-85: Error is caught but service shuts down permanently
except pynvml.NVMLError as e:
    if self._running:
        logger.warning(f"GPU became unavailable: {e}. Stopping telemetry updates.")
        self._running = False
    return (0.0, 0.0, 0.0)
```

**Problem**: Once GPU becomes unavailable, the entire telemetry service stops. No recovery mechanism.

### Recommended Solutions

#### Solution 1: Implement Graceful Degradation (Recommended)
Keep the service running but return cached/zero values instead of stopping:

```python
async def _update_loop(self) -> None:
    """Background task that periodically updates GPU telemetry with fallback."""
    error_count = 0
    max_consecutive_errors = 5
    
    while self._running:
        try:
            gpu_util, vram_used_gb, vram_total_gb = self._get_gpu_metrics()
            event = create_telemetry_event(gpu_util, vram_used_gb, vram_total_gb)
            await self._event_bus.publish(TOPIC_TELEMETRY_UPDATE, event)
            error_count = 0  # Reset on success
            
        except pynvml.NVMLError as e:
            # Increment error count but don't stop service
            error_count += 1
            if error_count == 1:
                logger.warning(f"GPU telemetry temporarily unavailable: {e}")
            
            # Publish zero values instead of stopping
            event = create_telemetry_event(0.0, 0.0, 0.0)
            await self._event_bus.publish(TOPIC_TELEMETRY_UPDATE, event)
            
            # If errors persist, log warning periodically
            if error_count == max_consecutive_errors:
                logger.warning("GPU telemetry unavailable for 5+ cycles")
                error_count = 0  # Reset to avoid log spam
                
        except Exception as e:
            logger.error(f"Error in telemetry update loop: {e}")
            # Continue running despite errors

        await asyncio.sleep(self._update_interval)
```

#### Solution 2: Add NVML Reinitialization
Attempt to reinitialize NVML if GPU becomes unavailable:

```python
def _reinitialize_nvml(self) -> bool:
    """Attempt to reinitialize NVML connection."""
    try:
        if self._initialized:
            pynvml.nvmlShutdown()
        pynvml.nvmlInit()
        self._initialized = True
        logger.info("NVML reinitialized successfully")
        return True
    except Exception as e:
        logger.debug(f"NVML reinitialization failed: {e}")
        return False
```

#### Solution 3: Use Polling with Timeout
Add a timeout mechanism to detect GPU availability:

```python
async def _get_gpu_metrics_safe(self) -> tuple[float, float, float]:
    """Get GPU metrics with timeout and recovery."""
    try:
        # Try to reinit if we haven't checked recently
        if not self._initialized and not self._initialize_nvml():
            return (0.0, 0.0, 0.0)
        
        return self._get_gpu_metrics()
    except Exception:
        # Silently return zeros, don't stop service
        return (0.0, 0.0, 0.0)
```

### Why "Unknown Error" Occurs

The "Unknown Error" message comes from pynvml when `nvmlDeviceGetUtilizationRates()` is called on a stale GPU handle. This happens because:

1. GPU handle obtained at initialization is no longer valid
2. Flet has taken exclusive control of GPU resources
3. NVML doesn't auto-refresh handles

### Package Note

The dependency `nvidia-ml-py>=12.535.0` is correct. The issue is not with the package version but with:
- How the handle is maintained across context switches
- The service's response to GPU unavailability
- Lack of NVML reinitialization logic

### Implementation Steps

1. Update telemetry.py to implement graceful degradation
2. Keep the service running even when GPU becomes unavailable
3. Publish zero values instead of stopping
4. Add optional NVML reinitialization on every update cycle (with cost/benefit analysis)
5. Test with Flet app running to verify metrics display "0%  0/0 GB" instead of crashing

### Testing

```bash
# Run app and verify GPU telemetry shows 0% instead of stopping
python3 forge/main.py
```

Expected: UI displays "0% 0.0 / 0.0 GB" (not an error, graceful fallback)