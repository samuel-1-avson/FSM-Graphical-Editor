cd path\to\your\project\fsm_designer_project\core_engine
# CMake build script for the FSM Core Engine

cmake_minimum_required(VERSION 3.10)
project(FsmCore CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create the shared library from our source file
add_library(fsm_core SHARED fsm_core.cpp)

# Tell the compiler where to find the nlohmann/json.hpp header
# It's in the directory ../dependencies relative to this CMakeLists.txt
target_include_directories(fsm_core PUBLIC 
    "${CMAKE_CURRENT_SOURCE_DIR}/../dependencies"
)

# On Windows, add a definition so our FSM_API macro uses dllexport
if(WIN32)
    target_compile_definitions(fsm_core PRIVATE FSM_CORE_BUILD_DLL)
endif()
