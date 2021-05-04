# cowin-vaccine-availability
Searches and notifies when vaccine slot is available

#### Create a run.sh of the following format and schedule that via CRON
```
export SLACK_ACCESS_TOKEN=
export SLACK_USER_ID=

source env/bin/activate

python slot_availability.py

deactivate
```

To figure out `district_id` you can edit the script and run it to fetch all the states and then all the districts.

```
# Prints all states (id and name map) - Useful to fetch state_id to list districts
get_all_states()

Prints all districts in state 21 (id and name map)
get_all_districts_for_state(21)
```