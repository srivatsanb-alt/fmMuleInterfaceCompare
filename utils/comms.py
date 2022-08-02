from core.logs import get_logger


def send_move_msg(sherpa: str, trip_id: int, trip_leg_id: int, dest_name, dest_pose):
    msg = {
        "trip_id": trip_id,
        "trip_leg_id": trip_leg_id,
        "destination_pose": dest_pose,
        "destination_name": dest_name,
    }
    # POST to sherpa URL
    get_logger(sherpa).info(f"msg to {sherpa}: {msg}")
