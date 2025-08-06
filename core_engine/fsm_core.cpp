
#define FSM_CORE_BUILD_DLL
#include "fsm_core.h"
#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <memory>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

struct State
{
    std::string name;
    std::string entry_action;
    std::string during_action;
    std::string exit_action;
    bool is_initial = false;
    bool is_final = false;
};

struct Transition
{
    std::string source;
    std::string target;
    std::string event;
    std::string condition;
    std::string action;
};

class FsmSimulator
{
public:
    FsmSimulator() { reset(); }

    void loadFromJson(const std::string &json_str)
    {
        states_.clear();
        state_map_.clear();
        transitions_.clear();

        auto data = json::parse(json_str);

        for (const auto &s_data : data["states"])
        {
            State s;
            s.name = s_data.value("name", "");
            s.entry_action = s_data.value("entry_action", "");
            s.during_action = s_data.value("during_action", "");
            s.exit_action = s_data.value("exit_action", "");
            s.is_initial = s_data.value("is_initial", false);
            s.is_final = s_data.value("is_final", false);
            states_.push_back(s);
        }

        for (auto &state : states_)
        {
            state_map_[state.name] = &state;
        }

        for (const auto &t_data : data["transitions"])
        {
            Transition t;
            t.source = t_data.value("source", "");
            t.target = t_data.value("target", "");
            t.event = t_data.value("event", "");
            t.condition = t_data.value("condition", "");
            t.action = t_data.value("action", "");
            transitions_.push_back(t);
        }
    }

    void setInitialVariables(const std::string &json_str)
    {
        initial_variables_.clear();
        auto data = json::parse(json_str);
        for (auto &el : data.items())
        {
            initial_variables_[el.key()] = el.value().dump();
        }
    }

    void reset()
    {
        action_log_.clear();
        variables_ = initial_variables_;
        current_tick_ = 0;
        current_state_path_.clear();
        pending_transition_.reset();
        internal_event_queue_.clear();

        State *initial_state = nullptr;
        for (auto &s : states_)
        {
            if (s.is_initial)
            {
                initial_state = &s;
                break;
            }
        }
        if (!initial_state && !states_.empty())
        {
            initial_state = &states_[0];
        }

        if (initial_state)
        {
            enterState(initial_state);
        }
    }

    void step(const std::string &event_name_str)
    {
        action_log_.clear();

        // Add external event to queue if present
        if (!event_name_str.empty())
        {
            internal_event_queue_.push_back(event_name_str);
        }

        if (current_state_path_.empty())
            return;

        // On a "no-event" step, just run the during action and queued events.
        if (event_name_str.empty())
        {
            current_tick_++;
            executeAction("DURING_ACTION", current_state_path_.back()->during_action);
        }

        bool transition_taken_this_step = false;
        while (!internal_event_queue_.empty() && !transition_taken_this_step)
        {
            std::string current_event = internal_event_queue_.front();
            internal_event_queue_.erase(internal_event_queue_.begin());

            if (current_tick_ == 0 || !event_name_str.empty())
            {
                current_tick_++;
            }

            State *current_leaf_state = current_state_path_.back();

            for (const auto &trans : transitions_)
            {
                if (trans.source == current_leaf_state->name && trans.event == current_event)
                {
                    if (!trans.condition.empty())
                    {
                        // Condition exists: ask Python to evaluate it.
                        logAction("AWAIT_CONDITION", trans.condition);
                        pending_transition_ = std::make_unique<Transition>(trans);
                        return; // Pause C++ execution
                    }

                    // No condition: execute transition immediately.
                    executeTransition(trans);
                    transition_taken_this_step = true;
                    break;
                }
            }
        }
    }

    void resolve_condition(bool result)
    {
        action_log_.clear();
        if (!pending_transition_)
            return;

        if (result)
        {
            executeTransition(*pending_transition_);
        }
        else
        {
            logAction("INFO", "Condition failed, transition aborted.");
        }
        pending_transition_.reset();
    }

    void queue_internal_event(const std::string &event_name)
    {
        internal_event_queue_.push_back(event_name);
    }

