#!/usr/bin/env python
# -*- coding: utf-8 -*- 
from __future__ import print_function
from bson.objectid import ObjectId

import rospy
import logging
from datetime import *

import numpy as np
from utm import Database, PathFinding

logging.basicConfig(filename='errors.txt', level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger(__name__)


class PostFlightService():
    """
    Listen for UAV battery
    Check if uav is in state 2 
    If state 2 check if it has a postflight plan
    If not plan a postflight trajectory
    Send drone off with postfligth trajectory
    check if drone has left area if so, update the landing zone as vacant 
    and remove uav
    """
    previous_service_number = 2
    update_service_number = 3

    def __init__(self):
        self.postFlight = Database.ZonePlanner()

    def find_home_path(self,grid_space, obstacles, uav_loc, goal_point):
        """start at landing zone and end at uav current location
        need to change name of uav current location to entry location"""
        astar = PathFinding.Astar(grid_space, obstacles,  uav_loc, goal_point)
        uav_wp = astar.main()
        
        return uav_wp

    def get_incoming_uavs_waypoints(self, service_num):
        """check for current flight paths, that is uav is in state 0 but 
        has waypoints"""
        waypoints = []
        myquery = {"$and": [{"landing_service_status":service_num}, 
                    {"Zone Assignment": {'$exists': True}}]}
        cursor = self.postFlight.landing_service_col.find(myquery)
        for document in cursor:
            waypoints.append(document["Raw Waypoint"])

        return waypoints

    def insert_waypoints(self,uav_name, uav_waypoint_list):
        """insert filtered waypoint path for uav"""
        self.postFlight.landing_service_col.update({"_id": uav_name},
            { "$set": { 
                "Home Waypoints": uav_waypoint_list}})

    def insert_raw_waypoints(self,uav_name, uav_waypoint_list):
        """insert filtered waypoint path for uav"""
        self.postFlight.landing_service_col.update({"_id": uav_name},
            { "$set": { 
                "Raw Home Waypoints": uav_waypoint_list}})

    def get_uav_info(self, field_name, service_number):
        """return field name info where landing service status is at 0
        field_name must be type str"""

        """"""
        myquery = {"landing_service_status": self.previous_service_number}
        uav_info_list = []
        cursor = self.postFlight.landing_service_col.find(myquery)
        for document in cursor: 
            uav_info_list.append(document[field_name])

        return uav_info_list

    def return_unassigned_list(self,some_list, index):
        """return all other values in list not assigned to the index"""
        copy = some_list
        if index >= len(copy):
            return copy
        else:
            copy.pop(index)
            print("copy", copy)
            return copy

    def add_obstacles(self,grid, obstacle_list):
        """"add obstacles to grid location"""
        for obstacle in obstacle_list:
            test = np.array(obstacle)
            if type(obstacle) != list or type(obstacle) != tuple:
                continue
            elif test.ndim > 1:
                continue
            else:
                (grid[int(obstacle[2]),int(obstacle[0]), int(obstacle[1])]) = 1
            
        return obstacle_list

    def get_dynamic_obstacles(self, idx, uav_path_obs, zone_locations, \
        zone_idx, path_list, uav_loc_list):
        """
        get location of uavs, 
        get location of zones not assigned to uavs
        get flight trajectories, 
        set as list
        """
        zone_bounds = self.return_unassigned_list(zone_locations[:], zone_idx) 
        zone_obstacles = []
        for zone in zone_bounds:
            x = zone[0]
            y = zone[1]
            for z in range(15):
                zone_obstacles.append((x,y,z))

        if idx == 0:
            new_obstacle = obstacle_list + \
                self.return_unassigned_list(zone_locations[:], zone_idx) + \
                zone_obstacles
        else:
            uav_path_obs.append(path_list[idx-1])
            flat_list = [item for sublist in uav_path_obs for item in sublist]
            uav_loc_flat = self.return_unassigned_list(uav_loc_list[:], idx)
            #print("uav location list", uav_loc_flat)
            uav_flat_list  = [item for sublist in uav_loc_flat for item in sublist]
            #print("uav flat list", uav_flat_list)
            new_obstacle = obstacle_list + \
                zone_obstacles + \
                flat_list

        grid_copy = grid.copy()
        new_obstacle = self.add_obstacles(grid_copy, new_obstacle)

        return grid_copy, new_obstacle

    def compute_vectors(self,point_1, point_2, point_3):
        vector_start = np.array(point_2)- np.array(point_1)
        vector_end = np.array(point_3) - np.array(point_2)
        
        return vector_start, vector_end
        
    def compute_cross_product(self,vector_1, vector_2):
        return np.cross(vector_1, vector_2)

    def reduce_waypoints(self,waypoint_list):
        print(waypoint_list)
        filtered_waypoints = []
        for i, waypoint in enumerate(waypoint_list):
            if i+2 - len(waypoint_list) == 0:
                filtered_waypoints.append(waypoint_list[i+1])
                """might want to append last waypoint value to new list"""
                return filtered_waypoints
            
            vec_start, vec_end = self.compute_vectors(waypoint, waypoint_list[i+1], waypoint_list[i+2])
            cross_product = self.compute_cross_product(vec_start, vec_end)
            if (cross_product[0] == 0 and cross_product[1] == 0
            and cross_product[2] == 0):
                print("collinear")
            else:
                print("not collinear")
                filtered_waypoints.append(waypoint)
                filtered_waypoints.append(waypoint_list[i+2])
                
        return filtered_waypoints

    def find_uavs_ready_to_leave(self, service_num):
        """find uavs that have landed but do not have a path planned to go
        home"""
        uav_names = []
        zone_names = []
        myquery = {"$and": [{"landing_service_status":service_num}, 
                    {"Home Waypoints": {'$exists': False}}]}
        cursor = self.postFlight.landing_service_col.find(myquery)
        for document in cursor:
            uav_names.append(document["_id"])
            zone_names.append(document["Zone Assignment"])
            print(uav_names)

        return uav_names, zone_names
    
    def main(self):
        """
        keep listening for uavs ready to leave
        if so append to list 
        plan flight path
        remove from list until empty
        keep looping
        """

        uavs, zone_names = self.find_uavs_ready_to_leave(self.previous_service_number)
        zone_coord_list = self.postFlight.get_zone_wp_list(zone_names)
        uav_class_list = self.postFlight.generate_publishers(uavs)
        uav_loc_list = self.get_uav_info("uav_location", self.previous_service_number)
        uav_loc_list.append(self.get_uav_info("uav_location", 0)) # for inbound uavs

        rate_val = 15
        rate = rospy.Rate(rate_val)

        while not rospy.is_shutdown():
            if not uav_class_list:
                print("Waiting for uavs")
                rospy.sleep(2.0)
                #keep listening for uavs
                uavs, zone_names = self.find_uavs_ready_to_leave(self.previous_service_number)
                #uavs,zone_names = self.postFlight.find_assigned_zones(self.previous_service_number)
                zone_coord_list = self.postFlight.get_zone_wp_list(zone_names)
                uav_class_list = self.postFlight.generate_publishers(uavs)
                uav_loc_list = self.get_uav_info("uav_location", self.previous_service_number)
                uav_loc_list.append(self.get_uav_info("uav_location", 0)) #for inbound uavs
            else:
                uav_path_obs = []
                path_list = []
                for idx, uav in enumerate(uav_class_list[:]):
                    rospy.sleep(0.5) #wait for a couple of seconds                    
                    #generate obstacles
                    grid_copy, new_obstacle = self.get_dynamic_obstacles(idx, uav_path_obs, \
                         zone_coord_list, idx, path_list, uav_loc_list)
                    #grid_copy, new_obstacle = self.get_dynamic_obstacles(idx, uav_path_obs)
                    #get landing and exit location
                    uav_landing_zone = self.postFlight.find_uav_info(uav.name, "Zone Assignment")
                    uav_exit_zone = self.postFlight.find_uav_info(uav.name, "uav_location")
                    zone_loc = self.postFlight.find_zone_waypoints(uav_landing_zone)
                    #telling the uav to start at the exit entry height
                    zone_loc[2] = uav_exit_zone[2]
                    print("zone location is", zone_loc)
                    #apply astar algorithim
                    uav_home_path = self.find_home_path(grid_copy, new_obstacle, \
                        zone_loc, uav_exit_zone)
                    #check if we have a path
                    if uav_home_path:
                        #append as dynamic obstacle
                        path_list.append(uav_home_path)
                        #reduce amount of waypoints
                        filter_homepath = self.reduce_waypoints(uav_home_path)
                        print("path planned is", filter_homepath)
                        home_loc = self.postFlight.find_uav_homeposition(uav.name)
                        filter_homepath.append(home_loc)
                        self.insert_waypoints(uav.name, filter_homepath)
                        self.insert_raw_waypoints(uav.name, uav_home_path)
                        print("removing uav", uav)
                        uav_class_list.remove(uav)
                    else:
                        print("cant find path")
                        break

                    if not uav_class_list:
                        break

            rate.sleep()


def generate_grid(grid_row, grid_col, grid_height):
    grid = []
    grid = np.zeros((grid_height, grid_row, grid_col))
    
    return grid

if __name__ == '__main__':
    """this is the homebase need to refactor this"""
    grid_z = 50 # this is probably the z axis
    grid_x = 50 # this is x
    grid_y = 50 # this is y
    grid = generate_grid(grid_z, grid_x,grid_y)
    
    rospy.init_node('post_flight_service')
    postFlightService = PostFlightService()

    static_obstacle_list = [(15,40)]
    obstacle_list = []
    for static_obstacle in static_obstacle_list:
        x = static_obstacle[0]
        y = static_obstacle[1]
        for z in range(25):
            obstacle_list.append((x,y,z))
    obstacle_list = postFlightService.add_obstacles(grid, obstacle_list)
    
    postFlightService.main()