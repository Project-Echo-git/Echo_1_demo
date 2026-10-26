cmake_minimum_required(VERSION 3.16)
project(PercipioRgbViewer LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(VCAMERA_SDK_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../percipio_ball_tracker_cpp/VcameraSDK-26.1.5/cpp" CACHE PATH "Percipio C++ SDK")
set(OpenCV_DIR "${CMAKE_CURRENT_SOURCE_DIR}/deps/opencv/build" CACHE PATH "OpenCV package directory")
find_package(OpenCV REQUIRED COMPONENTS core highgui)
add_executable(percipio_test percipio_test.cpp)
target_include_directories(percipio_test PRIVATE "${VCAMERA_SDK_DIR}/include" ${OpenCV_INCLUDE_DIRS})
target_link_libraries(percipio_test PRIVATE "${VCAMERA_SDK_DIR}/win/Release/lib/ucvcameraapi.lib" ${OpenCV_LIBS})
add_custom_command(TARGET percipio_test POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
    "${VCAMERA_SDK_DIR}/win/Release/bin" "$<TARGET_FILE_DIR:percipio_test>"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
    "$<TARGET_FILE:opencv_world>" "$<TARGET_FILE_DIR:percipio_test>")
