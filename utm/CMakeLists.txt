cmake_minimum_required(VERSION 3.10.0)
project(utm)

# set this to path to AirSim root folder if you want your catkin workspace in a custom directory
set(AIRSIM_ROOT /home/jnguyen/AirSim/)

# todo eigen3 in AirLib already
# find_package(Eigen3 REQUIRED) 
find_package(Boost REQUIRED)
find_package(OpenCV REQUIRED)
find_package(Eigen3 REQUIRED)

find_package(catkin REQUIRED COMPONENTS
  airsim_ros_pkgs
  airsim_tutorial_pkgs
  apriltag_ros
  cv_bridge
  image_transport
  mavros_msgs
  mongodb_store
  message_generation
  nav_msgs
  # nodelet
  # need to add mavros 
  roscpp
  rospy
  sensor_msgs
  std_msgs
  geographic_msgs
  geometry_msgs
  std_srvs
  tf2
  tf2_ros
  tf2_sensor_msgs
  tf2_geometry_msgs
  ${catkin_LIBRARIES} 
)

#python modules 
catkin_python_setup()

add_message_files(
 FILES
 LQRGain.msg
 Coords.msg
 WP.msg
)

#add_service_files(
#  FILES
#)

generate_messages(
 DEPENDENCIES
 std_msgs
 geometry_msgs
 #geographic_msgs
)

catkin_package(
  # LIBRARIES airsim_ros
  INCLUDE_DIRS
  CATKIN_DEPENDS 
  message_runtime 
  roscpp 
  std_msgs 
  airsim_ros_pkgs
  airsim_tutorial_pkgs
)

include_directories(
  include
  ${catkin_INCLUDE_DIRS}
  ${airsim_ros_pkgs_INCLUDE_DIRS}
  ${AIRSIM_ROOT}/AirLib/deps/eigen3
  ${AIRSIM_ROOT}/AirLib/include
  ${RPC_LIB_INCLUDES}
  ${AIRSIM_ROOT}/MavLinkCom/include
  ${AIRSIM_ROOT}/MavLinkCom/common_utils
  ${OpenCV_INCLUDE_DIRS}
  ${Boost_INCLUDE_DIRS}
  ${EIGEN3_INCLUDE_DIRS}
)

## Declare a cpp library
#add_library(PID src/PID.cpp)
#target_link_libraries(PID ${catkin_LIBRARIES})
#add_executable(null_test src/null_test.cpp)
#add_dependencies(null_test ${catkin_EXPORTED_TARGETS})
#target_link_libraries(null_test ${catkin_LIBRARIES})

add_executable(main_null src/main_null.cpp src/null_test.cpp)
add_dependencies(main_null ${catkin_EXPORTED_TARGETS})
target_link_libraries(main_null  ${catkin_LIBRARIES})

add_executable(test_track src/test_track.cpp src/PID.cpp)
add_dependencies(test_track ${catkin_EXPORTED_TARGETS})
target_link_libraries(test_track  ${catkin_LIBRARIES})

add_executable(offboard_test src/offboard_test.cpp src/PID.cpp src/moving_avg.cpp)
add_dependencies(offboard_test ${catkin_EXPORTED_TARGETS})
target_link_libraries(offboard_test  ${catkin_LIBRARIES})

add_executable(offboard_landing src/offboard_landing.cpp src/PID.cpp src/moving_avg.cpp)
add_dependencies(offboard_landing ${catkin_EXPORTED_TARGETS})
target_link_libraries(offboard_landing  ${catkin_LIBRARIES})

add_executable(offboard_landing_v2 src/offboard_landing_v2.cpp src/PID.cpp src/moving_avg.cpp)
add_dependencies(offboard_landing_v2 ${catkin_EXPORTED_TARGETS})
target_link_libraries(offboard_landing_v2  ${catkin_LIBRARIES})

add_executable(uas_px4_main src/uas_px4_main.cpp src/PID.cpp src/uas/uas_px4.cpp)
add_dependencies(uas_px4_main ${catkin_EXPORTED_TARGETS})
target_link_libraries(uas_px4_main  ${catkin_LIBRARIES})

