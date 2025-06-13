
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/api/ws"
    async with websockets.connect(uri) as websocket:
        # Send initial session setup
        await websocket.send(json.dumps({
            "session_id": "123",
            "user_name": "Kent Hudson Caparas",
            "job_role": "Software Developer",
            "job_level": "Entry-Level",
            "interview_type": "Behavioural"
        }))
        
        # Get initial response
        response = await websocket.recv()
        print("Received:", response)
        
        # Send a message
        await websocket.send(json.dumps({
            "content": "Yes, I am ready!"
        }))
        
        # Get response
        response = await websocket.recv()
        print("Received:", response)

asyncio.run(test_websocket())