    std::string getCurrentStateName() const
    {
        if (current_state_path_.empty())
            return "Halted";
        return current_state_path_.back()->name;
    }

    std::string getVariablesJson() const
    {
        json j = variables_;
        return j.dump();
    }

    std::string getAndClearLogJson()
    {
        json j = action_log_;
        action_log_.clear();
        return j.dump();
    }

    int getCurrentTick() const { return current_tick_; }

private:
    void enterState(State *state)
    {
        current_state_path_.push_back(state);
        executeAction("ENTRY_STATE", state->entry_action);
    }

    void executeTransition(const Transition &trans)
    {
        State *current_leaf_state = current_state_path_.back();
        executeAction("EXIT_STATE", current_leaf_state->exit_action);
        executeAction("TRANSITION_ACTION", trans.action);

        current_state_path_.pop_back();

        State *new_state = state_map_[trans.target];
        if (new_state)
        {
            enterState(new_state);
        }
    }

    void executeAction(const std::string &type, const std::string &code)
    {
        if (!code.empty())
        {
            logAction(type, code);
        }
    }

    void logAction(const std::string &type, const std::string &data)
    {
        if (!data.empty())
        {
            json log_entry;
            log_entry["type"] = type;
            log_entry["data"] = data;
            action_log_.push_back(log_entry.dump());
        }
    }

    std::vector<State> states_;
    std::map<std::string, State *> state_map_;
    std::vector<Transition> transitions_;

    int current_tick_;
    std::vector<State *> current_state_path_;
    std::map<std::string, std::string> variables_;
    std::map<std::string, std::string> initial_variables_;
    std::vector<std::string> action_log_;

    std::unique_ptr<Transition> pending_transition_;
    std::vector<std::string> internal_event_queue_;
};

// C API Implementation
FSM_API FSM_HANDLE create_fsm() { return new FsmSimulator(); }
FSM_API void destroy_fsm(FSM_HANDLE handle) { delete static_cast<FsmSimulator *>(handle); }

FSM_API bool load_fsm_from_json(FSM_HANDLE handle, const char *json_string)
{
    try
    {
        static_cast<FsmSimulator *>(handle)->loadFromJson(json_string);
        return true;
    }
    catch (const std::exception &)
    {
        return false;
    }
}

FSM_API void set_initial_variables_from_json(FSM_HANDLE handle, const char *json_string)
{
    static_cast<FsmSimulator *>(handle)->setInitialVariables(json_string);
}

FSM_API void reset_fsm(FSM_HANDLE handle) { static_cast<FsmSimulator *>(handle)->reset(); }
FSM_API void step(FSM_HANDLE handle, const char *event_name) { static_cast<FsmSimulator *>(handle)->step(event_name ? std::string(event_name) : ""); }
FSM_API void resolve_condition(FSM_HANDLE handle, bool result) { static_cast<FsmSimulator *>(handle)->resolve_condition(result); }
FSM_API void queue_internal_event(FSM_HANDLE handle, const char *event_name) { static_cast<FsmSimulator *>(handle)->queue_internal_event(event_name); }

char *copy_string_to_c(const std::string &s)
{
    char *c_str = new char[s.length() + 1];
#ifdef _WIN32
    strcpy_s(c_str, s.length() + 1, s.c_str());
#else
    std::strcpy(c_str, s.c_str());
#endif
    return c_str;
}

FSM_API const char *get_current_state_name(FSM_HANDLE handle)
{
    std::string name = static_cast<FsmSimulator *>(handle)->getCurrentStateName();
    return copy_string_to_c(name);
}

FSM_API const char *get_variables_json(FSM_HANDLE handle)
{
    std::string vars = static_cast<FsmSimulator *>(handle)->getVariablesJson();
    return copy_string_to_c(vars);
}

FSM_API const char *get_and_clear_log_json(FSM_HANDLE handle)
{
    std::string log = static_cast<FsmSimulator *>(handle)->getAndClearLogJson();
    return copy_string_to_c(log);
}

FSM_API int get_current_tick(FSM_HANDLE handle) { return static_cast<FsmSimulator *>(handle)->getCurrentTick(); }
FSM_API void free_string_memory(char *str) { delete[] str; }