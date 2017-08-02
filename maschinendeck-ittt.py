#!/usr/bin/env python3

MQTT_HEARTBEAT_INTERVAL_SECONDS = 60
FOREVER = True
import paho.mqtt.client as mqtt
import sched
import time
from datetime import datetime, timedelta
import ephem
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

class Auto():
  s = sched.scheduler(time.time, time.sleep)
  state = None
  def isSunSettingInOrSet(delta):
    trier = ephem.Observer()
    trier.lat, trier.lon = '49.7596', '6.6439'
    trier.elevation = 136
    
    prev_ris = ephem.localtime(trier.previous_rising(ephem.Sun()))
    prev_set = ephem.localtime(trier.previous_setting(ephem.Sun()))
    next_set = ephem.localtime(trier.next_setting(ephem.Sun()))
    now = datetime.now()
    
    if prev_set < prev_ris: #we have daytime (between sunrise and sunset), check if less than delta to sunset
      pre_set = next_set - delta
      if now > pre_set: #we are closer than delta to sunset
        return True
      else:
        return False
    else: #we have nighttime (between sunset and sunrise), so sun is set
      return True
  
  def on_message(self, client, userdata, msg):
    logging.debug("got on topic %s message %s" % (msg.topic, msg.payload));
    if msg.topic == "/maschinendeck/raum/status":
       if msg.payload == "open":
          self.state = True
          if not msg.retain:
            if isSunSettingInOrSet(timedelta(hours=1)):
              logger.debug("sunset, switch on lamp")
              client.publish("/maschinendeck/esper/1bfe7f/socket/set", "1")
       elif msg.payload == "closed":
          self.state = False
          if not msg.retain:
            client.publish("/maschinendeck/esper/1bfe7f/socket/set", "0")
       else:
          self.state = None

  def on_connect(self, client, userdata, flags, rc):
     logging.info("Connected with result code " + str(rc))

     client.subscribe("/maschinendeck/raum/status")
     self.mqttHeartbeat(False)
  
  def mqttHeartbeat(self, enqueue=True):
    if(FOREVER and enqueue):
      self.s.enter(MQTT_HEARTBEAT_INTERVAL_SECONDS, 0, self.mqttHeartbeat, ())
    logging.debug("sending MQTT Heartbeat for sonoffs")
    self.client.publish("/maschinendeck/esper/heartbeat")
    self.client.publish("/members/ranlvor/esper/heartbeat")
  
  def start(self):
    logging.info("Connecting to MQTT")
    client = mqtt.Client()
    self.client = client
    client.on_connect = self.on_connect
    client.on_message = self.on_message
    client.connect_async("mqtt.starletp9.de")
    client.loop_start()

    self.s.enter(MQTT_HEARTBEAT_INTERVAL_SECONDS, 0, self.mqttHeartbeat, ())
    self.s.run()

auto = Auto()
auto.start()
