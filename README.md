# sensirion_sps30_telegraf

Reads sensirion sps30 sensor via UART interface and posts results as influx line protocol string to telegraf instance.

Depends on https://pypi.org/project/sensirion-shdlc-driver/

### Known issues:
- There is a typo that stores PM2.5 values as PM2.4. Unfortunately if you have influxdb as a backend data store it is not trivial to rename those old values. For backward compatibility there is an option to continue storing it like that but the new default will be to store as PM2.5.
- Sensor library might report "unknown error 67" on startup. This error means that the current command (probably wakeup or start fan) can not be executed in the current state. This is most likely because a previous run of the program or other program left the sensor in running state and it's already active. The process will continue to run and try to read the sensor anyway. 
- The sensirion library does not understand "error 67" even though it's documented in the sensor data sheet. 
  