from setuptools import setup

package_name = 'museum_patrol_nodes'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Museum Patrol Team',
    maintainer_email='dev@museum-patrol.local',
    description='Museum patrol robot nodes (YOLO vision + task manager).',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'yolo_detector = museum_patrol_nodes.yolo_detector_node:main',
            'jpeg_compressor = museum_patrol_nodes.jpeg_camera_compressor_node:main',
            'task_manager = museum_patrol_nodes.task_manager_node:main',
            'patrol_navigation = museum_patrol_nodes.patrol_navigation_node:main',
        ],
    },
)
