# sensirion_sps30_telegraf

Reads sensirion sps30 sensor via UART interface and posts results as influx line protocol string to telegraf instance.

Depends on https://pypi.org/project/sensirion-shdlc-driver/

### Known issues:
- Sensor library might report "unknown error 67" on startup. This error means that the current command (probably wakeup or start fan) can not be executed in the current state. This is most likely because a previous run of the program or other program left the sensor in running state and it's already active. The process will continue to run and try to read the sensor anyway. 
- The sensirion library does not understand "error 67" even though it's documented in the sensor data sheet. 