add_executable(px4_att_test src/px4_att_test.cpp src/PID.cpp src/uas/uas_px4.cpp)
add_dependencies(px4_att_test ${catkin_EXPORTED_TARGETS})
target_link_libraries(px4_att_test  ${catkin_LIBRARIES})

add_executable(offboard_example src/offboard_example.cpp)
target_link_libraries(offboard_example ${catkin_LIBRARIES})

add_executable(offboard_tracking src/offboard_tracking.cpp)
target_link_libraries(offboard_tracking ${catkin_LIBRARIES})

add_executable(moving_avg_main src/moving_avg_main.cpp src/moving_avg.cpp)
add_dependencies(moving_avg_main ${catkin_EXPORTED_TARGETS})
target_link_libraries(moving_avg_main  ${catkin_LIBRARIES})

add_executable(test_px4_wp src/test_px4_wp.cpp src/PID.cpp src/uas/uas_px4.cpp)
add_dependencies(test_px4_wp ${catkin_EXPORTED_TARGETS})
target_link_libraries(test_px4_wp  ${catkin_LIBRARIES})

##################
##  Install #####
#################


install(TARGETS
    #TARGETS null_testlogger.
    ARCHIVE DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}
    LIBRARY DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}
    RUNTIME DESTINATION ${CATKIN_GLOBAL_BIN_DESTINATION}
)

catkin_install_python(PROGRAMS
    #drone stuff
    scripts/drone_image_raw.py
    scripts/offboard_drone.py
    scripts/apriltag_position_pub.py
    scripts/mavros_tf.py
    scripts/apriltag_norm.py
    scripts/ekf_tag.py
    scripts/land_permission.py
    scripts/logger.py
    scripts/user_control.py
    scripts/drone_transformation.py
    scripts/uav_mongo_query.py
    scripts/apriltag_object.py
    scripts/log_apriltag.py
    scripts/kf_design.py
    scripts/kf_logger.py
    
    
    #controller stuff
    scripts/controller/lqr.py
    scripts/controller/tag_stabilize.py

    #simpleflight stuff
    scripts/uas/test_airsim_api.py
    scripts/uas/simple_flight_drone.py
    scripts/uas/simple_land_drone.py
    scripts/uas/px4_wp_sender.py

    #data plotting tuff
    scripts/data_visualize/real_time_plot.py

    #database stuff
    scripts/landing_db/data_service_provider.py
    scripts/landing_db/landing_service_database.py

    #third party landing server
    # scripts/landing_service_nodes/pre_landing_service.py
    # scripts/landing_service_nodes/path_sender_service.py
    # scripts/landing_service_nodes/landing_state_service.py
    # scripts/landing_service_nodes/post_flight_service.py
    # scripts/landing_service_nodes/path_home_sender_service.py
    # scripts/landing_service_nodes/zone_observer.py
    scripts/uss/path_planning_service/path_planning_service.py

    #more third party stuff
    scripts/landing_service_nodes/landing_inbound_service.py
    scripts/landing_service_nodes/landing_permission_service.py
    

    #test setups
    tests/kf_displace.py
    tests/apriltag_displace.py
    tests/mongo_db_test.py
    tests/mongo_recieve_info.py
    tests/landing_zone_test.py
    tests/landing_service_databaseTest.py
    tests/data_service_providerTest.py
    DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

# Mark cpp header files for installation
install(
  DIRECTORY include/${PROJECT_NAME}/
  DESTINATION ${CATKIN_PACKAGE_INCLUDE_DESTINATION}
  FILES_MATCHING PATTERN "*.h"
)

install(FILES 
  #list of necessary files (xml...)
  #README.md
  # settings.json
  # nodelet_plugins.xml
  #DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

# for shipping binaries. run `$ catin_make install`
install(DIRECTORY
  launch
  rviz
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
  # PATTERN ".git" EXCLUDE
)
