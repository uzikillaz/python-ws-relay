import asyncio
import websockets
import os

HOST = '0.0.0.0'
# Railway provides the port to use in the PORT environment variable
PORT = int(os.environ.get('PORT', 8080))

HOST_CONN = None
CLIENT_CONN = None

connected_clients = set()

async def relay(source_ws, dest_ws, relay_type):
    print(f"[RELAY] Starting {relay_type} relay.")
    try:
        async for message in source_ws:
            if dest_ws and dest_ws.open:
                await dest_ws.send(message)
            else:
                print(f"[RELAY] Destination for {relay_type} not available. Stopping.")
                break
    except websockets.exceptions.ConnectionClosedError:
        print(f"[RELAY] Connection closed on {relay_type} source.")
    finally:
        print(f"[RELAY] {relay_type} relay stopped.")

async def handler(websocket, path):
    global HOST_CONN, CLIENT_CONN

    # The first connection is the host, the second is the client.
    if HOST_CONN is None:
        HOST_CONN = websocket
        print("[INFO] Host connected.")
        try:
            await websocket.wait_closed()
        finally:
            print("[INFO] Host disconnected.")
            HOST_CONN = None
            if CLIENT_CONN:
                await CLIENT_CONN.close()

    elif CLIENT_CONN is None:
        CLIENT_CONN = websocket
        print("[INFO] Client connected. Starting relays.")
        
        # Create two-way relay tasks
        screen_relay_task = asyncio.create_task(relay(HOST_CONN, CLIENT_CONN, 'Screen'))
        command_relay_task = asyncio.create_task(relay(CLIENT_CONN, HOST_CONN, 'Command'))

        try:
            # Wait for either connection to close
            done, pending = await asyncio.wait(
                [screen_relay_task, command_relay_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
        finally:
            print("[INFO] Client disconnected.")
            CLIENT_CONN = None
            if HOST_CONN and HOST_CONN.open:
                await HOST_CONN.close()
    else:
        print("[WARN] Third client tried to connect. Connection refused.")
        await websocket.close(1011, "Relay is already full.")

async def main():
    print(f"[*] WebSocket relay server starting on {HOST}:{PORT}")
    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
