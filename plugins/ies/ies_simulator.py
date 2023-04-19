import websockets
import json
import random
import datetime
import asyncio


async def close_conn(websocket):
    print("closing ws connection!")
    await websocket.close()


async def simulate_bookings(ws_url, id=0):
    ies_time_format = "%Y-%m-%dT%H:%M:%SZ"
    # ws_url = "ws://192.168.6.137:8002/ws/api/v1/plugin/ies/03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"
    start_location = "Warehouse_Pick"
    location_ids = [
        "HP02_FA02",
        "HP03_FA01",
        "HP04_FA03",
        "HP05_FA05",
        "HP06_FA04",
        "HP07_FA06",
    ]  # bosch station ids
    while True:
        try:
            async with websockets.connect(
                ws_url, ping_interval=None, ping_timeout=None
            ) as websocket:
                while True:
                    if random.random() > 0.8:
                        stn_id = random.randint(0, len(location_ids) - 1)
                        # id = 101
                        # stn_id = 0
                        print(f"sending JobCreate req: id = {id}, stn_id = {stn_id}")
                        deadline_time = datetime.datetime.now() + datetime.timedelta(
                            hours=2
                        )
                        deadline_time_str = deadline_time.strftime(ies_time_format)

                        JobCreate_msg = {
                            "messageType": "JobCreate",
                            "externalReferenceId": "ref_id_" + str(id),
                            "taskList": [
                                {"ActionName": "Pickup", "LocationId": start_location},
                                {
                                    "ActionName": "Deliver",
                                    "LocationId": location_ids[stn_id],
                                },
                            ],
                            "deadline": deadline_time_str,
                            "priority": 0,
                            "properties": {
                                "materialNo": "string",
                                "materialDescription": "string",
                                "quantity": "string",
                                "kanbanId": "kanban:" + str(id),
                                "productionOrderId": "string",
                                "source": "string",
                                "destination": "string",
                                "unitLoadType": "string",
                                "unitLoadTypeId": "string",
                                "noOfUnitLoads": "string",
                                "unitloadType.name": "string",
                                "unitloadType.category": "string",
                                "unitloadType.description": "string",
                                "unitloadType.width": "string",
                                "unitloadType.height": "string",
                                "unitloadType.length": "string",
                                "unitloadType.weight": "string",
                                "agvSystemUnitLoadTypeId": "string",
                            },
                        }
                        msg_json = json.dumps(JobCreate_msg)
                        await websocket.send(msg_json)
                        id += 1
                    await asyncio.sleep(0.5)
        except websockets.ConnectionClosed as e:
            print(f"connection closed, trying again (exception: {e})")
