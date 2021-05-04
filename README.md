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
