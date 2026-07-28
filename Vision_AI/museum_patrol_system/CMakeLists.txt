cmake_minimum_required(VERSION 3.8)
project(museum_patrol_system)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/MuseumState.msg"
  "msg/MuseumCommand.msg"
)

ament_python_install_package(museum_patrol_nodes
  PACKAGE_DIR museum_patrol_nodes
)

install(
  PROGRAMS
    scripts/yolo_detector
    scripts/jpeg_compressor
    scripts/task_manager
    scripts/patrol_navigation
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY launch config maps rviz
  DESTINATION share/${PROJECT_NAME}
)

install(
  FILES package.xml
  DESTINATION share/${PROJECT_NAME}
)

install(
  FILES resource/museum_patrol_system
  DESTINATION share/ament_index/resource_index/packages
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
