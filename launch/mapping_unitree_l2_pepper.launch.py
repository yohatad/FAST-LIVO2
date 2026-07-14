#!/usr/bin/python3
# FAST-LIVO2 on Pepper: Unitree L2 (/points, /imu/data) + RealSense color
# (/camera/color/image_raw, already raw in the bag so no republisher needed).

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node


def generate_launch_description():
    config_file_dir = os.path.join(get_package_share_directory("fast_livo"), "config")
    rviz_config_file = os.path.join(get_package_share_directory("fast_livo"), "rviz_cfg", "M300.rviz")

    lio_config = os.path.join(config_file_dir, "unitree_l2_pepper.yaml")
    camera_config = os.path.join(config_file_dir, "camera_realsense_pepper.yaml")

    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz", default_value="False", description="Whether to launch Rviz2",
    )

    return LaunchDescription([
        use_rviz_arg,

        # global parameter server holding the vikit camera model params
        Node(
            package="demo_nodes_cpp",
            executable="parameter_blackboard",
            name="parameter_blackboard",
            parameters=[camera_config],
            output="screen",
        ),

        Node(
            package="fast_livo",
            executable="fastlivo_mapping",
            name="laserMapping",
            parameters=[lio_config],
            output="screen",
        ),

        Node(
            condition=IfCondition(LaunchConfiguration("use_rviz")),
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            arguments=["-d", rviz_config_file],
            output="screen",
        ),
    ])
