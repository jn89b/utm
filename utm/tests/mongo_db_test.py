#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import rospy
import mongodb_store_msgs.srv as dc_srv
import mongodb_store.util as dc_util
from mongodb_store.message_store import MessageStoreProxy
from geometry_msgs.msg import Pose, Point, Quaternion

import platform
if float(platform.python_version()[0:2]) >= 3.0:
    import io
else:
    import StringIO

"""
listens to incoming uav id 
if uav id does not exist in database:
    request query of uav information
    only update the uav position 
else uav id does not exist in database:
    log new information about uav

UAV information recorded in database: DONE
    -uav name which is the id for this situation
    -uav position information, global and local
    -uav battery 
    -uav service request
    -uav Mode

third party service sees what information it requests 
if it requests the service then will publish information/control 
of drone

Be able to remove UAV from database:
    -request uav id number
    -get all documents of uav id number
    -remove all from database

"""

if __name__ == '__main__':

    rospy.init_node("example_message_store_client")

    rate = rospy.Rate(0.5)

    msg_store = MessageStoreProxy(collection='data_service')

    p = Pose(Point(0, 1, 2), Quaternion(3, 4,  5, 6))

    #while not rospy.is_shutdown():
    try:

        # insert a pose object with a name, store the id from db
        p_id = msg_store.insert_named("uav2", p)

        # this is how you retrieve a query get it back with a name
        print(msg_store.query_named("uav2", Pose._type))

        p.position.x = 666

        # update it with a name
        #msg_store.update_named("hello world", p)

        p.position.y = 2020

        # update the other inserted one using the id
        msg_store.update_id(p_id, p)    

        stored_p, meta = msg_store.query_id(p_id, Pose._type)

        assert stored_p.position.x == 666
        assert stored_p.position.y == 2020
    
        """QUERYS"""
        print("stored object ok")
        print("stored object inserted at %s (UTC rostime) by %s" % (meta['inserted_at'], meta['inserted_by']))
        print("stored object last updated at %s (UTC rostime) by %s" % (meta['last_updated_at'], meta['last_updated_by']))

        # get it back with a name
        print(msg_store.query_named("uav0", Pose._type))

        # try to get it back with an incorrect name, so get None instead
        print(msg_store.query_named("my favourite position", Pose._type))

        # get all poses
        print(msg_store.query(Pose._type))

        # get the latest one pose
        print(msg_store.query(Pose._type, sort_query=[("$natural", -1)], single=True))

        # get all non-existant typed objects, so get an empty list back
        print(msg_store.query( "not my type"))

        # get all poses where the y position is 1
        print(msg_store.query(Pose._type, {"position.y": 1}))

        # get all poses where the y position greater than 0
        print(msg_store.query(Pose._type, {"position.y": {"$gt": 0}}))

        #rate.sleep()

    except rospy.ServiceException as e:
        print("Service call failed: %s"%e)



