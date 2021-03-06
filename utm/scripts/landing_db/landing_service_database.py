#!/usr/bin/env python
# -*- coding: utf-8 -*- 
from __future__ import print_function
from bson.objectid import ObjectId

import rospy
import platform

from utm import Database
from mongodb_store_msgs.msg import StringPairList
from mongodb_store.message_store import MessageStoreProxy
from datetime import *

if float(platform.python_version()[0:2]) >= 3.0:
    import io
else:
    import StringIO


"""
BUGS 
NEED to check if database is empty

"""

class LandingDBNode():
    """
    LandingDB appends all UAVs that are requesting the third party landing service
    assigns initial state of UAV 
    String messages from UAV are as follows:
        -uav battery -- Int32 
        -uav position information global reference(pose and quat)
        -uav waypoint waypoint position as tuple(pose and quat)
        -uav service request -- Bool
        -uav state -- String

    Attributes
    dbInfo : Database.AbstractDatabaseInfo()
        Instiantes abstract databaseinfo:
        ip_address : str
        port_num : int
        poolsize : int

    """
    database_name = "message_store"
    main_col_name = "data_service"
    landing_col_name = "landing_service_db"

    def __init__(self, ip_address, port_num,poolsize):
        
        #access database
        self.dbInfo= Database.AbstractDatabaseInfo(ip_address, port_num, poolsize)
        self.mainDB = self.dbInfo.access_database(self.database_name)
    
        #mongodb
        self.main_collection = self.get_collection(self.mainDB, self.main_col_name)      
        self.landing_collection = self.get_collection(self.mainDB, self.landing_col_name)

        #ros service proxies with mongodb
        self.data_srv_col_prox = MessageStoreProxy(collection=self.main_col_name)    
        self.landing_srv_col_prox = MessageStoreProxy(collection= self.landing_col_name)

        #self.dataBaseInfo.retrieve_all_objects()
        self.sub = None

    @classmethod
    def get_collection(self,database, col_name):
        """class method that returns collection from mongodb database input and collection name"""
        collection = database[col_name]
        return collection

    def main(self):
        """main function implementation"""
        rate = rospy.Rate(0.25)
        while not rospy.is_shutdown():
            self.listen_for_incoming()
            rate.sleep()

    def listen_for_incoming(self):
        """listen for any incoming uavs"""
        myquery = {"pairs": {"$exists": True}}

        
        for doc in self.main_collection.find(myquery):
            meta_info = doc['_meta']
            uav_name = meta_info['name']
            bat_val = self.get_uav_battery_info(uav_name=uav_name)
            #uav_cur_loc = self.get_uav_info(uav_name, 1)
            
            """if uav does not want service then we ignore"""
            if (self.get_uav_srv_info(uav_name) == False): 
                continue
            
            """uav already exists in the landing service database"""
            if (self.does_uav_exist(uav_name) == True):
                print("uav exists already")
                continue

            if (self.is_landing_collection_empty()== True) or (self.does_uav_exist(uav_name) == False):
                uav_loc = self.get_uav_location(uav_name=uav_name)
                uav_home = self.get_uav_home(uav_name=uav_name)
                self.insert_to_landing_collection(uav_name, bat_val, 0, uav_loc, uav_home)

    def get_uav_srv_info(self, uav_name):
        """check if uav wants to use the landing service"""
        for item,meta in self.data_srv_col_prox.query_named(uav_name, StringPairList._type, single=False):
            print(item)
            srv_msg_type = item.pairs[4].first 
            srv_id = item.pairs[4].second
            srv_val = self.data_srv_col_prox.query_id(srv_id, srv_msg_type)[0].data
            if srv_val == False:
                print(uav_name + " " + "does not want the service\n")
            return srv_val

    def get_uav_location(self, uav_name):
        """get uav location from dataservice"""
        for item, meta in self.data_srv_col_prox.query_named(uav_name, StringPairList._type, single=False):
            msg_type = item.pairs[2].first 
            msg_id = item.pairs[2].second
            pose = self.data_srv_col_prox.query_id(msg_id, msg_type)[0].pose
            x = pose.position.longitude
            y = pose.position.latitude
            z = pose.position.altitude
            uav_locs = [x,y,z]

            """need to change to an int for grid position formatting"""
            uav_locs = [int(i) for i in uav_locs]
            print("insertin", uav_locs)

        return uav_locs

    def get_uav_home(self, uav_name):
        """need to refactor this with uav locations its the same thing"""
        for item, meta in self.data_srv_col_prox.query_named(uav_name, StringPairList._type, single=False):
            msg_type = item.pairs[1].first 
            msg_id = item.pairs[1].second
            pose = self.data_srv_col_prox.query_id(msg_id, msg_type)[0].pose
            x = pose.position.longitude #longitude is x
            y = pose.position.latitude #latitude is y
            z = pose.position.altitude 
            uav_home = [x,y,z]

            """need to change to an int for grid position formatting"""
            uav_home = [int(i) for i in uav_home]
            print("insertin", uav_home)

        return uav_home

    def get_uav_battery_info(self, uav_name):
        """get battery information"""
        for item,meta in self.data_srv_col_prox.query_named(uav_name, StringPairList._type, single=False):
            print(uav_name)
            print(item)
            batter_msg_type = item.pairs[0].first 
            battery_id = item.pairs[0].second
            battery_val = self.data_srv_col_prox.query_id(battery_id, batter_msg_type)[0].data

            return battery_val

    def get_uav_info(self, uav_name,index):
        """get information"""
        for item,meta in self.data_srv_col_prox.query_named(uav_name, StringPairList._type, single=False):
            msg_type = item.pairs[index].first 
            id_num = item.pairs[index].second
            val = self.data_srv_col_prox.query_id(id_num, msg_type)[0]

            return val

    def insert_to_landing_collection(self, uav_name, battery_val, state_val, uav_loc, uav_home):
        """this has a lot of coupling"""
        post = {"_id": uav_name,
                "uav_name": uav_name,
                "battery" : battery_val,
                "uav_location": uav_loc,
                "uav_home": uav_home,
                "landing_service_status": state_val,
        }
        self.landing_collection.insert_one(post)
        print(uav_name + " " + "added to database\n")
    
    def is_landing_collection_empty(self):
        """checks if collection has field name 
        field name is type string
        return True if it does"""
        #myquery = {field_name: {"$exists": True}} 
        if self.landing_collection.count(()) == 0:
            return True

    def does_uav_exist(self,uav_name):
        """check if uav key already exists in the landing collection"""
        myquery = {"_id": uav_name}
        cursor = self.landing_collection.find(myquery)
        if cursor.count() == 0: #means no uav is in there
            return False
        else:
            print(uav_name + " " + "exists already in database\n")
        
if __name__ == '__main__':
    """
    listen for uavs that are requesting a service 
    if uav is not part of the landing service database and is requesting the 
    service then we will 
    add it to the landing service database
    generate message strings with ros? 

    make a list of drone names in database 
    search for names not in this database and is requesting service
    add onto database 
    keep looping
    """

    rospy.init_node("landing_service_database")

    ip_address = "127.0.0.1"
    port_num = 27017
    poolsize = 100
    
    landingDBNode  = LandingDBNode(ip_address=ip_address, port_num=port_num, poolsize=poolsize)
    srv_collection = landingDBNode.main_collection
    landing_srv_collection = landingDBNode.landing_collection

    try:
        #landingDBNode.listen_for_incoming()
        landingDBNode.main()
    except rospy.ServiceException as e:
        print("Service call failed: %s"%e)

