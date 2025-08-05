-- -START OF FILE fsm_designer_project / core_engine / fsm_core.h-- -
#ifndef FSM_CORE_H
#define FSM_CORE_H

// Macro for handling DLL export/import on Windows
#if defined(_WIN32)
#if defined(FSM_CORE_BUILD_DLL)
#define FSM_API __declspec(dllexport)
#else
#define FSM_API __declspec(dllimport)
#endif
#else
#define FSM_API
#endif

    // Opaque handle to the C++ FsmSimulator object
    typedef void *FSM_HANDLE;

#ifdef __cplusplus
extern "C"
{
#endif

    // --- Lifecycle ---
    FSM_API FSM_HANDLE create_fsm();
    FSM_API void destroy_fsm(FSM_HANDLE handle);

    // --- Configuration ---
    FSM_API bool load_fsm_from_json(FSM_HANDLE handle, const char *json_string);
    FSM_API void set_initial_variables_from_json(FSM_HANDLE handle, const char *json_string);
    FSM_API void reset_fsm(FSM_HANDLE handle);

    // --- Simulation ---
    FSM_API void step(FSM_HANDLE handle, const char *event_name);

    // --- Data Retrieval ---
    // NOTE: All functions returning char* return memory allocated by C++.
    // The caller (Python) is responsible for freeing it with free_string_memory().
    FSM_API const char *get_current_state_name(FSM_HANDLE handle);
    FSM_API const char *get_variables_json(FSM_HANDLE handle);
    FSM_API const char *get_and_clear_log_json(FSM_HANDLE handle);
    FSM_API int get_current_tick(FSM_HANDLE handle);

    // --- Memory Management ---
    FSM_API void free_string_memory(char *str);

#ifdef __cplusplus
}
#endif

#endif // FSM_CORE_H
-- -END OF FILE fsm_designer_project / core_engine / fsm_core.h-- -