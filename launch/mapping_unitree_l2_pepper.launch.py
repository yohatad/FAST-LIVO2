#!/usr/bin/python3
# FAST-LIVO2 on Pepper: Unitree L2 (/points, /imu/data) + RealSense color
# (/camera/color/image_raw, already raw in the bag so no republisher needed).

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node


def generate_launch_description():
    config_file_dir = os.path.join(get_package_share_directory("fast_livo"), "config")
    rviz_cfg_dir = os.path.join(get_package_share_directory("fast_livo"), "rviz_cfg")

    lio_config = os.path.join(config_file_dir, "unitree_l2_pepper.yaml")
    camera_config = os.path.join(config_file_dir, "camera_realsense_pepper.yaml")

    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz", default_value="False", description="Whether to launch Rviz2",
    )

    # pepper_l2.rviz is fast_livo2.rviz with the ThirdPersonFollower retargeted from
    # "drone" (upstream's frame, absent here) to "aft_mapped", the body frame
    # LIVMapper broadcasts. With a bogus target the camera stays at the origin while
    # the robot drives away. Fixed Frame stays camera_init.
    rviz_cfg_arg = DeclareLaunchArgument(
        "rviz_cfg", default_value=os.path.join(rviz_cfg_dir, "pepper_l2.rviz"),
        description="RViz2 config to load with use_rviz:=True",
    )

    return LaunchDescription([
        use_rviz_arg,
        rviz_cfg_arg,

        # global parameter server holding the vikit camera model params
        Node(
            package="demo_nodes_cpp",
            executable="parameter_blackboard",
            name="parameter_blackboard",
            parameters=[camera_config],
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
                    name="laserMapping",
                    parameters=[lio_config],
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
            output="screen",
        ),
    ])
