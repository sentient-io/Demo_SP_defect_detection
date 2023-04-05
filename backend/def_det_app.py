import asyncio
from typing import List
from fastapi import FastAPI, WebSocket, Request,WebSocketDisconnect
import uvicorn
import argparse

app = FastAPI()

parser = argparse.ArgumentParser(description='Face Recognize for video. Single face per frame.')
parser.add_argument('port', help='Port')

class ConnectionManager:
    stream_running = False
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        print("Broadcasting called????")
        for connection in self.active_connections:
            print("connection inside")
            try:
                await connection.send_json(message)
            except Exception as err:
                print(err)

manager = ConnectionManager()

@app.websocket("/ws")
async def socket_endpoint(websocket: WebSocket):
    print("Accepting the connections........")
    await manager.connect(websocket)
    
    try:
        while True:
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("A client is just disconnected............")
        
     
@app.post("/post_results")
async def web_endpoint(frameinfo: Request):
    print("post")
    req_data = await frameinfo.json()
    # brod_data.update(req_data)
    await manager.broadcast(req_data)
    
    return {
		"status": "success",
		"data": req_data
	}
         


if __name__ == '__main__':
    kwargs = vars(parser.parse_args())
    port =int(kwargs['port'])
    uvicorn.run(app, port=port, host='0.0.0.0')