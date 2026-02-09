import secrets
import click


@click.command()
@click.option("--hw_id", help="Hardware id of the device (chassis_id in case of vehicle)")
def gen_api_key(hw_id):
    if len(hw_id) < 2:
        print("Usage : api_key_gen <hwid/chassis-id of machine>")
        exit(1)
    else:
        key = secrets.token_urlsafe(32) + "_" + hw_id
        print("hwid : ", hw_id, " apikey : ", key)
    return


if __name__ == "__main__":
    gen_api_key()
