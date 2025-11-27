from fastapi import FastAPI
from .scanner import broadcast_discover

app = FastAPI(title="TIS Device Manager - Dev API")

@app.get("/api/discover")
def api_discover():
    result = broadcast_discover(timeout=2.0)
    output = []

    for addr, parsed, raw in result:
        output.append({
            "from": f"{addr[0]}:{addr[1]}",
            "parsed": parsed,
            "hex": raw.hex()
        })

    return {"found": output}
