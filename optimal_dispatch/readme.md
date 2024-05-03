## Optimal Dispatch ##

Optimal dispatch logic tries to allocate the pending trips with the best sherpa available. Choice of best sherpa is made with the paramter $Z$


$Z=(eta)^a/(priority)^b$
<br>
$priority=p1/p2$

```markdown
where,
    eta - expected time of arrival computed for the sherpa to reach the first station of the trip booked,
    priority - measure of how long a trip has been pending,
    p1 - Time since booking of currrent trip,
    p2 - Minimum of time since booking across all the pending trips,
    a - eta power factor , 0<a<1,
    b - priority power factor , 0<b<1,
```

## How is optimal dispatch triggered ##

Optimal dispatch is called from the handlers(../handlers/default/handlers.py), whenever it receives a message of type in [OptimalDispatchInfluencers](../core/constants.py#OptimalDispathInfluencers).


## Optimal dispatch for scheduled trips ##

For scheduled trips, we enqueue a job at scheduled trip's start time to trigger optimal dispatch. Please check [periodic_assigner](../scripts/periodic_assigner.py)


## Run optimal dispatch ##

1. Optimal dispatch first check if there has been any new bookings, any trip cancelation or any change in sherpa availability before runing optimal dispatch. If there are no changes to these, there is no requirement to run optimal dispatch.

2. We compute eta matrix of size (num_trips, num_available_sherpas) filled with values of Z, defined in [Optimal Dispatch](#optimal-dispatch). The eta power factors, priority power factors are configurable, can be chosen based on business use case.

3. We run hungarian algorithm on the final eta matrix, to get the assignments. To run hungarian_assignment. The input matrix provided to the hungarian assignment needs to be a square matrix, we add dummy data to the eta matrix to make it square.


## References ##

1. https://en.wikipedia.org/wiki/Hungarian_algorithm#:~:text=The%20Hungarian%20method%20is%20a,anticipated%20later%20primal%E2%80%93dual%20methods.