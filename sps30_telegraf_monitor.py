#!/usr/bin/python3

from sensirion_shdlc_driver import ShdlcSerialPort, ShdlcConnection, ShdlcDevice
from sensirion_shdlc_driver.command import ShdlcCommand

import time
import struct

import logging
import socket
import requests

from optparse import OptionParser
import traceback

log = logging.getLogger('SPS30_Sensor')
SENSOR_VALUES = ['PM1.0', 'PM2.4', 'PM4.0', 'PM10', 'N_PM0.5', 'N_PM1.0', 'N_PM2.5', 'N_PM4.0', 'N_PM10', 'avg_size']

class ShdlcCmdStart(ShdlcCommand):
  def __init__(self):
    super(ShdlcCmdStart, self).__init__(0x00, data=[0x01, 0x03], max_response_time=0.5, max_response_length=32, post_processing_time=2.0)

class ShdlcCmdStartCleaning(ShdlcCommand):
  def __init__(self):
    super(ShdlcCmdStartCleaning, self).__init__(0x56, data=[], max_response_time=0.5, max_response_length=0, post_processing_time=15.0)

class ShdlcCmdRead(ShdlcCommand):
  def __init__(self):
    super(ShdlcCmdRead, self).__init__(0x03, data=[], max_response_time=0.5, max_response_length=40, post_processing_time=0.5)

class ShdlcCmdStop(ShdlcCommand):
  def __init__(self):
    super(ShdlcCmdStop, self).__init__(0x01, data=[], max_response_time=0.5, max_response_length=0, post_processing_time=2.0)

class ShdlcCmdSleep(ShdlcCommand):
  def __init__(self):
    super(ShdlcCmdSleep, self).__init__(0x10, data=[], max_response_time=0.5, max_response_length=0, post_processing_time=2.0)

class ShdlcCmdWake(ShdlcCommand):
  def __init__(self, device):
    port = device.connection.port
    port._serial.write(0xff)
    super(ShdlcCmdWake, self).__init__(0x11, data=[], max_response_time=0.5, max_response_length=0, post_processing_time=2.0)

def parse_options():
  parser = OptionParser()
  parser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False)
  parser.add_option('-n', '--num_mess', dest='number_mess', type='int', help='Number of measurements to perform and average', default=20)
  parser.add_option('-s', '--sleep_int', dest='sleep_int', type = 'float', help='Time to wait between measurement iterations', default=1)
  parser.add_option('-w', '--warmup_time', dest='warmup_time', type = 'float', help='Time to wait for fan to spin up and start measurements', default=20)
  parser.add_option('-p', '--port', dest='port', type = 'string', help='path to serial port io file', default='/dev/ttyAMA0')
  parser.add_option('-l', '--location', dest='location', type = 'string', help='location of the sensor', default='UnderStairs')
  parser.add_option('-t', '--telegraf_address', dest='telegraf', type = 'string', help='URL for telegraf instance', default='http://192.168.178.220:8090/telegraf')
  parser.add_option('-i', '--interval', dest='interval', type = 'int', help='Seconds between waking up and capturing data', default='300')

  return parser.parse_args()

def readData(options):
  averages = [0] * 10
  sensor_id = ''
  with ShdlcSerialPort(port=options.port, baudrate=115200) as port:
    device = ShdlcDevice(ShdlcConnection(port), slave_address=0)
    log.debug('Waking device')
    try:
      device.execute(ShdlcCmdWake(device))
    except:
      log.warning('Something went wrong while waking up the sensor')
      log.warning(traceback.format_exc())
    sensor_id = device.get_serial_number()
    if options.verbose:
      log.debug('Version')
      log.debug("Version: {}".format(device.get_version()))
      log.debug("Product Name: {}".format(device.get_product_name()))
      log.debug("Article Code: {}".format(device.get_article_code()))
      log.debug("Serial Number: {}".format(sensor_id))

    log.debug('Starting up fan')
    try:
      device.execute(ShdlcCmdStart())
    except:
      log.error('Failed to start up fan')

    log.debug('Warmup')
    time.sleep(options.warmup_time)
#    print('Cleaning')
#    device.execute(ShdlcCmdStartCleaning())
    log.debug('Reading')
    data = []
    n = options.number_mess
    for i in range(0, n):
      rawData = device.execute(ShdlcCmdRead())
      data.append(struct.unpack(">ffffffffff", rawData))
      time.sleep(options.sleep_int)
    for d in data:
      for i, k in enumerate(d):
        averages[i] += k
    for i, k in enumerate(averages):
      averages[i] = k / n
    log.debug(averages)

  with ShdlcSerialPort(port=options.port, baudrate=115200) as port:
    device = ShdlcDevice(ShdlcConnection(port), slave_address=0)
    log.debug('Stopping device')
    device.execute(ShdlcCmdStop())

  with ShdlcSerialPort(port=options.port, baudrate=115200) as port:
    device = ShdlcDevice(ShdlcConnection(port), slave_address=0)
    log.debug('Putting device to sleep')
    device.execute(ShdlcCmdSleep())

  return sensor_id, averages


def upload_telegraf(options, sensor_id, data):
  t = time.time()
  timestamp = int(t) * 1000000000
  session = requests.session()
  session.trust_env = False

  for mess, d in zip(SENSOR_VALUES, data):
    telegraf_string = 'sps30,location=%s,sensor_id=%s,pm=%s value=%f %d' % (options.location, sensor_id, mess, d, timestamp)
    print(telegraf_string)
    try:
      response = session.post(options.telegraf, data=telegraf_string)
      log.debug('http response code   : %s' % response.status_code)
      log.debug('http response heaers : %s' % response.headers)
      log.debug('http response content: %s' % response.content)
      #pass
    except:
      log.error('Failed to submit data string %s' % telegraf_string)
      log.error(traceback.format_exc())

def main_loop(options):
  while True:
    before = time.time()
    sensor_id, data = readData(options)
    upload_telegraf(options, sensor_id, data)
    if options.verbose:
      print(sensor_id, data)
    after = time.time()
    diff = options.interval - (after - before)
    if diff > 0:
      time.sleep(diff)
    

def main():
  options, args = parse_options()
  main_loop(options)

  #Never gets called
  sensor_id, data = readData(options)
  upload_telegraf(options, sensor_id, data)
  print(sensor_id, data)


if __name__ == '__main__':
  main()
