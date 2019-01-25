#!/usr/local/bin/python3

import csv
import datetime
import argparse
import requests
from lxml import html, etree

# Configuration
work_stop_south = '70212' # Mountain View Station, Southbound Trains
home_stop_south = '70262' # San Jose Diridon Station, Southbound Trains
work_stop_north = '70211' # Mountain View Station, Northbound Trains
home_stop_north = '70261' # San Jose Diridon Station, Northbound Trains

class CalTrain:
  stop_data = 'data/stop_times.txt'
  stops = {}

  def __init__(self):
    self.init_stops()

  def init_stops(self):
    with open(self.stop_data, newline='') as f:
      # 0 = trip_id
      # 1 = arrival_time
      # 2 = departure_time
      # 3 = stop_id
      reader = csv.reader(f)
      for row in reader:
        if row[0].isdigit(): # Ignore shuttles and the header row
          if int(row[0]) < 400: # Let's only care about weekday schedules
            if not row[3] in self.stops.keys():
              self.stops[row[3]] = {}
            if not row[0] in self.stops[row[3]].keys():
              self.stops[row[3]][row[0]] = {}
            self.stops[row[3]][row[0]]['arrival'] = row[1]
            self.stops[row[3]][row[0]]['departure'] = row[2]

  def get_realtime_for_stop(self, direction, trainid):
    if direction == 'SB':
      endpoint = 'http://www.caltrain.com/schedules/realtime/stations/mountainviewstation-mobile.html'
      content = requests.get(endpoint, timeout=0.25)
      doc = html.fromstring(content.text)
      div = doc.find('.//div[@id="ipsttrains"]')
      sb = div.find('.//table[@class="ipf-st-ip-trains-subtable"]')
      for sbtrain in sb.findall('.//tr[@class="ipf-st-ip-trains-subtable-tr"]'):
        details = sbtrain.findall('.//td') # 0 = trainid, 1 = type, 2 = estimated arrival in mins, 3 = estimated arrival time
        if trainid == details[0].text:
          return details[2].text
    else:
      endpoint = 'http://www.caltrain.com/schedules/realtime/stations/sanjosediridonstation-mobile.html'
      content = requests.get(endpoint, timeout=0.25)
      doc = html.fromstring(content.text)
      div = doc.find('.//div[@id="ipsttrains"]')
      nb = div.findall('.//table[@class="ipf-st-ip-trains-subtable"]')[1]
      for nbtrain in nb.findall('.//tr[@class="ipf-st-ip-trains-subtable-tr"]'):
        details = nbtrain.findall('.//td') # 0 = trainid, 1 = type, 2 = estimated arrival in mins, 3 = estimated arrival time
        if trainid == details[0].text:
          return details[2].text

  def get_stops(self, stopid):
    return self.stops[stopid]

  def get_departure(self, stopid, trainid):
    return self.stops[stopid][trainid]['departure']

  def does_train_stop_at(self, trainid, destid):
    if trainid in self.stops[destid]:
      return self.stops[destid][trainid]['arrival']
    else:
      return None

  def find_next_train(self, stopid, destid, direction):
    now = datetime.datetime.now()
    next_train = "UNDEFINED"
    next_train_departs = "UNDEFINED"
    next_train_seconds = 86400
    for trainid in self.get_stops(stopid):
      if self.does_train_stop_at(trainid, destid):
        departs_at = self.get_departure(stopid, trainid)
        if int(departs_at.split(":")[0]) < 24: # Just ignore times they put as 24 meaning next AM
          new_time = datetime.datetime.strptime("{}-{}-{} {}".format(now.year, now.month, now.day, departs_at), "%Y-%m-%d %H:%M:%S")
          time_delta = (new_time - now).total_seconds()
          if time_delta > 0:
            if time_delta < next_train_seconds:
              next_train = trainid
              next_train_departs = departs_at
              next_train_seconds = time_delta
    next_in_minutes = round(next_train_seconds / 60)
    realtime = self.get_realtime_for_stop(direction, next_train).split(" ")[0]
    delta = int(realtime) - next_in_minutes;
    delta_text = "" 
    if delta > 0:
      delta_text = " (+{})".format(delta) 
    print("{}{} {} mins{}".format(direction, next_train, next_in_minutes, delta_text))


def get_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--direction",
    required=True,
    help="To work or home?"
         "  example: --direction home" )
  args = parser.parse_args()
  return args

if __name__ == '__main__':
  args = get_args()
  ct = CalTrain()
  if args.direction == 'home':
    ct.find_next_train(work_stop_south, home_stop_south, 'SB')
  else:
    ct.find_next_train(home_stop_north, work_stop_north, 'NB')
