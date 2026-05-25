import asyncio
import os

import httpx
import typer

app = typer.Typer(help="Smart Lab Device Control Hub CLI")
DEFAULT_API = os.getenv("SMART_LAB_API_URL", "http://127.0.0.1:8000/api/v1")


async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    async with httpx.AsyncClient(base_url=DEFAULT_API, timeout=10.0) as client:
        response = await client.request(method, path, **kwargs)
        response.raise_for_status()
        return response


@app.command()
def devices() -> None:
    """List registered devices."""

    response = asyncio.run(_request("GET", "/devices"))
    for device in response.json():
        typer.echo(f"{device['device_id']}\t{device['device_type']}\t{device['transport']}")


@app.command("start-device")
def start_device(device_id: str) -> None:
    response = asyncio.run(_request("POST", f"/devices/{device_id}/commands", json={"command": "start"}))
    typer.echo(response.json())


@app.command("stop-device")
def stop_device(device_id: str) -> None:
    response = asyncio.run(_request("POST", f"/devices/{device_id}/commands", json={"command": "stop"}))
    typer.echo(response.json())


@app.command("reset-device")
def reset_device(device_id: str) -> None:
    response = asyncio.run(_request("POST", f"/devices/{device_id}/commands", json={"command": "reset"}))
    typer.echo(response.json())


@app.command("run-assay")
def run_assay(assay_id: str) -> None:
    response = asyncio.run(_request("POST", "/assays/run", json={"assay_id": assay_id}))
    typer.echo(response.json())


@app.command()
def monitor(interval: float = typer.Option(2.0, help="Polling interval in seconds")) -> None:
    """Poll monitoring data until interrupted."""

    async def _monitor() -> None:
        while True:
            response = await _request("GET", "/monitoring")
            data = response.json()
            process = data["process"]
            workers = data["workers"]
            typer.echo(
                f"pid={process['pid']} cpu={process['cpu_percent']}% "
                f"rss={process['memory_mb']}MB devices={workers['device_count']} "
                f"queue={workers['telemetry_queue_depth']}"
            )
            await asyncio.sleep(interval)

    try:
        asyncio.run(_monitor())
    except KeyboardInterrupt:
        typer.echo("monitor stopped")


@app.command()
def logs(limit: int = 20) -> None:
    response = asyncio.run(_request("GET", "/logs", params={"limit": limit}))
    for item in response.json():
        typer.echo(f"{item['created_at']} {item['level']} {item['component']}: {item['message']}")


if __name__ == "__main__":
    app()
