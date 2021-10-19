#!/usr/bin/env python
# -*- coding: utf-8 -*- 
from __future__ import print_function
from bson.objectid import ObjectId

import rospy
import threading
import numpy as np
from utm import Database
from utm import UAVGen
from scipy import spatial

from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Int8
from mongodb_store_msgs.msg import StringPairList
from mongodb_store.message_store import MessageStoreProxy
from datetime import *


class PathPlanner():
    """
    Look for drones at state 0 and have an assigned waypoint from waypoint collections
    Plan their path trajectories based on where they are at and their current waypoint
    Open up multiple threads to send location waypoints to these drones 
    Once at goal waypoint set UAV state to 1
    """
    ip_address = "127.0.0.1"
    port_num = 27017
    poolsize = 100
    database_name = "message_store"
    landing_srv_col_name = "landing_service_db"
    landing_zone_col_name = "landing_zones"

    def __init__(self):
        
        #access database
        self.dbInfo = Database.AbstractDatabaseInfo(self.ip_address, self.port_num, self.poolsize)
        self.mainDB = self.dbInfo.access_database(self.database_name)

        #recieve collection information
        self.landing_service_col = self.mainDB[self.landing_srv_col_name]
        self.landing_zone_col = self.mainDB[self.landing_zone_col_name]

        #ros proxy messages
        self.control_dict = {}

    def find_assigned_zones(self, service_num):
        """check if uav has an assigned location and if they are at state 0"""
        #myquery = {"Zone Assignment": {"$exists": True}}
        uavs = []
        zones = []
        myquery = {"$and": [{"landing_service_status":service_num}, 
                    {"Zone Assignment": {'$exists': True}}]}
        cursor = self.landing_service_col.find(myquery)
        for document in cursor:
            uavs.append(document["uav_name"])
            zones.append(document["Zone Assignment"])

        return uavs,zones

    def find_zone_waypoints(self, zone_number):
        myquery = {"Zone Number": zone_number}
        cursor = self.landing_zone_col.find(myquery)
        for document in cursor:
            zone_coordinates = document["location"]

        return zone_coordinates

    def get_zone_wp_list(self, zone_names):
        zone_coords = []
        for zone in zone_names:
            zone_coords.append(self.find_zone_waypoints(zone))
        
        return zone_coords

    def plan_uav_path(self):
        """takes in uav"""
        pass

    def send_wp_cmds(self):
        """open up multiple threads to send waypoints to drones"""

    def generate_publishers(self, uavs):
        uavObject_list = []
        for uav in uavs:
            uavComms = UAVGen.UAVComms(uav)
            uavObject_list.append(uavComms)
        
        return uavObject_list

    def is_arrived_to_zone(self, zone_coords, uav_coords):
        print(uav_coords)
        dist = abs(np.sqrt((zone_coords[0]- uav_coords[0])**2+(zone_coords[1]- uav_coords[1])**2))
        #print(dist)
        print(dist)
        if dist <= 0.25:
            return True
        else:
            return False

    def check_valid_uav_coords(uav_coords):
        """make sure uav coords are not none type"""

    def update_uav_state(self, uav_name, new_status):
        self.landing_service_col.update({"uav_name": uav_name},
        {"$set":{
            "landing_service_status": new_status
        }})

if __name__ == '__main__':
    rospy.init_node('utm_path_planner')
    pathPlanner = PathPlanner()
    uavs,zone_names = pathPlanner.find_assigned_zones(0)
    zone_coord_list = pathPlanner.get_zone_wp_list(zone_names)
    uav_class_list = pathPlanner.generate_publishers(uavs)
    """generate publishers and begin sending waypoint commands to drones""" 
    threads = []
    #open multiple threads to begin publising the waypoint command to the drone

    rate_val = 10
    rate = rospy.Rate(rate_val)

    """wrap this guy in main function"""
    while not rospy.is_shutdown():
        """need to check when the class is empty, if empty we listen for more drones"""
        #for i in range(len(uav_class_list)):
        for idx, uav in enumerate(uav_class_list[:]):
            uav.send_utm_state_command(0)
            uav.send_waypoint_command(zone_coord_list[idx])

        if uav_class_list is None:
            uavs,zone_names = pathPlanner.find_assigned_zones()
            zone_coord_list = pathPlanner.get_zone_wp_list(zone_names)
            uav_class_list = pathPlanner.generate_publishers(uavs)
        rate.sleep()




