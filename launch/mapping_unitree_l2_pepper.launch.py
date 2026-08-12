#!/usr/bin/python3
# FAST-LIVO2 on Pepper: Unitree L2 (/points, /imu/data) + RealSense color
# (/camera/color/image_raw, already raw in the bag so no republisher needed).

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node


def generate_launch_description():
    config_file_dir = os.path.join(get_package_share_directory("fast_livo"), "config")
    rviz_cfg_dir = os.path.join(get_package_share_directory("fast_livo"), "rviz_cfg")

    # Selectable so the RealSense-IMU variant can be launched without editing
    # this file:  config_file:=unitree_l2_pepper_rsimu.yaml
    lio_config = PathJoinSubstitution([config_file_dir,
                                       LaunchConfiguration("config_file")])
    camera_config = os.path.join(config_file_dir, "camera_realsense_pepper.yaml")

    # Bag replay publishes /clock, and without this every node here runs on the
    # WALL clock while the data carries bag time. RViz then silently drops every
    # cloud ("timestamp on the message is earlier than all the data in the
    # transform cache") -- the same trap documented in FAST_LIO's mapping.launch.py.
    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time", default_value="False",
        description="True when replaying a bag with --clock.",
    )

    # Must match publish.body_frame in the selected config:
    # unitree_l2_pepper.yaml -> l2lidar_frame_imu,
    # unitree_l2_pepper_rsimu.yaml -> camera_imu_optical_frame.
    # A mismatch silently yields a wrong odom -> base_footprint.
    lidar_imu_frame_arg = DeclareLaunchArgument(
        "lidar_imu_frame", default_value="l2lidar_frame_imu",
        description="Static-tree frame the estimated body corresponds to, used "
                    "by lio_map_odom_bridge to close odom -> base_footprint.",
    )

    config_file_arg = DeclareLaunchArgument(
        "config_file", default_value="unitree_l2_pepper.yaml",
        description="Config under fast_livo/config. unitree_l2_pepper.yaml uses "
                    "the L2's own IMU; unitree_l2_pepper_rsimu.yaml uses the "
                    "RealSense's (/camera/imu) -- see utils/L2_IMU/REPORT.md.",
    )

    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz", default_value="False", description="Whether to launch Rviz2",
    )

    # pepper_l2.rviz is fast_livo2.rviz retargeted onto the rig's tree: Fixed Frame
    # camera_init -> odom (the gravity-levelled frame lio_map_odom_bridge publishes
    # as a static parent of odom_lidar), the ThirdPersonFollower target "drone"
    # (upstream's frame, absent here) -> base_footprint, and the Odometry display's
    # topic /aft_mapped_to_init -> /odom_lio. With a bogus follow target the camera
    # stays at the origin while the robot drives away.
    rviz_cfg_arg = DeclareLaunchArgument(
        "rviz_cfg", default_value=os.path.join(rviz_cfg_dir, "pepper_l2.rviz"),
        description="RViz2 config to load with use_rviz:=True",
    )

    # Closes odom -> base_footprint from /odom_lio, exactly as FAST-LIO and
    # Point-LIO do. Requires publish.publish_tf: false in the config, so
    # FAST-LIVO2 does not also broadcast the same edge.
    odom_bridge_node = Node(
        package="fast_lio",
        executable="lio_map_odom_bridge.py",
        name="lio_map_odom_bridge",
        output="screen",
        parameters=[{
            "odom_topic": "/odom_lio",
            "lidar_imu_frame": LaunchConfiguration("lidar_imu_frame"),
            "use_sim_time": LaunchConfiguration("use_sim_time"),
        }],
    )

    return LaunchDescription([
        use_sim_time_arg,
        lidar_imu_frame_arg,
        config_file_arg,
        use_rviz_arg,
        odom_bridge_node,
        rviz_cfg_arg,

        # global parameter server holding the vikit camera model params
        Node(
            package="demo_nodes_cpp",
            executable="parameter_blackboard",
            name="parameter_blackboard",
            parameters=[camera_config, {"use_sim_time": LaunchConfiguration("use_sim_time")}],
            output="screen",
        ),

        # vikit's getRemoteParam waits only 100ms for the blackboard's parameter
        # service before falling back to an empty cam_model, which aborts the node
        # with "Camera model not correctly specified". Start the mapper once the
        # blackboard is already serving.
        TimerAction(
            period=3.0,
            actions=[
                Node(
                    package="fast_livo",
                    executable="fastlivo_mapping",
                    # Standard odometry topic across every LIO variant; see
                    # FAST_LIO/launch/mapping.launch.py. FAST-LIVO2 publishes
                    # /aft_mapped_to_init natively.
                    remappings=[("/aft_mapped_to_init", "/odom_lio")],
                    name="laserMapping",
                    parameters=[lio_config, {"use_sim_time": LaunchConfiguration("use_sim_time")}],
                    output="screen",
                ),
            ],
        ),

        Node(
            condition=IfCondition(LaunchConfiguration("use_rviz")),
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            arguments=["-d", LaunchConfiguration("rviz_cfg")],
            parameters=[{"use_sim_time": LaunchConfiguration("use_sim_time")}],
            output="screen",
        ),
    ])
