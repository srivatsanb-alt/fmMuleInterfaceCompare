import asyncio
import plugins.ies.ies_simulator as ies_sim

ip = "192.168.6.251"
id = 0
num_req = 100
type = "JobCreate"
asyncio.get_event_loop().run_until_complete(
    ies_sim.simulate_bookings(ip, id, num_req, type)
)
