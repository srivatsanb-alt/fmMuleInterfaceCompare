import secrets
import click


@click.command()
@click.option("--num_devices", help="Number of devices(summon_button)")
def gen_summon_button_api_key(num_devices):
    for i in range(1, int(num_devices) + 1):
        key = secrets.token_urlsafe(32) + "_" + str(i)
        print("device_id : ", i, " apikey : ", key)

    return


if __name__ == "__main__":
    gen_summon_button_api_key()
