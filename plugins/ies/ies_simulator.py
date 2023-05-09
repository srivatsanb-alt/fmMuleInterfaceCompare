import websockets
import json
import random
import datetime
import asyncio
import pytz


async def close_conn(websocket):
    print("closing ws connection!")
    await websocket.close()


def datetime_to_str(dt, time_format):
    dt = dt.astimezone(pytz.utc)
    return dt.strftime(time_format)


async def simulate_bookings(ip, id=0, num_req=1000, type="JobCreate", cancel_id=0):
    ies_time_format = "%Y-%m-%dT%H:%M:%SZ"
    ies_time_format_query = "%Y-%m-%dT%H:%M:%S.%f"
    ws_url = (
        "ws://"
        + ip
        + ":8002/ws/api/v1/plugin/ies/03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"
    )
    # ws_url = "ws://192.168.6.137:8002/ws/api/v1/plugin/ies/03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"
    start_location = "Warehouse_Pick"
    location_ids = [
        "HP02_FA02",
        "HP03_FA01",
        "HP04_FA03",
        "HP05_FA05",
        "HP06_FA04",
        "HP07_FA06",
        "HP03_FBCM",
        "HP05_FA07",
        "HP04_BECHUTE",
    ]  # bosch station ids
    count = 0
    if type != "JobCreate":
        print(f"simulating {type} msg..")
        num_req = 1
    try:
        async with websockets.connect(
            ws_url, ping_interval=None, ping_timeout=None
        ) as websocket:
            while count < num_req:
                if random.random() > 0.0:
                    stn_id = random.randint(0, len(location_ids) - 1)
                    print(f"creating JobCreate msg req: id = {id}, stn_id = {stn_id}")
                    deadline_time = datetime.datetime.now() + datetime.timedelta(hours=2)
                    deadline_time_str = datetime_to_str(deadline_time, ies_time_format)
                    print(f"deadline: {deadline_time_str}")

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
                    since = datetime.datetime.now() + datetime.timedelta(hours=-1)
                    until = datetime.datetime.now()
                    JobQuery_msg = {
                        "messageType": "JobQuery",
                        "since": datetime_to_str(since, ies_time_format_query),
                        "until": datetime_to_str(until, ies_time_format_query),
                    }
                    JobCancel_msg = {
                        "messageType": "JobCancel",
                        "externalReferenceId": f"ref_id_{cancel_id}",
                    }
                    print(f"sending msg {type}_msg ...")
                    print(JobQuery_msg)
                    if type == "JobCreate":
                        msg_json = json.dumps(JobCreate_msg)
                    elif type == "JobCancel":
                        msg_json = json.dumps(JobCancel_msg)
                    elif type == "JobQuery":
                        msg_json = json.dumps(JobQuery_msg)
                    await websocket.send(msg_json)
                    id += 1
                    count += 1
                await asyncio.sleep(0.5)
    except websockets.ConnectionClosed as e:
        print(f"connection closed, trying again (exception: {e})")
