import asyncio
import plugins.ies.ies_simulator as ies_sim
import click
from absl import app


@click.command()
@click.option("--ip", default="127.0.0.1", help="IP address of FM server (in quotes)")
@click.option(
    "--id",
    default=0,
    help="ID number to start bookings, if you are running sim for 1st time, ID is 0. Next time, ID starts at num_reqs you gave previously",
)
@click.option("--num_req", default=100, help="number of requests to be sent to FM")
def run_ies_sim(ip, id, num_req):
    asyncio.get_event_loop().run_until_complete(
        ies_sim.simulate_bookings(ip, id, num_req, type="JobCreate")
    )


if __name__ == "__main__":
    app.run(run_ies_sim())
