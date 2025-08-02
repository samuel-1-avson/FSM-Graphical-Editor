# fsm_designer_project/examples/matlab_integration_example.py

"""
Example demonstrating the enhanced MATLAB integration capabilities
"""

import sys
import os
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QProgressBar, QLabel, QHBoxLayout, QGroupBox, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox
from PyQt5.QtCore import QTimer, pyqtSlot

# Import our enhanced MATLAB integration modules
from core.matlab_integration import (
    MatlabConnection, 
    SimulationConfig, 
    CodeGenConfig, 
    MatlabModelValidator,
    MatlabDiagnostics,
    EngineState
)
from managers.matlab_simulation_manager import (
    MatlabSimulationManager,
    SimulationState,
    SimulationData,
    SimulationDataLogger,
    MatlabPerformanceMonitor,
    create_simulation_manager_with_logging,
    create_default_simulation_config
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatlabIntegrationDemo(QMainWindow):
    """
    Demo application showcasing enhanced MATLAB integration features
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced MATLAB Integration Demo")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize components
        self.matlab_connection = None
        self.simulation_manager = None
        self.data_logger = None
        self.performance_monitor = MatlabPerformanceMonitor()
        
        # Setup UI
        self.setup_ui()
        
        # Initialize MATLAB connection
        self.initialize_matlab()
    
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Status section
        self.setup_status_section(layout)
        
        # Configuration section
        self.setup_configuration_section(layout)
        
        # Model operations section
        self.setup_model_operations_section(layout)
        
        # Simulation section
        self.setup_simulation_section(layout)
        
        # Output section
        self.setup_output_section(layout)
    
    def setup_status_section(self, parent_layout):
        """Setup status display section"""
        status_group = QGroupBox("MATLAB Engine Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("padding: 10px; border: 1px solid gray; background: lightgray;")
        status_layout.addWidget(self.status_label)
        
        # Diagnostics button
        diag_btn = QPushButton("Run Diagnostics")
        diag_btn.clicked.connect(self.run_diagnostics)
        status_layout.addWidget(diag_btn)
        
        parent_layout.addWidget(status_group)
    
    def setup_configuration_section(self, parent_layout):
        """Setup configuration section"""
        config_group = QGroupBox("Simulation Configuration")
        config_layout = QHBoxLayout(config_group)
        
        # Left column - basic settings
        left_layout = QVBoxLayout()
        
        # Stop time
        stop_time_layout = QHBoxLayout()
        stop_time_layout.addWidget(QLabel("Stop Time:"))
        self.stop_time_spin = QDoubleSpinBox()
        self.stop_time_spin.setRange(0.1, 1000.0)
        self.stop_time_spin.setValue(10.0)
        self.stop_time_spin.setSuffix(" s")
        stop_time_layout.addWidget(self.stop_time_spin)
        left_layout.addLayout(stop_time_layout)
        
        # Step size
        step_size_layout = QHBoxLayout()
        step_size_layout.addWidget(QLabel("Step Size:"))
        self.step_size_spin = QDoubleSpinBox()
        self.step_size_spin.setRange(0.001, 1.0)
        self.step_size_spin.setValue(0.1)
        self.step_size_spin.setSuffix(" s")
        step_size_layout.addWidget(self.step_size_spin)
        left_layout.addLayout(step_size_layout)
        
        # Solver
        solver_layout = QHBoxLayout()
        solver_layout.addWidget(QLabel("Solver:"))
        self.solver_combo = QComboBox()
        self.solver_combo.addItems(['ode45', 'ode23', 'ode1', 'ode2', 'ode4'])
        self.solver_combo.setCurrentText('ode45')
        solver_layout.addWidget(self.solver_combo)
        left_layout.addLayout(solver_layout)
        
        config_layout.addLayout(left_layout)
        
        # Right column - advanced settings
        right_layout = QVBoxLayout()
        
        self.save_output_check = QCheckBox("Save Output")
        self.save_output_check.setChecked(True)
        right_layout.addWidget(self.save_output_check)
        
        self.save_states_check = QCheckBox("Save States")
        self.save_states_check.setChecked(True)
        right_layout.addWidget(self.save_states_check)
        
        self.limit_data_check = QCheckBox("Limit Data Points")
        self.limit_data_check.setChecked(True)
        right_layout.addWidget(self.limit_data_check)
        
        config_layout.addLayout(right_layout)
        
        parent_layout.addWidget(config_group)
    
    def setup_model_operations_section(self, parent_layout):
        """Setup model operations section"""
        model_group = QGroupBox("Model Operations")
        model_layout = QHBoxLayout(model_group)
        
        # Model generation
        gen_btn = QPushButton("Generate Demo Model")
        gen_btn.clicked.connect(self.generate_demo_model)
        model_layout.addWidget(gen_btn)
        
        # Model validation
        validate_btn = QPushButton("Validate Model")
        validate_btn.clicked.connect(self.validate_current_model)
        model_layout.addWidget(validate_btn)
        
        # Code generation
        codegen_btn = QPushButton("Generate Code")
        codegen_btn.clicked.connect(self.generate_code)
        model_layout.addWidget(codegen_btn)
        
        parent_layout.addWidget(model_group)
    
    def setup_simulation_section(self, parent_layout):
        """Setup simulation control section"""
        sim_group = QGroupBox("Simulation Control")
        sim_layout = QVBoxLayout(sim_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Simulation")
        self.start_btn.clicked.connect(self.start_simulation)
        button_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_simulation)
        self.pause_btn.setEnabled(False)
        button_layout.addWidget(self.pause_btn)
        
        self.resume_btn = QPushButton("Resume")
        self.resume_btn.clicked.connect(self.resume_simulation)
        self.resume_btn.setEnabled(False)
        button_layout.addWidget(self.resume_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_simulation)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        sim_layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        sim_layout.addWidget(self.progress_bar)
        
        # Current state display
        self.current_state_label = QLabel("Current State: Unknown")
        self.current_state_label.setStyleSheet("font-weight: bold; padding: 5px; border: 1px solid gray;")
        sim_layout.addWidget(self.current_state_label)
        
        # Performance metrics
        self.performance_label = QLabel("Performance: No data")
        sim_layout.addWidget(self.performance_label)
        
        parent_layout.addWidget(sim_group)
    
    def setup_output_section(self, parent_layout):
        """Setup output display section"""
        output_group = QGroupBox("Output & Logs")
        output_layout = QVBoxLayout(output_group)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(200)
        output_layout.addWidget(self.output_text)
        
        # Export buttons
        export_layout = QHBoxLayout()
        
        export_csv_btn = QPushButton("Export Data to CSV")
        export_csv_btn.clicked.connect(self.export_data)
        export_layout.addWidget(export_csv_btn)
        
        clear_btn = QPushButton("Clear Output")
        clear_btn.clicked.connect(self.output_text.clear)
        export_layout.addWidget(clear_btn)
        
        output_layout.addLayout(export_layout)
        
        parent_layout.addWidget(output_group)
    
    def initialize_matlab(self):
        """Initialize MATLAB connection and simulation manager"""
        self.log_message("Initializing MATLAB integration...")
        
        # Create MATLAB connection
        self.matlab_connection = MatlabConnection()
        self.matlab_connection.connectionStatusChanged.connect(self.on_connection_status_changed)
        self.matlab_connection.modelGenerationFinished.connect(self.on_model_generation_finished)
        self.matlab_connection.codeGenerationFinished.connect(self.on_code_generation_finished)
        
        # Create simulation manager with logging
        self.simulation_manager, self.data_logger = create_simulation_manager_with_logging()
        
        # Connect simulation signals
        self.simulation_manager.engine_status_changed.connect(self.on_simulation_engine_status)
        self.simulation_manager.simulation_state_changed.connect(self.on_simulation_state_changed)
        self.simulation_manager.simulation_data_updated.connect(self.on_simulation_data_updated)
        self.simulation_manager.simulation_progress.connect(self.on_simulation_progress)
        self.simulation_manager.simulation_completed.connect(self.on_simulation_completed)
        self.simulation_manager.error_occurred.connect(self.on_error_occurred)
        
        # Setup performance monitoring timer
        self.perf_timer = QTimer()
        self.perf_timer.timeout.connect(self.update_performance_metrics)
        self.perf_timer.start(1000)  # Update every second
    
    @pyqtSlot(EngineState, str)
    def on_connection_status_changed(self, state, message):
        """Handle connection status changes"""
        if state == EngineState.CONNECTED:
            self.status_label.setText(f"✓ Connected: {message}")
            self.status_label.setStyleSheet("padding: 10px; border: 1px solid green; background: lightgreen;")
        elif state == EngineState.ERROR:
            self.status_label.setText(f"✗ Error: {message}")
            self.status_label.setStyleSheet("padding: 10px; border: 1px solid red; background: lightcoral;")
        else:
            self.status_label.setText(f"○ {state.value.title()}: {message}")
            self.status_label.setStyleSheet("padding: 10px; border: 1px solid orange; background: lightyellow;")
        
        self.log_message(f"Connection: {message}")
    
    @pyqtSlot(bool, str)
    def on_simulation_engine_status(self, connected, message):
        """Handle simulation engine status"""
        if connected:
            self.log_message(f"Simulation engine ready: {message}")
        else:
            self.log_message(f"Simulation engine not ready: {message}")
    
    @pyqtSlot(SimulationState, str)
    def on_simulation_state_changed(self, state, message):
        """Handle simulation state changes"""
        self.log_message(f"Simulation state: {state.value} - {message}")
        
        # Update UI based on state
        if state == SimulationState.RUNNING:
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.resume_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.performance_monitor.start_monitoring()
        elif state == SimulationState.PAUSED:
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
        elif state in [SimulationState.IDLE, SimulationState.COMPLETED, SimulationState.ERROR]:
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.progress_bar.setValue(0)
    
    @pyqtSlot(SimulationData)
    def on_simulation_data_updated(self, data):
        """Handle simulation data updates"""
        self.current_state_label.setText(f"Current State: {data.active_state} (t={data.time:.2f}s)")
        self.performance_monitor.update(data.time)
    
    @pyqtSlot(float, float)
    def on_simulation_progress(self, current_time, total_time):
        """Handle simulation progress updates"""
        if total_time > 0:
            progress = int((current_time / total_time) * 100)
            self.progress_bar.setValue(progress)
            self.progress_bar.setFormat(f"{current_time:.2f}s / {total_time:.2f}s ({progress}%)")
    
    @pyqtSlot(bool, str, dict)
    def on_simulation_completed(self, success, message, final_data):
        """Handle simulation completion"""
        if success:
            self.log_message(f"Simulation completed successfully: {message}")
            stats = self.data_logger.get_statistics()
            self.log_message(f"Statistics: {stats}")
        else:
            self.log_message(f"Simulation failed: {message}")
    
    @pyqtSlot(str)
    def on_error_occurred(self, error_message):
        """Handle errors"""
        self.log_message(f"ERROR: {error_message}")
    
    @pyqtSlot(bool, str, str)
    def on_model_generation_finished(self, success, message, output_path):
        """Handle model generation completion"""
        if success:
            self.log_message(f"Model generated successfully: {output_path}")
        else:
            self.log_message(f"Model generation failed: {message}")
    
    @pyqtSlot(bool, str, str)
    def on_code_generation_finished(self, success, message, output_path):
        """Handle code generation completion"""
        if success:
            self.log_message(f"Code generated successfully: {output_path}")
        else:
            self.log_message(f"Code generation failed: {message}")
    
    def get_simulation_config(self) -> SimulationConfig:
        """Get simulation configuration from UI"""
        return SimulationConfig(
            stop_time=self.stop_time_spin.value(),
            step_size=self.step_size_spin.value(),
            solver=self.solver_combo.currentText(),
            save_output=self.save_output_check.isChecked(),
            save_states=self.save_states_check.isChecked(),
            limit_data_points=self.limit_data_check.isChecked()
        )
    
    def generate_demo_model(self):
        """Generate a demo finite state machine model"""
        self.log_message("Generating demo FSM model...")
        
        # Define a simple traffic light FSM
        states = [
            {
                'name': 'Green',
                'x': 100, 'y': 100, 'width': 120, 'height': 60,
                'is_initial': True,
                'entry_action': 'light_color = "green"',
                'during_action': 'timer = timer + 1'
            },
            {
                'name': 'Yellow',
                'x': 300, 'y': 100, 'width': 120, 'height': 60,
                'entry_action': 'light_color = "yellow"',
                'during_action': 'timer = timer + 1'
            },
            {
                'name': 'Red',
                'x': 200, 'y': 250, 'width': 120, 'height': 60,
                'entry_action': 'light_color = "red"',
                'during_action': 'timer = timer + 1'
            }
        ]
        
        transitions = [
            {
                'source': 'Green',
                'target': 'Yellow',
                'event': 'timer_event',
                'condition': 'timer >= 30',
                'action': 'timer = 0'
            },
            {
                'source': 'Yellow',
                'target': 'Red',
                'event': 'timer_event',
                'condition': 'timer >= 5',
                'action': 'timer = 0'
            },
            {
                'source': 'Red',
                'target': 'Green',
                'event': 'timer_event',
                'condition': 'timer >= 25',
                'action': 'timer = 0'
            }
        ]
        
        # Validate the model definition
        valid_states, state_errors = MatlabModelValidator.validate_states(states)
        valid_transitions, trans_errors = MatlabModelValidator.validate_transitions(transitions, states)
        
        if not valid_states or not valid_transitions:
            error_msg = "Model validation failed:\n" + "\n".join(state_errors + trans_errors)
            self.log_message(error_msg)
            return
        
        # Generate the model
        output_dir = str(Path.cwd() / "generated_models")
        os.makedirs(output_dir, exist_ok=True)
        
        self.matlab_connection.generate_simulink_model(
            states, transitions, output_dir, "TrafficLightFSM"
        )
    
    def validate_current_model(self):
        """Validate the current model"""
        model_path = Path.cwd() / "generated_models" / "TrafficLightFSM.slx"
        
        if not model_path.exists():
            self.log_message("No model found to validate. Generate a model first.")
            return
        
        # Validate model name
        model_name = "TrafficLightFSM"
        valid_name, name_errors = MatlabModelValidator.validate_model_name(model_name)
        
        if valid_name:
            self.log_message(f"✓ Model '{model_name}' validation passed")
        else:
            self.log_message(f"✗ Model name validation failed: {'; '.join(name_errors)}")
        
        # Try to load the model for validation
        config = self.get_simulation_config()
        success = self.simulation_manager.load_model(str(model_path), config)
        
        if success:
            self.log_message("✓ Model loaded successfully for validation")
        else:
            self.log_message("✗ Failed to load model for validation")
    
    def generate_code(self):
        """Generate code from the current model"""
        model_path = Path.cwd() / "generated_models" / "TrafficLightFSM.slx"
        
        if not model_path.exists():
            self.log_message("No model found for code generation. Generate a model first.")
            return
        
        self.log_message("Starting code generation...")
        
        # Configure code generation
        config = CodeGenConfig(
            language="C++",
            target_file="ert.tlc",
            optimization_level="O2",
            generate_makefile=True,
            include_comments=True,
            custom_defines={"FSM_VERSION": "1.0", "DEBUG_MODE": "0"}
        )
        
        output_dir = str(Path.cwd() / "generated_code")
        os.makedirs(output_dir, exist_ok=True)
        
        self.matlab_connection.generate_code(str(model_path), config, output_dir)
    
    def start_simulation(self):
        """Start the simulation"""
        model_path = Path.cwd() / "generated_models" / "TrafficLightFSM.slx"
        
        if not model_path.exists():
            self.log_message("No model found for simulation. Generate a model first.")
            return
        
        self.log_message("Starting simulation...")
        
        # Get configuration from UI
        config = self.get_simulation_config()
        
        # Load and start simulation
        if self.simulation_manager.load_model(str(model_path), config):
            # Wait a moment for model to load, then start
            QTimer.singleShot(1000, self.simulation_manager.start_simulation)
        else:
            self.log_message("Failed to load model for simulation")
    
    def pause_simulation(self):
        """Pause the simulation"""
        self.simulation_manager.pause_simulation()
    
    def resume_simulation(self):
        """Resume the simulation"""
        self.simulation_manager.resume_simulation()
    
    def stop_simulation(self):
        """Stop the simulation"""
        self.simulation_manager.stop_simulation()
    
    def run_diagnostics(self):
        """Run MATLAB diagnostics"""
        self.log_message("Running MATLAB diagnostics...")
        
        # Generate diagnostic report
        report = MatlabDiagnostics.generate_diagnostic_report()
        self.log_message("=== DIAGNOSTIC REPORT ===")
        for line in report.split('\n'):
            self.log_message(line)
        self.log_message("=== END REPORT ===")
        
        # Get engine info if available
        if self.matlab_connection and self.matlab_connection.is_connected():
            engine_info = self.matlab_connection.get_engine_info()
            if engine_info:
                self.log_message(f"Engine Info: {engine_info}")
    
    def export_data(self):
        """Export simulation data to CSV"""
        if not self.data_logger or not self.data_logger.data_history:
            self.log_message("No simulation data to export")
            return
        
        try:
            output_file = Path.cwd() / "simulation_data.csv"
            self.data_logger.export_to_csv(str(output_file))
            self.log_message(f"Data exported to: {output_file}")
        except Exception as e:
            self.log_message(f"Export failed: {e}")
    
    def update_performance_metrics(self):
        """Update performance metrics display"""
        if self.simulation_manager and self.simulation_manager.is_simulation_active():
            metrics = self.performance_monitor.get_metrics()
            
            if metrics:
                perf_text = f"Performance: {metrics.get('data_rate', 0):.1f} pts/s"
                if 'avg_memory_mb' in metrics:
                    perf_text += f", Mem: {metrics['avg_memory_mb']:.1f}MB"
                if 'avg_cpu_percent' in metrics:
                    perf_text += f", CPU: {metrics['avg_cpu_percent']:.1f}%"
                
                self.performance_label.setText(perf_text)
    
    def log_message(self, message):
        """Log a message to the output text area"""
        timestamp = QTimer().singleShot.__globals__['time'].strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.output_text.append(formatted_message)
        logger.info(message)
    
    def closeEvent(self, event):
        """Handle application close"""
        self.log_message("Shutting down MATLAB integration...")
        
        if self.simulation_manager:
            self.simulation_manager.shutdown()
        
        if self.matlab_connection:
            self.matlab_connection.shutdown()
        
        event.accept()


def main():
    """Main function to run the demo application"""
    app = QApplication(sys.argv)
    
    # Create and show the demo window
    demo = MatlabIntegrationDemo()
    demo.show()
    
    # Run the application
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())


# Additional utility functions for integration testing

def test_matlab_integration():
    """Standalone function to test MATLAB integration without GUI"""
    
    print("Testing MATLAB Integration...")
    print("=" * 50)
    
    # Test diagnostics
    print("\n1. Running diagnostics...")
    report = MatlabDiagnostics.generate_diagnostic_report()
    print(report)
    
    # Test model validation
    print("\n2. Testing model validation...")
    
    # Sample states and transitions
    test_states = [
        {'name': 'State1', 'x': 100, 'y': 100, 'is_initial': True},
        {'name': 'State2', 'x': 200, 'y': 100}
    ]
    
    test_transitions = [
        {'source': 'State1', 'target': 'State2', 'event': 'trigger'}
    ]
    
    valid_states, state_errors = MatlabModelValidator.validate_states(test_states)
    valid_transitions, trans_errors = MatlabModelValidator.validate_transitions(test_transitions, test_states)
    
    print(f"States valid: {valid_states}")
    if state_errors:
        print(f"State errors: {state_errors}")
    
    print(f"Transitions valid: {valid_transitions}")
    if trans_errors:
        print(f"Transition errors: {trans_errors}")
    
    # Test model name validation
    print("\n3. Testing model name validation...")
    test_names = ["ValidModel", "123Invalid", "Model_With_Underscores", "sin", ""]
    
    for name in test_names:
        valid, errors = MatlabModelValidator.validate_model_name(name)
        print(f"'{name}': {'✓' if valid else '✗'}")
        if errors:
            print(f"  Errors: {errors}")
    
    print("\n4. Testing configuration objects...")
    
    # Test simulation config
    sim_config = create_default_simulation_config()
    print(f"Default simulation config: {sim_config}")
    
    # Test code generation config
    code_config = CodeGenConfig(
        language="C++",
        custom_defines={"VERSION": "1.0", "DEBUG": "1"}
    )
    print(f"Code generation config: {code_config}")
    
    print("\nIntegration test completed!")


def create_minimal_fsm_example():
    """Create a minimal FSM example for testing"""
    
    states = [
        {
            'name': 'Idle',
            'x': 100, 'y': 100, 'width': 100, 'height': 50,
            'is_initial': True,
            'entry_action': 'status = "idle"'
        },
        {
            'name': 'Active',
            'x': 300, 'y': 100, 'width': 100, 'height': 50,
            'entry_action': 'status = "active"',
            'during_action': 'counter = counter + 1'
        }
    ]
    
    transitions = [
        {
            'source': 'Idle',
            'target': 'Active',
            'event': 'start',
            'condition': 'enable == 1',
            'action': 'counter = 0'
        },
        {
            'source': 'Active',
            'target': 'Idle',
            'event': 'stop',
            'condition': 'counter >= 10',
            'action': 'counter = 0'
        }
    ]
    
    return states, transitions


def benchmark_simulation_performance():
    """Benchmark simulation performance with different configurations"""
    
    print("Benchmarking MATLAB simulation performance...")
    
    configs = [
        SimulationConfig(stop_time=5.0, step_size=0.1, solver='ode1'),
        SimulationConfig(stop_time=5.0, step_size=0.01, solver='ode1'),
        SimulationConfig(stop_time=5.0, step_size=0.1, solver='ode45'),
        SimulationConfig(stop_time=10.0, step_size=0.1, solver='ode1'),
    ]
    
    for i, config in enumerate(configs):
        print(f"\nConfiguration {i+1}:")
        print(f"  Stop time: {config.stop_time}s")
        print(f"  Step size: {config.step_size}s")
        print(f"  Solver: {config.solver}")
        
        # This would require actual MATLAB integration to run
        # For now, just print the configuration
        params = config.to_matlab_params()
        print(f"  MATLAB params: {params}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_matlab_integration()
    elif len(sys.argv) > 1 and sys.argv[1] == "--benchmark":
        benchmark_simulation_performance()
    else:
        main()