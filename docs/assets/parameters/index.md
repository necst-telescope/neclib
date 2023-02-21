# NECST Parameters

| Parameter Name | TOML type | Parsed type in Python | Description |
| --- | --- | --- | --- |
| `observatory` | `String` | `str` | Name of the observatory or telescope |
| `location` | `Inline-table{ lon = String, lat = String, height = String }` | `EarthLocation` | Location of the telescope |
| `simulator` | `Boolean` | `bool` | If `true`, the system won't make any attempt to communicate with devices |
| `record_root` | `String` | `Path` | Path in which all records are saved |
| `alert_interval_sec` | `Float` | `float` | Interval at which alert messages are published |
| `antenna_pid_param_az` | `Array[Float, Float, Float]` | `list[float]` | Constant parameters for PID controller, for Az. axis control |
| `antenna_pid_param_el` | `Array[Float, Float, Float]` | `list[float]` | Constant parameters for PID controller, for El. axis control |
| `antenna_drive_range_az` | `Array[String, String]` | `ValueRange[Quantity]` | Hardware limit of Az. axis drive range |
| `antenna_drive_range_el` | `Array[String, String]` | `ValueRange[Quantity]` | Hardware limit of El. axis drive range |
| `antenna_drive_warning_limit_az` | `Array[String, String]` | `ValueRange[Quantity]` | Preferred drive range for Az. axis |
| `antenna_drive_warning_limit_el` | `Array[String, String]` | `ValueRange[Quantity]` | Preferred drive range for El. axis |
| `antenna_drive_critical_limit_az` | `Array[String, String]` | `ValueRange[Quantity]` | Software limit of Az. axis drive range |
| `antenna_drive_critical_limit_el` | `Array[String, String]` | `ValueRange[Quantity]` | Software limit of El. axis drive range |
| `antenna_pointing_accuracy` | `String` | `Quantity` | Threshold of drive convergence |
| `antenna_pointing_parameter_path` | `String` | `Path` | Path to pointing error parameter file |
| `antenna_max_acceleration_az` | `String` | `Quantity` | Maximum allowed acceleration of antenna drive, for Az. axis |
| `antenna_max_acceleration_el` | `String` | `Quantity` | Maximum allowed acceleration of antenna drive, for El. axis |
| `antenna_max_speed_az` | `String` | `Quantity` | Maximum allowed speed of antenna drive, for Az. axis |
| `antenna_max_speed_el` | `String` | `Quantity` | Maximum allowed speed of antenna drive, for El. axis |
| `antenna_command_frequency` | `Integer` | `int` | Frequency of speed command to the motor for antenna drive |
| `antenna_command_offset_sec` | `Float` | `float` | Time margin for coordinate conversion |
| `ros_service_timeout_sec` | `Float` | `float` | Maximum time duration ROS service client waits for its server |
| `ros_communication_deadline_sec` | `Float` | `float` | ROS communications staler than this duration won't be subscribed |
| `ros_logging_interval_sec` | `Float` | `float` | ROS logger throttles the output when it's too verbose |
| `ros_topic_scan_interval_sec` | `Float` | `float` | ROS topic scanning interval, for nodes which constantly check all existing topics |

<!-- antenna_speed_to_pulse_factor_az, el -->
