import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from fastapi.routing import APIRoute
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel

app = FastAPI()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP Request Latency",
    ["method", "path"],
)

items = {}


class Item(BaseModel):
    name: str


def get_route_path(request: Request):
    # on veut /items/{item_id} et pas /items/1, /items/2... sinon explosion de labels
    for route in app.routes:
        if isinstance(route, APIRoute):
            match, _ = route.matches(request.scope)
            if match.name == "FULL":
                return route.path
    return request.url.path


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    path = get_route_path(request)
    REQUEST_COUNT.labels(method=request.method, path=path, status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, path=path).observe(duration)
    return response


@app.get("/")
def root():
    return {"message": "API Running 🚀"}


@app.post("/items")
def create_item(item: Item):
    item_id = len(items) + 1
    items[item_id] = item.name
    return {"id": item_id, "name": item.name}


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Not found")
    return {"id": item_id, "name": items[item_id]}


@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    items[item_id] = item.name
    return {"id": item_id, "name": item.name}


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    items.pop(item_id, None)
    return {"message": "Deleted"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
