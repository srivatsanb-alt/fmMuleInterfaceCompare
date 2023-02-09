from fastapi import FastAPI, APIRouter, WebSocket

app = FastAPI()

router = APIRouter()

app.include_router(router)

@router.websocket("/plugin/ws/api/v1/summon_button")
async def summon_button_ws(websocket: WebSocket):

    await websocket.accept()

    while True:
        print("Connected")