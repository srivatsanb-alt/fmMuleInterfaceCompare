# Fleet Manager ↔ Mule Detailed Interface Dependencies

This report provides detailed analysis of interface dependencies:
- Mule's public API (exported functions/classes)
- Fleet Manager's usage of Mule interfaces
- Function signatures and call chains

## Mule Submodule Public API

### Exported Functions

**ati/common/config.py**

- `def add_keyval(d, key, val)`
- `def load_mule_config(config_file)`
- `def load_mule_config_orig(config_file)`
- `def regenerate_config(mule_root, subdir)`
- `def reload_mule_config(config_file)`

**ati/common/router_localbuild/test/publisher.py**

- `def main()`

**ati/common/router_localbuild/test/simple_test.py**

- `def main()`
- `def publisher_thread()`
- `def subscriber_thread()`

**ati/common/router_localbuild/test/subscriber.py**

- `def main()`

**ati/common/vehicle.py**

- `def check_distance(d, radius)`
- `def get_bezier_indices(s_arr, samples)`
- `def get_c_shape_points(center, length, width, length_padding, width_padding)`
- `def get_hitch_bitmap(grid, mule_pose, mule_inner_dims, hitch_dims, hitch_length, hitch_offset_from_rear)`
- `def get_hitch_mount(mule_pose, mule_inner_dims, hitch_offset_from_rear)`
- `def get_mule_box(config, from_lidar, use_inner, xpad, ypad)`
- `def get_mule_dimensions(config, xpad)`
- `def get_payload_bitmap(grid, payload_pose, payload_length, payload_width, payload_padding_crop)`
- `def get_payload_dims(payload_length, payload_width, payload_padding_crop)`
- `def get_platform_bitmap(grid, platform_pose, platform_length, platform_width, platform_side_padding, platform_length_padding)`
- `def get_square_mask(ob, x, y, yaw, center_offset, l, b, rhs)`
- `def get_strut_config(config)`
- `def load_config()`
- `def mule_box_bitmap(grid, pose, mule_dims)`
- `def mule_box_pose(x, y, t, mule_dims)`
- `def square_check(x, y, yaw, ob, center_offset, l, b, rhs)`
- `def swept_path(s, e, mule_dims)`
- `def swept_path_bitmap(grid, path1, mule_dims, path2, trolley_dims)`
- `def swept_path_trolley(s1, e1, trolley_dims)`
- `def trolley_box_bitmap(grid, trolley_pose, trolley_dims)`
- `def trolley_box_pose(x, y, t, trolley_dims)`
- `def zone_path_bitmap(grid, zone_coords)`

**ati/control/actuator/actuator_utils.py**

- `def _find_turn_indicator(turn_id, forward, paused)`
- `def _obstacle_warning(speed_factor, obstacle_speed_factor, last_obstruction_time, visa_factor, safety_exception_indicator, forward, paused)`
- `def _obstacle_warning_inplace(omega, obstacle_speed_factor, last_obstruction_time, safety_exception_indicator, paused)`

**ati/control/bridge/control_module.py**

- `def main(argv)`

**ati/control/bridge/cx/cx_factory.py**

- `def assign_auto_hitch_cx()`
- `def assign_auto_unhitch_trolley_ops_cx()`
- `def assign_follow_me_cx()`
- `def assign_pallet_ops_cx()`
- `def assign_tote_dispatch_cx()`
- `def assign_trolley_ops_cx()`
- `def select_cx(sherpa_application)`

**ati/control/bridge/cx/cx_utils.py**

- `def check_map_files()`
- `def not_a_dispatch_station(cur_pose, station_objects, stations_poses)`
- `def publish_dispatch_msg(sock)`
- `def send_fm_alert_for_dispatch_button(sock)`
- `def send_lights_and_sounds_msgs(sock)`
- `def set_lights_and_sounds_to_defaults(sock)`

**ati/control/bridge/cx/pallet_ops_cx.py**

- `def get_payload_corners(pose, dims)`

**ati/control/bridge/path_state/path_state_utils.py**

- `def _get_action_args(action)`
- `def _get_indicator_bit(speed_bit, theta)`
- `def compute_inplace_angle(cur_pose, station_pose, inplace_direction)`
- `def compute_path_state(route)`
- `def find_greatest_lower_bound(alist, value)`
- `def get_dense_path_generator(segment_type)`
- `def get_lanechange_path(s, u1, t, u2, speed_bit, action_type, smoothness)`
- `def get_regime_props(regime)`
- `def get_segment_path(segment, seg_speed_zone, action_type)`
- `def get_segment_regime_mapping(route)`
- `def get_segment_route_type_mapping(route)`
- `def inplace_path(x, y, start_theta, dtheta, speed_zone, action_type)`
- `def is_parked_precisely(cte, te)`
- `def lanechange_path(s, u1, t, u2, speed_bit, action_type)`
- `def max_curvature_check(dense_path, max_curvature)`
- `def park_bezier_path(s, u1, t, u2, speed_bit, action_type)`
- `def process_for_inplace_theta(dense_path_list, action_modes)`
- `def read_from_db(db, entry, default)`
- `def straight_path(s, t, speed_bit, action_type)`
- `def turn_path(s, u1, t, u2, speed_bit, action_type)`
- `def unpark_bezier_path(s, u1, t, u2, speed_bit, action_type)`

**ati/control/bridge/router_planner_interface.py**

- `def _get_gmaj_meta_checksum(gmaj_path)`
- `def create_json_file(wpsj_path, gmaj_path)`
- `def get_hitch_station_attribute(station)`
- `def get_station_lane_attrribute(station, lane_type)`
- `def get_unpark_merge_attribute(station)`
- `def maybe_update_gmaj(gmaj_path, wpsj_path, VERIFY_WPSJ_CHECKSUM)`
- `def process_dict(terminal_lines)`
- `def process_stations_info(stations)`

**ati/control/dynamic_router/auto_hitch_park_solver.py**

- `def _compute_axial_parking_route_merge(station_pose, station_node_pose, station_direction, path_approach_direction, station_lane)`
- `def _get_all_axial_parking_routes(station_pose, station_node_pose, station_direction, hitch_station, station_lane)`
- `def _get_all_axial_unparking_routes(station_direction, station_pose, station_node_pose, station_lane)`
- `def _park_axial_lanechange_hitch(station_pose, station_node_pose, station_direction, path_approach_direction)`
- `def _park_axial_lanechange_merge(station_pose, station_node_pose, station_direction, path_approach_direction)`
- `def _park_axial_uturn_merge(station_pose, station_node_pose, station_direction, path_approach_direction)`
- `def _unpark_axial_lanechange(station_pose, station_node_pose, station_direction, path_departure_direction)`
- `def _unpark_axial_uturn(station_pose, station_node_pose, station_direction, path_departure_direction)`

**ati/control/dynamic_router/axial_cross_park_solver.py**

- `def _compute_axial_parking_route(station_pose, station_node_pose, station_direction, path_approach_direction)`
- `def _compute_axial_unparking_route(station_pose, station_node_pose, station_direction, path_departure_direction, unpark_merge)`
- `def _get_all_axial_parking_routes(station_pose, station_node_pose, station_direction)`
- `def _get_all_axial_unparking_routes(station_direction, station_pose, station_node_pose, unpark_merge)`
- `def _get_all_cross_parking_routes(station_pose, station_node_pose, station_direction)`
- `def _get_all_cross_unparking_routes(station_direction, station_pose, station_node_pose)`
- `def _get_axial_station_paths_directions(station_direction)`
- `def _get_cross_station_paths_directions(station_direction)`
- `def _park_axial_lanechange(station_pose, station_node_pose, station_direction, path_approach_direction)`
- `def _park_axial_uturn(station_pose, station_node_pose, station_direction, path_approach_direction)`
- `def _park_cross_turn(station_pose, station_node_pose, station_direction, path_approach_direction)`
- `def _unpark_axial_lanechange(station_pose, station_node_pose, station_direction, path_departure_direction, unpark_merge)`
- `def _unpark_axial_lanechange_fwd(station_pose, station_node_pose, station_direction, path_departure_direction)`
- `def _unpark_axial_uturn(station_pose, station_node_pose, station_direction, path_departure_direction)`
- `def _unpark_cross_turn(station_pose, station_node_pose, station_direction, path_departure_direction)`

**ati/control/dynamic_router/dropr.py**

- `def _adjust_turn_radius(line1, line2)`
- `def _clear_circuitous_paths(wps)`
- `def _get_init_angle(path, path_direction, end_of_route)`
- `def _get_turn_speed_index(u1, u2, p1, p2)`
- `def _give_straight(path, i)`
- `def _give_turn(path, i)`
- `def _make_core_route_from_djpath(dj_path)`
- `def _rationalize_aptap_route(init_wps)`
- `def _remove_consecutive_repeat_pts(wps, tolerance)`
- `def _simple_inplace(path, path_direction, input_angle, end_of_route)`
- `def check_aptap_terminal_points(dj_wps, start_pose, end_pose, start_pose_station, end_pose_station)`
- `def collapse_collinear(wps)`
- `def compute_path_direction(mule_theta, path_wps)`
- `def debug_log(log_text)`
- `def find_mod_radius(p1, p2, p3)`
- `def find_turn_points(p1, p2, p3, trip_state)`
- `def generate_flex_radius_path(wps)`
- `def make_aptap_route_from_dj_path(dj_path, start_pose, end_pose)`
- `def make_aptap_route_from_dj_path_trolley_ops(dj_path, start_pose, end_pose)`
- `def normalize_angle(angle)`
- `def rationalize_first_segment(wps)`

**ati/control/dynamic_router/graph_builder_utils.py**

- `def _closest_edge_to_station(station_obj, cand_edges)`
- `def _find_angle(pt1, pt2)`
- `def _get_edges_dict(G)`
- `def _get_meta_data(graph_object_path)`
- `def _get_name(pose)`
- `def _get_nodes_dict(G)`
- `def _get_oriented_edges(cand_edges, station_obj)`
- `def _get_station_node_pose(station, closest_edge)`
- `def _get_stations_obj_dict(station_objs)`
- `def _is_across_axis(station_vector, cand_line)`
- `def _is_along_axis(station_vector, cand_line)`
- `def _is_culdesac(G, cand_edge)`
- `def _process_node_data(node_dict)`
- `def add_culdesacs(G)`
- `def add_nodes_and_edges(G, line)`
- `def add_station_node(G, station_node_pose, station_obj)`
- `def build_basic_grid_graph(G, kernel_lines)`
- `def build_graph_from_graph_object(graph_info)`
- `def converting_edge_attributes(graph_info)`
- `def converting_node_attributes(graph_info)`
- `def dump_graph_object(G, gmaj_checksum, dynamic_router_release, json_path)`
- `def find_duplicate_node(G, new_node)`
- `def find_edge_for_node(station_node_pose, lane, cand_lanes)`
- `def get_all_stations_info(G)`
- `def get_grid_kernel_lines(terminal_pts_kernel_lines)`
- `def get_relevant_lane(pose, cand_lanes, is_start_node)`
- `def import_graph_object_json(fleet)`
- `def maybe_build_graph_object_json(terminal_lines_int, stations_objects, dynamic_router_release, gmaj_path, graph_object_path)`
- `def update_edges(G, closest_edge, station_node, culdesac)`
- `def update_graph_with_stations(G, stations, kernel_lines)`

**ati/control/dynamic_router/grid_map_utils.py**

- `def add_camera_zone(zone, c1, l, b, name, feature_type)`
- `def add_ez_gate(new_ez_gate, ez_gates_list)`
- `def add_line(l, line_id, t1, t2, is_edge_line, name, bidirectional)`
- `def add_low_speed_zone(zone, c1, l, b, velocity_factor, name)`
- `def add_obstacle_avoidance_zone(zone, c1, l, b, max_offset, name)`
- `def add_ramp_zone(zone, c1, l, b, name, upslope_gradient)`
- `def add_station(stations, pose, tag, orientation, name, is_transit_allowed, unpark_merge, lidar_pose)`
- `def add_traffic_intersection_zone(zone, c1, l, b, name)`
- `def add_zone(zone_dict, zone_type)`
- `def adjust_stations_for_reverse_parking(stations)`
- `def angle(z)`
- `def correct_line(ref_wall_line, path, i)`
- `def debug_log(message)`
- `def delete_line(line_id, l)`
- `def delete_station(name, stations)`
- `def det(z1, z2)`
- `def disp_lanes(l, style, init_lanes)`
- `def disp_map(mapdir, xlim, ylim, title, figsize, nposes)`
- `def edit_station_pose(name, new_pose, stations, is_lidar_pose)`
- `def get_zone_coords(c1, l, b)`
- `def initialize_editor(json_path, thresh)`
- `def invert_station_pose_front_axle_to_rear_axle(pose)`
- `def length(z)`
- `def mid_point(p1, p2)`
- `def plot_arrow(p1, p2)`
- `def plot_grid_map(l, stations, map_dir, xlim, ylim, init_lanes, lsz_path)`
- `def process_stations_info(stations)`
- `def rotate(p, q, theta)`
- `def sanitize_lanes(l, thresh)`
- `def show_zones(zone_name, zones)`
- `def simul(z1, z2, b)`
- `def stations_info(stations_dict)`
- `def transform_pose_lidar_to_axle(pose)`
- `def trim_all_lanes(l)`
- `def update_ez_json_file(ez_gates_list, json_path)`
- `def update_gmaj_file(l, stations, file_path)`
- `def update_path(path, i, axis)`
- `def update_turn(path, i, r)`

**ati/control/dynamic_router/grid_route_library.py**

- `def _add_pre_segment_regimes(pt1_rel_lane)`
- `def _add_segement_regime(action, segment, terminal_lines_dict)`
- `def _check_for_consecutive_pp(route)`
- `def _get_path_without_turns(str_pts)`
- `def _get_routes_terminal_pts(unpark_routes, park_routes)`
- `def _get_segment_dict(index, segment_type, segment_props)`
- `def _get_segment_props(segment)`
- `def _get_special_action_segment(segment_args)`
- `def _get_straight_pts_from_route(route)`
- `def _include_psas(route)`
- `def _process_segment_regimes(formatted_route, terminal_lines_dict)`
- `def _remove_intermediate_pps(route)`
- `def _set_all_attributes(ez_dict)`
- `def _special_straight(p1, p2, segment_feature, route_type, seg_speed_id)`
- `def _special_turn(p1, v1, p2, v2, segment_feature, route_type, seg_speed_id)`
- `def analyse_route(formatted_route)`
- `def calc_segment_dist(segment)`
- `def collapse_modes(in_route)`
- `def disp_map(mapdir, xlim, ylim, title, figsize, nposes)`
- `def find_relevant_lane(pt, terminal_lines_dict)`
- `def format_core_route(core_routes)`
- `def format_inplace(new_route, core_route, sub_route, seg_id, count_del_segs)`
- `def get_dense_path(final_route)`
- `def get_dists_array(path_wps)`
- `def get_formatted_route(final_route, terminal_lines_dict, G, check_psa)`
- `def get_path_wps(route)`
- `def get_path_wps_for_viz(formatted_route)`
- `def get_path_wps_without_turns(route)`
- `def get_raw_route_length(raw_route)`
- `def get_route_cost(route)`
- `def get_segment_args(segment, seg_type)`
- `def get_special_straight_route(speed_id)`
- `def get_special_turn_route(speed_id)`
- `def get_terminal_lines_dict(terminal_lines_info: List) → List`
- `def get_terminal_pts(segment)`
- `def import_ez_gates_from_map_file()`
- `def make_dummy_straight_path(start_pose, end_pose)`
- `def make_straight_path(start_pose, end_pose)`
- `def plot_arrow(p1, p2, head_width, length_includes_head)`
- `def plot_dense_path(final_route, router, map_dir, disp_ez_names, plot_title, new_plot, use_v5wps_graph)`
- `def plot_polygon(polygon)`
- `def plot_route_graph(router, map_dir, disp_ez_names, arrows, title, new_plot)`
- `def plot_route_pts(G, formatted_route, route_seg)`
- `def plot_v5wps_graph(router, map_dir, disp_ez_names, arrows, new_plot)`
- `def stitch_route(unpark_route, core_route, park_route)`

**ati/control/dynamic_router/lifter_park_solver.py**

- `def _compute_axial_parking_route_merge(station_pose, station_node_pose, station_direction, path_approach_direction, station_lane, task)`
- `def _get_all_axial_parking_routes(station_pose, station_node_pose, station_direction, station_lane, task)`
- `def _get_all_axial_unparking_routes(station_direction, station_pose, station_node_pose, station_lane)`
- `def _get_all_cross_parking_routes(station_pose, station_node_pose, station_direction, station_lane, task)`
- `def _get_all_cross_unparking_routes(station_direction, station_pose, station_node_pose, station_lane)`
- `def _get_cross_station_paths_directions(station_direction)`
- `def _park_axial_lanechange(station_pose, station_node_pose, station_direction, path_approach_direction, pre_segment_action)`
- `def _park_axial_uturn_merge(station_pose, station_node_pose, station_direction, path_approach_direction, pre_segment_action, task)`
- `def _park_cross_turn(station_pose, station_node_pose, station_node_pose_direction, station_direction, path_approach_direction, pre_segment_action, task)`
- `def _unpark_axial_lanechange(station_pose, station_node_pose, station_direction, path_departure_direction)`
- `def _unpark_axial_uturn(station_pose, station_node_pose, station_direction, path_departure_direction)`
- `def _unpark_cross_turn(station_pose, station_node_pose, station_direction, path_departure_direction)`
- `def generate_docking_route(cur_pose, table_pose, reattempt)`

**ati/control/dynamic_router/lifter_pm_park_solver.py**

- `def _get_all_axial_parking_routes(station_pose, station_node_pose, station_direction, station_lane, task)`
- `def _get_all_axial_unparking_routes(station_direction, station_pose, station_node_pose, station_lane)`
- `def _get_all_cross_parking_routes(station_pose, station_node_pose, station_direction, station_lane, is_lanechange_required, task)`
- `def _get_all_cross_unparking_routes(station_direction, station_node_pose, start_pose)`
- `def _park_axial_lanechange(station_pose, station_node_pose, station_node_pose_direction, station_direction, path_approach_direction, pre_segment_action, task)`
- `def _park_cross_turn(station_pose, station_node_pose, station_node_pose_direction, station_direction, path_approach_direction, is_lanechange_required, pre_segment_action, task)`
- `def _unpark_axial_lanechange(station_pose, station_node_pose, station_direction, path_departure_direction)`
- `def _unpark_cross_turn(station_node_pose, path_departure_direction, start_pose)`
- `def generate_docking_route(cur_pose, pallet_pose, current_mode, reattempt)`
- `def generate_docking_route_2_stage(cur_pose, pallet_pose, pallet_length, current_mode, cte, te, reattempt)`
- `def is_axial_angle(angle1, angle2, threshold)`
- `def is_cross_angle(angle1, angle2, threshold)`

**ati/control/dynamic_router/map_editor_utils.py**

- `def _getEigenVals(pose_yelli, start, end)`
- `def create_gmaj_from_nodes(x, y)`
- `def det(z1, z2)`
- `def find_lane_endpoints(poses_data, plot_required)`
- `def get_intersection_points(poses_data, xps, yps)`
- `def get_straight_line_points(poses_data, is_plot_required)`
- `def identify_straight_lines(yelli_poses, turn_threshold, is_plot_required)`
- `def plot_lanes_points_of_intersection(xi, yi, xps, yps)`
- `def process_run_data_create_gmaj(ref_data_path, yelli_path, is_plot_required)`
- `def simul(z1, z2, b)`

**ati/control/dynamic_router/pallet_mover_park_solver.py**

- `def _get_all_axial_parking_routes(station_pose, station_node_pose, station_direction, station_lane, task)`
- `def _get_all_axial_unparking_routes(station_direction, station_pose, station_node_pose, station_lane)`
- `def _get_all_cross_parking_routes(station_pose, station_node_pose, station_direction, station_lane, is_lanechange_required, park_bezier_required, station_extra_args, task)`
- `def _get_all_cross_unparking_routes(station_direction, station_node_pose, station_lane, start_pose, is_lanechange_required, inplace_exit, station_extra_args)`
- `def _park_axial_lanechange(station_pose, station_node_pose, station_node_pose_direction, station_direction, path_approach_direction, pre_segment_action, task)`
- `def _park_cross_turn(station_pose, station_node_pose, station_node_pose_direction, station_direction, path_approach_direction, is_lanechange_required, park_bezier_required, station_extra_args, pre_segment_action, task)`
- `def _unpark_axial_lanechange(station_pose, station_node_pose, station_direction, path_departure_direction)`
- `def _unpark_cross_turn(station_node_pose, station_direction, path_departure_direction, start_pose, is_lanechange_required, inplace_exit, station_extra_args)`
- `def generate_docking_route(cur_pose, payload_pose, current_mode, reattempt)`
- `def generate_docking_route_2_stage(cur_pose, payload_pose, payload_length, current_mode, cte, te, reattempt)`
- `def is_axial_angle(angle1, angle2, threshold)`
- `def is_cross_angle(angle1, angle2, threshold)`

**ati/control/dynamic_router/park_solver_v5.py**

- `def _get_all_axial_parking_routes(station_pose, station_node_pose, station_direction, edge_direction, task)`
- `def _get_all_axial_unparking_routes(station_direction, station_pose, station_node_pose, station_lane)`
- `def _get_all_cross_parking_routes(station_pose, station_node_pose, station_direction, edge_direction, is_lanechange_required, park_bezier_required, station_extra_args, task)`
- `def _get_all_cross_unparking_routes(station_direction, station_node_pose, start_pose, is_lanechange_required, inplace_exit, station_extra_args)`
- `def _park_axial_lanechange(station_pose, station_node_pose, station_node_pose_direction, station_direction, path_approach_direction, pre_segment_action, task)`
- `def _park_cross_turn(station_pose, station_node_pose, station_direction, edge_direction, is_lanechange_required, park_bezier_required, station_extra_args, pre_segment_action, task)`
- `def _unpark_axial_lanechange(station_pose, station_node_pose, station_direction, path_departure_direction)`
- `def _unpark_cross_turn(station_node_pose, station_direction, path_departure_direction, start_pose, is_lanechange_required, inplace_exit, station_extra_args)`
- `def generate_docking_route(cur_pose, payload_pose, current_mode, reattempt)`
- `def generate_docking_route_2_stage(cur_pose, payload_pose, payload_length, current_mode, cte, te, reattempt)`
- `def get_final_straight_segment(inplace_start_point, station_pose, station_angle, station_direction, inplace_angle, path_approach_angle)`
- `def is_axial_angle(angle1, angle2, threshold)`
- `def is_cross_angle(angle1, angle2, threshold)`
- `def is_station_towards_lane(station_node_pose, station_pose, station_direction)`

**ati/control/dynamic_router/route_solvers_factory.py**

- `def auto_hitch_park_solver()`
- `def axial_cross_park_solver()`
- `def core_routes_solver()`
- `def get_solver()`
- `def lifter_park_solver()`
- `def pallet_mover_park_solver()`
- `def select_route_solver(routing_application)`
- `def trolley_ops_solver()`
- `def v2_wps_solver()`
- `def v5wps_routes_solver()`

**ati/control/dynamic_router/standalone_router.py**

- `def create_standalone_router(graph_object: Dict[...], mule_config: Dict[...]) → StandaloneRouter`

**ati/control/dynamic_router/v2_routing.py**

- `def calculate_map_waypoints(wps_data)`
- `def collapse_modes(route)`
- `def construct_edges(all_routes)`
- `def edge_cost(path)`
- `def find_route(start, end)`
- `def generate_route(G, waypoints, stations, desired_trip)`
- `def get_route_utils()`
- `def get_shortest_path(G, desired_trip, waypoints)`
- `def get_stations_dict()`
- `def get_waypoints(routes)`
- `def load_gmaj()`
- `def load_map_waypoints()`

**ati/control/dynamic_router/v2_wps_routes_solver.py**

- `def _compute_auto_hitch_pickup_route(start_pose, end_pose, return_pose, auto_hitch_fwd_offset)`
- `def _compute_auto_unhitch_drop_route(start_pose, end_pose)`
- `def _get_stations_names_dict(stations_dict)`
- `def offset_pose_fwd(pose, offset)`

**ati/control/dynamic_router/v5wps_utils.py**

- `def _adjust_turn_radius_v5wps(p1, p2, p3, trip_state)`
- `def _get_pose(pose)`
- `def _give_inplace_v5wps(p1, p2, p3, prev_heading, next_heading)`
- `def _give_straight_v5wps(p1, p2)`
- `def _give_turn_v5wps(p1, p2, p3)`
- `def _make_v5wps_core_route_from_djpath(dj_path, heading_directions)`
- `def build_graph_from_graph_object(graph_info)`
- `def check_aptap_terminal_points_v5wps(dj_wps, start_pose, end_pose, start_pose_station, end_pose_station, heading_directions)`
- `def check_if_collinear(p1, p2, p3)`
- `def check_path_with_turn_radius(dj_path)`
- `def clean_heading_direction(head_directions)`
- `def collapse_collinear_v5wps(wps, heading_directions)`
- `def debug_log(log_text)`
- `def find_turn_points_v5wps(p1, p2, p3, trip_state)`
- `def get_cumulative_dist_from_path_wps(path_wps)`
- `def get_node_object(nodes_info, node_name, edges_info)`
- `def get_nodes_and_edges_list(graph_info)`
- `def get_path_lines_from_path_wps(path_wps)`
- `def get_trip_state(k, n)`
- `def handle_heading_direction_change(prev_point, p1, p2, p3, prev_heading_directions, curr_heading_directions, route, core_route, path_wps)`
- `def import_map_file_as_json(use_map_file, file_name)`
- `def make_aptap_route_from_dj_path_v5wps(dj_path, heading_directions, start_pose, end_pose)`
- `def process_edges(graph_info)`
- `def process_stations(graph_info)`

**ati/control/instrumentation/load_cell.py**

- `def check_tote_load()`
- `def main(argv)`

**ati/control/instrumentation/load_cell_calibration.py**

- `def main(argv)`
- `def write_param_to_config(param, string)`

**ati/control/logger/archive.py**

- `def avoidance_fields()`
- `def lmpc_cost_fields()`
- `def log_setup(name, field_names)`
- `def log_update(data)`
- `def mpc_cost_fields()`
- `def parking_fields()`
- `def precision_parking_fields()`
- `def ps4_fields()`
- `def tracker_fields()`
- `def visa_fields()`

**ati/control/logger/trip_logs.py**

- `def get_status_id(path_state_obj)`
- `def is_parking(path_state_obj)`
- `def is_transit(path_state_obj)`
- `def is_unparking(path_state_obj)`
- `def publish_trip_log_message(sock)`

**ati/control/misc/ez.py**

- `def _add_linked_gates(in_edges, exclusion_zones)`
- `def _calc_gate_dist(zone, line)`
- `def _create_visa_obj(zone_ids, visa_types, eta, zone_names)`
- `def _get_gate_dist(orientation)`
- `def _get_intersection_zones(G, exclusion_zones)`
- `def _get_station_zones(G, exclusion_zones)`
- `def _get_visa_type(is_unparking, is_parking)`
- `def _is_parking(line, zone, line_pos)`
- `def _is_unparking(line, zone, wp_dist)`
- `def add_exclusion_zones(G)`
- `def debug_log(log_text)`
- `def get_all_valid_zones(ezs, path_lines, dists_array)`
- `def get_exclusion_zones_list_dict(exclusion_zones)`
- `def get_visa_object(valid_zones)`
- `def is_intersecting_with_zone(zone, path_line)`
- `def set_gate_passes(recovery: bool, len_visa_obj: int)`
- `def valid_zones_for_line(line, exclusion_zones, wp_dist, line_pos)`

**ati/control/misc/ps4_control.py**

- `def main(argv)`

**ati/control/misc/tote_monitor.py**

- `def get_exception_msg()`
- `def main(argv)`
- `def publish_exception_msg()`
- `def update_history(history, new_reading)`

**ati/control/misc/unhitch_monitor.py**

- `def main(argv)`

**ati/control/planner/bezier.py**

- `def get_dense_path(route)`

**ati/control/planner/bezier_utils.py**

- `def add_points(wx, wy, points)`
- `def binomial(n, i)`
- `def calc_bezier_points(bezier_array, i, control_points, n_control_points, n_pts)`
- `def calc_golden_ratio(u1, u2)`
- `def factorial(i)`
- `def get_bezier_terms(k, n_control_points, n_pts, t)`
- `def get_t(bezier_length)`
- `def get_waypoints(route)`

**ati/control/planner/frenet_utils.py**

- `def convert_frenet_to_cart(x, y, d, yaw, bezier_indices)`
- `def convert_to_bytes(path_list)`
- `def get_additional_params(x, y)`
- `def get_bezier_index(s, resolution_factor)`
- `def get_cross_prod(td, d_yaw, pose)`
- `def get_entity_mask(ob_global, entity_path, entity_length, entity_width)`
- `def get_trolley_coordinates(path, trolley)`
- `def publish_candidates_msg(path_list, frame_id)`
- `def publish_planner_msg(path, frame_id, path_cost)`
- `def put_asymmetric_padding(path, is_mule_term_on_ref, width, mule_path)`
- `def ref_mule_check(path, ob_global, l, b, mule_mask, rhs)`
- `def sq_check_collision(path, t_fp, ob_global)`

**ati/control/planner/full_trajectory.py**

- `def bezier_curve(p0, p1, p2, p3, t)`
- `def calculate_ramp_dist(vstart, vend)`
- `def check_invalid_v(v_min, v_max)`
- `def convert_to_numpy(path)`
- `def generate_bezier_trajectory(x_init, y_init, theta_init, x_final, y_final, theta_final, smoothness, num_points)`
- `def generate_traj_no_ramp_down(traj_info)`
- `def generate_trajectory(ref_path, mode, curr_v)`
- `def get_ramped_velocity_profile(traj_info)`
- `def get_v_max_and_seg(traj_info, ramp_dist)`
- `def inplace(t)`
- `def lanechange(s, u1, t, u2, smoothness, n)`
- `def new_inplace(x, y, start_theta, dtheta)`
- `def normalize(theta1)`
- `def parse(route)`
- `def post_process(t)`
- `def recalculate_velocities_dt(ramp_up_dist, ramp_down_dist, vmax, short_seg, traj_info)`
- `def regenerate_traj(traj_info)`
- `def set_trajectory_info(ref_path, vstart, policy)`
- `def straight(s, t)`
- `def turn(s, u1, t, u2, n)`
- `def turn_theta(alpha, beta, s, t, n)`
- `def turn_theta_lane(alpha, n, offset, offset_sign)`

**ati/control/planner/trajectory.py**

- `def convert_to_numpy(path)`
- `def inplace(t)`
- `def lanechange(s, u, t, n)`
- `def new_inplace(x, y, start_theta, dtheta)`
- `def normalize(theta1)`
- `def parse(route)`
- `def post_process(t)`
- `def straight(s, t)`
- `def turn(s, u1, t, u2, n)`
- `def turn_theta(alpha, beta, s, t, n)`
- `def turn_theta_lane(alpha, n, offset, offset_sign)`

**ati/control/regimes/regime_factory.py**

- `def select_regime(regime_name) → RegimeFactory`

**ati/control/regimes/regimes.py**

- `def switch_slam_topic(path_state, current_feature_slam_topic)`

**ati/control/safety/imu_divergence.py**

- `def main(argv)`
- `def publish_exception(pub_sock, exception_string)`

**ati/control/safety/polygon_policy.py**

- `def get_confidence_score(d_grid, path_mask)`
- `def load_cell_overload(_sock)`
- `def local_obst_distance(obst_local)`
- `def log_policy_message(sock)`
- `def log_stoppage_message(sock)`
- `def publish_camera_zone(sock, zone, entering_zone)`
- `def publish_ramp_transition(sock, gradient)`

**ati/control/safety/runaway_monitor.py**

- `def check_data_latency(data_gath)`
- `def get_monitors(monitors_list, runaway_config, vehicle_config, data_gath, batch_event_left, batch_event_right, batch_event_steer)`
- `def get_valid_monitors(runaway_config, vehicle_config, vehicle_type)`
- `def main(argv)`

**ati/control/safety/runaway_utils.py**

- `def _get_exception_msg_gen(score, sensor_id_pub, ex_msg, exception_flag)`
- `def _publish_buffer(SOCK, sock_message)`
- `def _publish_exception_msg(SOCK, excp_msg)`
- `def _publish_good_msg(SOCK, good_msg)`

**ati/control/scripts/open_loop.py**

- `def main(argv)`

**ati/control/scripts/open_loop_actuator_test.py**

- `def main(argv)`

**ati/control/scripts/open_loop_lifter_test.py**

- `def main(argv)`

**ati/control/scripts/open_loop_steering.py**

- `def main(argv)`

**ati/control/scripts/open_loop_utils.py**

- `def _get_drive_msg(ref_steer)`

**ati/control/sockets/sockets.py**

- `def _f()`
- `def get_async_bus()`
- `def get_drivable_stub()`
- `def get_encoder_stub()`
- `def get_exception_stub()`
- `def get_lifter_sensor_stub()`
- `def get_pause_stub()`
- `def get_payload_pose_stub()`
- `def get_pub_sock()`
- `def get_route_type_stub()`
- `def singleton(f)`

**ati/control/test_scripts/check_map_routes.py**

- `def dfs(graph, start, end, path)`
- `def find_station_ids(st_objs, station_name)`

**ati/control/test_scripts/communicator_unit_test/msg_publisher.py**

- `def gen_tracker_state()`
- `def gen_yelli_msg(pose)`

**ati/control/test_scripts/fleet_manager.py**

- `def fleet(dest, dest_pose, reset, complete_reset)`
- `def get_orchestrator()`
- `def get_station_pose_from_grid_map(stations, id)`

**ati/control/tracker_library/drive_inplace.py**

- `def normalize(theta1)`

**ati/control/tracker_library/lmpc_tracker.py**

- `def block_diagonal_matrix(Q, N)`
- `def find_time_index(arr, idx, threshold)`
- `def get_model_matrices(pose, control, mpc_frequency, deltat)`
- `def interleave_arrays(arr1, arr2)`
- `def normalize(theta)`

**ati/control/tracker_library/mpc_tracker.py**

- `def cost_function(weights, v0, k0, path, v_t, dt, state)`
- `def cost_function_gradient(weights, v0, k0, path, v_t, dt, state)`
- `def evaluate_cost(weights, v0, k0, path, v_t, dt, state)`

**ati/control/tracker_library/mpc_tracker_module.py**

- `def get_tracker_logs(mpc_context, mpc_logs, processing_time, planner_time, global_cte)`

**ati/control/tracker_library/regulator.py**

- `def _angle_correction(zref, zref_next)`
- `def _calc_cte(pose_xy, zref, zref_next)`
- `def calculate_velocity(alpha)`
- `def clip(x, x_min, x_max)`
- `def closest_pt(ref, pose_xy)`
- `def coords(xref, yref, i)`
- `def find_distances(turn, i, P_index)`
- `def limit_velocity(v, w, prev_v, prev_w, velocity_limits, distances)`
- `def slow_down(d, v1, v2)`
- `def tracker_command(ref_pose, ref_pose_next, current_pose, distances, curr_vmax)`
- `def tracker_control()`

**ati/control/tracker_library/regulator_numba.py**

- `def _angle_correction(zref, zref_next)`
- `def _calc_cte(pose_xy, zref, zref_next)`
- `def calculate_velocity(alpha)`
- `def clip(x, x_min, x_max)`
- `def closest_pt(ref, pose_xy)`
- `def coords(xref, yref, i)`
- `def find_distances(turn, i, P_index)`
- `def get_tan_tracker_config_params()`
- `def limit_velocity(v, w, prev_v, prev_w, velocity_limits, distances)`
- `def slow_down(d, v1, v2)`
- `def tracker_command(ref_pose, ref_pose_next, current_pose, prev_v, prev_w, old_cte, distances, curr_vmax)`

**ati/control/trip_status/trip_status_factory.py**

- `def auto_hitch_trip_status()`
- `def select_trip_status(sherpa_application)`
- `def tote_dispatch_trip_status()`

**ati/diagnostics.py**

- `def _check_for_error(temp_dir, error, diag, thresh)`
- `def certify_error()`
- `def characterize_error(temp_dir)`
- `def check_clean_shutdown()`
- `def current_working_dir()`
- `def find_auto_run_folder()`

**ati/drivers/battery_data_pallet_mover.py**

- `def get_currents(msg, send_sock)`
- `def main()`
- `def predict_soc(voltage)`

**ati/drivers/can_bus/can_python_drivers/CAN_Parsing.py**

- `def makeByteArray(number, numBytes)`

**ati/drivers/can_bus/can_python_drivers/can_bus_dc.py**

- `def main()`
- `def process_can_data(can_msg: CanReceived, mcu_data_id: int)`
- `def publishLowBatteryMessage(soc, sock)`
- `def publish_battery_msg(soc, sock)`
- `def publish_generic_msg(soc, voltage, sock)`
- `def voltage_to_soc(voltage)`

**ati/drivers/can_bus/can_python_drivers/can_driver_lifting_lifterv2.py**

- `def control_loop(pos_ref, pos_act, lift_signal, LA, error_flag)`
- `def exit_handler(sig, frame)`
- `def main(argv)`
- `def process_can_msg(pub_sock, can_data, pos_ref, pos_act, lift_signal, error_flag)`
- `def process_lift_msg(lift_signal)`
- `def receive_loop(pos_ref, pos_act, lift_signal, LA, error_flag)`
- `def send_get_ready_msg(LA, pub_sock)`

**ati/drivers/can_bus/can_python_drivers/can_driver_lifting_monofork.py**

- `def are_actuators_near_ref(actuator_pos, ref_pos)`
- `def check_position_sync(linear_actuator1, linear_actuator2, pos1, pos2)`
- `def check_time_sync(linear_actuator1, linear_actuator2, last_pos_act1_time, last_pos_act2_time)`
- `def control_loop(pos_ref, pos_act1, pos_act2, lift_signal, linear_actuator1, linear_actuator2, error_flag, is_epo_pressed)`
- `def exit_handler(sig, frame)`
- `def is_close(query, ref)`
- `def main(argv)`
- `def process_can_msg(pub_sock, can_data, pos_ref, pos_act, lift_signal, error_flag)`
- `def process_lift_msg(lift_signal)`
- `def receive_loop(pos_ref, pos_act1, pos_act2, lift_signal, linear_actuator1, linear_actuator2, error_flag, is_epo_pressed)`
- `def send_get_ready_msg(linear_actuator1, linear_actuator2, pub_sock)`

**ati/drivers/can_bus/can_python_drivers/can_hall_sensor.py**

- `def main(argv)`
- `def process_can_data(can_msg: schema.CanReceived, hall_data: HallData, rpm_id: int, direction_id: int, last_rpm_time: float, last_direction_time: float)`
- `def publish_data(sock, hall_data)`

**ati/drivers/can_bus/can_python_drivers/linakactuator.py**

- `def makeByteArray(number, numBytes)`

**ati/drivers/conveyor_driver.py**

- `def run_conveyor(direction, totes, bypass_init_check, timeout)`

**ati/drivers/hall_sensor.py**

- `def main(argv)`
- `def process_data(hall_data, packet)`
- `def publish_data(sock, hall_data)`

**ati/drivers/isaac_sim/isaac_sim_bridge.py**

- `def add_spherical_coordinates(frame)`
- `def check_if_any_thread_has_died(threads)`
- `def comms_between_isaac_sim_and_mule(encoder_connection, control_commands_connection, frame_id, threads)`
- `def creating_and_starting_threads(encoder_tcp_sock, control_commands_tcp_sock, frame_id)`
- `def decode_message(packet)`
- `def encode_sample(sample: str)`
- `def format_livox_packet(frame)`
- `def main(argv)`

**ati/drivers/neopixel_indicators.py**

- `def alert(panels, status, dt, arg)`
- `def dispatch_pause(panels, status, dt, arg)`
- `def emergency(panels, status, dt, arg)`
- `def encode_framebuffer(fb)`
- `def error_state(panels, status, dt, arg)`
- `def free(panels, status, dt, arg)`
- `def inplace(panels, status, dt, arg)`
- `def left(panels, status, dt, arg)`
- `def low_battery(panels, status, dt, arg)`
- `def main()`
- `def manual(panels, status, dt, arg)`
- `def merge_fbs(led_panel)`
- `def move(panels, status, dt, arg)`
- `def move_start(panels, status, dt, arg)`
- `def obstacle(panels, status, dt, arg)`
- `def obstacleHf(panels, status, dt, arg)`
- `def obstacle_safety_exception(panels, status, dt, arg)`
- `def off_state(panels, status, dt, arg)`
- `def pause(panels, status, dt, arg)`
- `def ps4_connected(panels, status, dt, arg)`
- `def reverse(panels, status, dt, arg)`
- `def right(panels, status, dt, arg)`
- `def wait_for_dispatch(panels, status, dt, arg)`
- `def watch_bus()`

**ati/drivers/pallet_mover_powerboard.py**

- `def main()`
- `def predict_soc(voltage)`

**ati/drivers/powerboard.py**

- `def count_current_peaks(data_array, new_value)`
- `def get_tot_current(data)`
- `def main()`
- `def publish_current_data(sock, data)`
- `def publish_powerboard_data(sock, data)`
- `def resync(port, sync_sequence)`

**ati/drivers/powerboard_serial_v4.py**

- `def main()`
- `def predict_soc(voltage)`

**ati/drivers/ps4/ps4_driver.py**

- `def main(argv)`

**ati/drivers/ps5/ps5_driver.py**

- `def _disconnect_cleanup(dualsense, pub_sock, last_state: int) → int`
- `def _publish_indicator(pub_sock, pattern: str)`
- `def _set_state(pub_sock, desired_state: int, last_state: int, controller_id: str) → int`
- `def main(argv)`

**ati/drivers/read_ultrasound.py**

- `def main(sock)`
- `def send_msg(sock, data)`

**ati/drivers/realsense/cam_recorder.py**

- `def cam_gst_recorder()`
- `def copy_file(src, target)`
- `def exit_handler(sig, frame)`
- `def stop_recording()`
- `def wait_for_cam_driver_to_initialise(config)`

**ati/drivers/realsense/realsense_gstreamer_multi.py**

- `def exit_handler(sig, frame)`
- `def main()`
- `def stop_driver()`

**ati/drivers/realsense/realsense_utils.py**

- `def basic_config_checks(config, realsense_devices_info: dict)`
- `def get_realsense_devices()`
- `def get_realsense_devices_info(output_json)`
- `def override_configs_for_camera_calibration(rgbd_driver_configs)`

**ati/drivers/rplidar/rplidar.py**

- `def main()`
- `def parse_scan(packet)`
- `def publish_frames(lidar, publisher, frame_id)`

**ati/drivers/sound/sound_configuration.py**

- `def create_symlink(src, dest)`
- `def update_sound_files()`
- `def update_sound_files_to_respective_lang(lang)`
- `def update_volume()`
- `def write_to_text_file(path, data)`

**ati/drivers/teleops_driver.py**

- `def construct_joystick_message(wheel_controller, velocity, angle)`
- `def generate_path(joystick_y, current_pose, angle_in_radians)`
- `def get_path_with_current_vel_command(pose, command_v, command_w, lookahead_time, dt)`
- `def handle_joystick(wheel_controller, joystick_x, joystick_y, sock, policy, current_pose)`
- `def main(argv)`

**ati/drivers/test_conveyor.py**

- `def main(argv)`

**ati/drivers/test_conveyor_dispatch.py**

- `def main(argv)`

**ati/drivers/test_conveyor_peripherals.py**

- `def main(argv)`

**ati/drivers/test_conveyor_recieve.py**

- `def main(argv)`

**ati/drivers/tpms/tpms_driverv2.py**

- `def detection_callback(device, advertisement_data)`
- `def main()`
- `def parse_manufacturer_data_12(data: bytes) → dict`
- `def publish_message(message)`
- `def raw_packet_to_str(data: bytes) → str`

**ati/drivers/wheel_calibration.py**

- `def compute_controls(report, steering_angle, encoder_debug)`
- `def compute_encoder_offset(encoder_ticks)`
- `def delfino_check(delfino_ps)`
- `def do_calibration()`
- `def encoder_raw_recovery(db)`
- `def main(argv)`
- `def maybe_continue_callibration(db)`
- `def maybe_switch_state_to_off(orc)`
- `def should_i_write()`
- `def update_and_publish_commands(velocity, steering_angle, steer_angle_init, wheel_controller, sock, current_encoder_angle, encoder_debug)`
- `def write_offset_to_config(offset)`
- `def write_total_offset(encoder_debug, old_offset)`

**ati/drivers/xt_dispatch_driver.py**

- `def dispatch_reader(dispatch_value, sock)`
- `def main(argv)`

**ati/examples/debug_log.py**

- `def main(argv)`

**ati/examples/debug_pub.py**

- `def main(argv)`

**ati/examples/images_pub.py**

- `def main(argv)`

**ati/mulectl.py**

- `def _do_i_reset_visa(id: str, pose: list)`
- `def camera(cam, operation)`
- `def cli()`
- `def echo_dictionary(x_dict)`
- `def echo_last_n_lines(file, n)`
- `def errors(n)`
- `def get_config()`
- `def get_orchestrator()`
- `def get_ps4_key_from_redis()`
- `def get_station_pose_from_grid_map(stations, id)`
- `def live_data()`
- `def log_and_echo_msg(msg)`
- `def modify_camera_config(cam_str, operation)`
- `def ps4_key()`
- `def recovery(n, date)`
- `def reload_config()`
- `def reset_all_redis_states(redis_db: redis.client.Redis, pose: list)`
- `def reset_pose(station, fleet_station, init_pose)`
- `def reset_pose_with_input_pose(pose)`
- `def reset_totes()`
- `def reset_visa_redis_state(redis_db: redis.client.Redis, pose: list)`
- `def runs(n)`
- `def set_cam(config_file, cam_str, op, status)`
- `def set_cam_driver(config_file, cam_str, op, status)`
- `def set_perception(config_file, cam_str, op, status)`
- `def set_recording(config_file, cam_str, op, status)`
- `def status()`
- `def stop()`
- `def switch(mode, run_name)`
- `def yelli(front_axle)`

**ati/orchestrator/orchestrator.py**

- `def main()`

**ati/orchestrator/orchestrator_utils.py**

- `def build_info()`
- `def cleanup_orc_csvs()`
- `def create_symlink(src, dest)`
- `def get_folder_name(config, mode, run_name, recorder_folder, start_time_sec)`
- `def get_ip_address()`
- `def get_orc_status()`
- `def get_orchestrator()`
- `def log_event(msg)`
- `def maybe_rewrite_redis_aof(redis_db)`
- `def publish_to_mule_analytics(msg_type: str, msg: dict)`
- `def reset_redis_vars_mode_change(redis_conn)`
- `def send_peripherals_msg(sock, mode)`
- `def symlink(target, link)`
- `def symlink_file(target, link)`

**ati/orchestrator/rpc_utils.py**

- `def serve_orc_on_xml_rpc(orchestrator)`
- `def start_orc_rpc(orchestrator)`

**ati/perception/body_mask.py**

- `def get_ego_pts_mask(frame, body_mask_3d, xlim, ylim, zlim, voxel_res)`
- `def load_body_mask(sensor_str_fq, mask_folder)`
- `def make_body3d_mask(frame, xlim, ylim, zlim, voxel_res)`
- `def save_body_mask(sensor_name, body_mask_3d, xlim, ylim, zlim, voxel_res)`

**ati/perception/calibration/align_with_lidar.py**

- `def align_lidar_with_ekf(dataset_dir, res, lidar_filename)`
- `def align_lidar_with_wheel_traj(dataset_dir, wheel_traj, lidar_filename)`

**ati/perception/calibration/calibrate.py**

- `def calibrate(data_dir, start_frame, end_frame, debug, cam_step, lidar_step, visualize, cam_min_depth, cam_max_depth, max_z_error, n_frames_viz, use_trunc, in_mule, residual_threshold)`
- `def print_calibration(sensor_type, sensor_name, transform)`

**ati/perception/calibration/calibrate_body_mask.py**

- `def create_body_mask(args)`
- `def create_cam_mask(psd, cam_str, vehicle_params, voxel_res)`
- `def create_lidar_mask(psd, vehicle_params, voxel_res)`
- `def delete_old_mule_mask()`

**ati/perception/calibration/calibration_utils.py**

- `def detect_planes(point_cloud, residual_threshold, min_inliers, angle_threshold, max_planes, n_every, debug)`
- `def estimate_yaw(frame_r, debug, prong_length)`
- `def plot_hist(ns, hs, debug)`
- `def post_process_yaw(ys, ns, prong_length, debug)`
- `def print_matrix(R, title)`
- `def rotation_matrix_to_align_with_z(normal)`

**ati/perception/calibration/check_calibration_data.py**

- `def main()`

**ati/perception/calibration/imu_calibrate.py**

- `def main(data_dir: str) → Any`

**ati/perception/calibration/measurement_model.py**

- `def measurement_function(s, model)`
- `def measurement_jacobian(s, model)`

**ati/perception/calibration/old_to_new_config.py**

- `def add_config(section, key, value)`
- `def get_config_changes(consolidated, cam)`
- `def update_config(data_dir, cam)`

**ati/perception/calibration/plot_estimated_steering_and_extrinsics.py**

- `def plot_calibration(csv_path: str)`

**ati/perception/calibration/relative_calibrator_ICP.py**

- `def main(data_dir)`

**ati/perception/calibration/run_vehicle_lidar_and_steering_calibration_online.py**

- `def handle_wheel_packet(packet, ekf, enc_res, wheel_radius, track_width, left_right_state)`
- `def main(argv)`
- `def parse_lidar_packet(packet, replaying)`
- `def publish_state(sock, state_vec, timestamp)`

**ati/perception/calibration/run_vehicle_lidar_steering_calibration.py**

- `def load_and_prepare_events(dataset_dir, params)`
- `def load_vehicle_params_from_toml(dataset_dir)`
- `def log_state(t, s, P)`
- `def propagate_dead_reckoning(v, delta, dt, x, y, th)`
- `def run_calibration_on_dataset(dataset_dir)`
- `def run_event_based_ekf(events, est, lidar_data, wheelbase, init_pose)`

**ati/perception/calibration/run_vehicle_lidar_steering_calibration_main.py**

- `def main()`

**ati/perception/calibration/utils_se2.py**

- `def best_fit_se2(P, Q)`
- `def get_v_w_from_ticks(left_ticks, right_ticks, front_encoder_resolution, front_wheel_radius, track_width)`
- `def interp_traj(df, tq)`
- `def relative_pose_vec(xi, yi, thi, xj, yj, thj)`
- `def se2_from(x, y, th)`
- `def se2_inv(T)`
- `def se2_to_vec(T)`
- `def wrap_angle(a)`

**ati/perception/calibration/visualize_calibration_results.py**

- `def plot_calibration_results(res, wheel_traj, wheel_traj_corr, dataset_dir)`

**ati/perception/calibration/visualize_tracker_data.py**

- `def analyze_tracker_stats(dataset_dir, show_plot)`

**ati/perception/depth_estimation/monocular_depth_on_stoppage.py**

- `def publish_mono_depth_on_cam_stoppage(argv)`

**ati/perception/detection/detection_module.py**

- `def detect_table(model, table_detected)`
- `def main(argv)`

**ati/perception/detection/detection_utils.py**

- `def create_mask(data, roi_x_min, roi_x_max, roi_y_min, roi_y_max, roi_z_max)`
- `def fullview(data, mask, ax, figsize)`
- `def get_centroid(frame, verbose)`
- `def get_cluster_centroid(point_cloud)`
- `def image_to_lidar(x, y, origin, grid_res)`
- `def lidar_to_image(pts, grid_res, padding)`
- `def minBoundingRect(hull_points_2d, max_area)`
- `def sort_points(corners)`
- `def topview(data, zlim, ax, fig, alpha, show, useht, newdata, title, figsize, bbox)`

**ati/perception/detection/model_gym.py**

- `def assign_leg_clustering()`
- `def assign_model_1()`
- `def select_model(ALGO)`

**ati/perception/ekf/augmented_ekf.py**

- `def get_class_params(measurement_type, config)`
- `def get_datasrc(topic_dict)`
- `def get_initial_pose(pose, tf_params)`
- `def get_measurement_models_and_topic_dict(measurement_types, config)`
- `def main()`
- `def publish_generic_state(ekf, sock, fields, update_types)`
- `def publish_state(ekf_state, sock)`

**ati/perception/ekf/ekf_utils.py**

- `def circular_sub(a1, a2)`
- `def convert_wheel_odo_to_yelli(wpose, lidar_y_offset)`
- `def convert_yelli_to_wheel_odo(ypose, lidar_y_offset)`
- `def get_2D_rotation_mat(theta)`
- `def get_closest_positive_semi_definite_mat(mat)`
- `def get_mahalanobis_distance(x, state)`
- `def get_yelli_rotation(theta)`
- `def normalize_pose(theta)`

**ati/perception/ekf/measurement_models.py**

- `def get_measurement_models(config)`
- `def get_yelli_measurement_model(measured_pose, params)`
- `def get_yelli_params(config)`
- `def normalize_covariance(qnb, P)`

**ati/perception/ekf/motion_models.py**

- `def get_process_model(config)`
- `def get_wheel_config(config)`
- `def get_wheel_odo_model(data, params)`
- `def get_wheel_odo_model_debug(data, params)`
- `def process_Jacobian(wr, wl, prev_theta, dT, radius)`
- `def process_noise_covariance(w_sigma, prev_theta, dT, radius, track_width)`
- `def validate_prediction(x, last_updated_x, alt_xvec, deviation_threshold, alt_Q)`
- `def wheel_odo_predict(prev_state, wr, wl, dT, radius, track_width)`

**ati/perception/ekf/msg_processor.py**

- `def get_differential_enc(msg_processor, msg_attrs)`
- `def get_gyro(msg_processor, msg_attr_ids)`
- `def get_msg(msg_processor, msg_attrs)`
- `def is_msgs_new(msg_processor, msg_attrs)`
- `def process_differential_enc_msg(ticks_per_revolution, msg)`
- `def process_gyro_bias_msg(msg, msg_meta)`
- `def process_imu_msg(msg, msg_meta)`
- `def process_msg(msg, msg_meta)`
- `def process_wheel_enc_msg(msg, msg_meta)`

**ati/perception/ekf/sensor_fusion.py**

- `def get_initial_covariance(P_sigma)`
- `def initialize_ekf(initial_pose, initial_covariance)`

**ati/perception/ekf/sensor_readers/sensors.py**

- `def initialize_wheel_enc_debug(callback_method, mtype)`

**ati/perception/ekf/trolley_ekf/trolley_ekf.py**

- `def data_gather_stub()`
- `def main(argv)`

**ati/perception/ekf/v_w_ekf_live.py**

- `def main(argv)`

**ati/perception/ekf/v_w_ekf_live2.py**

- `def main(argv)`

**ati/perception/ekf/v_w_ekf_live2sensor_rejection.py**

- `def main(argv)`

**ati/perception/lidar/lidar_class.py**

- `def adjust(data, transform)`
- `def adjust_carto(carto_data, transform)`
- `def animate(nlidar)`
- `def fix(t)`
- `def get_obstacles(df, show_obstacles, ax, min_samples, usedbscan, debug)`
- `def get_pts_in_rect(data, rectangle, margin)`
- `def makevideo_obstacles(lidar_csv, frames, get_obstacles_for_timestamp, xlim, ylim, camera, fname)`

**ati/perception/lidar/lidar_utils.py**

- `def R(th)`
- `def apply_tilt(frame, roll, pitch, yaw)`
- `def apply_tilt_new(frame, roll, pitch, yaw)`
- `def camera_to_lidar(x, y, c_to_l)`
- `def clear_blindspot(frame, blindspot_angles, nbeams, r)`
- `def cluster_3d(data, useoutliers, tree, threshold_abs, threshold_rel)`
- `def connected_components(graph)`
- `def correct_lidar_for_ego_motion_v_w(frame, v, w, dt)`
- `def correct_tilt(frame, roll, pitch, lidar_ht, use_cuda, tilt_range, tilt_steps, penalty, correct)`
- `def dfs(v)`
- `def exclude_frame_numba(frame, xlim, ylim, zlim)`
- `def find_missing_sectors(frame, N, threshold)`
- `def find_missing_sectors_combined(frame, N, threshold, min_dist)`
- `def find_missing_sectors_new(pts, xmin, ymin, nsectors, threshold, debug)`
- `def find_planes(data, nevery, maxdist, restrict, tolerance, max_height, maxplanes, maxcount, minratio, minpoints, debug)`
- `def fix_reflection_points(frame, H, truncate_to_ground)`
- `def fn_transform_livox_frame(frame)`
- `def get_blindspot_angles(minimule_strut_info)`
- `def get_camera_points(dfx, l_to_c, w, h)`
- `def get_data_for_angle(data, b)`
- `def get_data_for_angle_numba(data, b)`
- `def get_frame(packet, transform)`
- `def get_hitch_pose(lidar_frame, hitch_details, lidar_height, mule_pose, roll, pitch, return_points)`
- `def get_lidar_image(df, xlim, ylim, xstep, ystep)`
- `def get_lidar_transform_merged(config, lidar_type)`
- `def get_lidar_type(config)`
- `def get_limits_based_on_mode(lidar_drivable_config, mode)`
- `def get_relevant_lidar_data(df, zlim, ylim, xlim, normalizeHeight, debug)`
- `def get_rotation_in_quaternion(roll, pitch, yaw)`
- `def get_rotation_matrix(roll, pitch, yaw)`
- `def get_rotation_matrix_numba(roll, pitch, yaw)`
- `def get_transform_fn(config, lidar_id)`
- `def lidar_to_camera(x, y, l_to_c)`
- `def make_frame(packet)`
- `def make_frame_single_beam(frame, inverted)`
- `def make_frame_v1(packet)`
- `def make_frame_v2(packet)`
- `def match_hitch_width(hitch_pts, hitch_details)`
- `def printinfo()`
- `def ransac_remove_floor_gpu(points, k, distance_threshold, height_percentile)`
- `def ransac_remove_roof(points, num_iterations, distance_threshold)`
- `def ransac_remove_roof_gpu(points, k, distance_threshold, height_percentile)`
- `def remove_roof_points(frame, res, z_std_thresh)`
- `def roll_pitch_cupy(frame, roll, pitch, tilt_range, n, penalty, z1, z2, debug)`
- `def roll_pitch_numba(frame, rr, rp, prevroll, prevpitch, penalty, z1, z2)`
- `def rotate(x, y, th, centroid)`
- `def rotate2(xs, ys, th, centroid)`
- `def rotate2_array(xys, th, centroid)`
- `def rotate3(data3, th, centroid)`
- `def rotate_lidar_frame(dfx, debug)`
- `def rotate_lidar_frame_3d(frame, roll, pitch, yaw)`
- `def rotate_point(x, y, theta_rad)`
- `def trim_frame(frame, zlim, ylim, xlim, debug)`
- `def trim_frame_mask(frame, zlim, ylim, xlim, debug)`
- `def trim_frame_mask_numba(frame, xlim, ylim, zlim)`
- `def trim_frame_numba(frame, xlim, ylim, zlim)`
- `def trim_image(depth_img, trim, height, width)`
- `def voxel_filter(pts, voxel)`

**ati/perception/lidar/lidar_utils_plot.py**

- `def draw_3dbbox(rect, ht, ax, l_to_c, vanishing_point, w, h, c1, c2, debug)`
- `def draw_rectangle(x1, x2, y1, y2, c, margin, alpha, ax)`
- `def frontview(data, dlimit, xlim, ylim, usebeam, limits)`
- `def topview(data, xlim, ylim, zlim, ax, fig, alpha, show, useht, newdata, title, figsize, colorbar, s)`

**ati/perception/lidar/lidar_voxel.py**

- `def voxel_centroid_fast(points, voxels)`
- `def voxel_filter(points, voxel_size)`

**ati/perception/lidar/shooting.py**

- `def circular_sub(a1, a2)`
- `def circular_sub_numba(a1, a2)`
- `def fix_shooting_points(frame, x, y, xpad, ypad, radius, threshold)`
- `def fix_shooting_points_alt(frame, x, y, xpad, ypad, hth, dth, min_pts, use_numba)`
- `def fix_shooting_points_spinning_lidar(frame, num_sensors, x, y, xpad, ypad, dth, min_pts)`
- `def get_elimination_inds(frame, num_sensors, dth, min_pts, inds_of_interest)`
- `def get_elimination_inds_from_frame(lfr, hth, dth, min_pts)`
- `def get_elimination_inds_from_frame_numba(lfr, hth, dth, min_pts)`
- `def get_elimination_inds_from_sorted_vbeam(vfr, hth, dth, min_pts)`
- `def get_elimination_inds_from_sorted_vbeam_numba(vfr, hth, dth, min_pts)`
- `def get_elimination_inds_numba(pts, dth, min_pts)`
- `def get_sensor_segs_spinning_lidar(frame, num_sensors, inds_of_interest)`

**ati/perception/lidar_2d/rplidar.py**

- `def process_lidar_2d(distances, horizontal_angles, transform)`

**ati/perception/mlmodels/convert_onnx2trt.py**

- `def main(args)`

**ati/perception/mlmodels/kitti_annotation.py**

- `def create_kitti_label_file(predicted_boxes: BBox3D, file_path: str)`

**ati/perception/mlmodels/onnx_utils.py**

- `def change_input_batch_size(model_path, output_path, num_inputs)`

**ati/perception/mlmodels/tensorrt_utils.py**

- `def allocate_buffers(engine)`
- `def build_simple_trtengine_from_onnx(onnx_model, output_path, fp, batch_size, max_workspace_size)`
- `def do_inference_v2(context, bindings, inputs, outputs, stream)`
- `def get_model_info(engine)`
- `def load_trt_engine(serialised_engine, logger)`

**ati/perception/mlmodels/trt_int8_quantizer.py**

- `def build_int8_model(onnx_model, output_path, calibrator, batch_size, max_workspace_size)`
- `def main(args)`

**ati/perception/mlmodels/utils.py**

- `def check_min_points_in_rotated_box(box, frame, padding, min_points_in_mask)`
- `def get_object_cluster_from_bbox(depth_data, num_clusters, sub_sample, max_dist, max_iter, accuracy)`
- `def rotated_nms_py(boxes, iou_thresh)`

**ati/perception/object_detection/human_detection.py**

- `def get_limits(human_detection_config, vehicle_params)`
- `def get_model_path(human_detection_config)`
- `def is_object_within_limits(bbox, xlim, ylim)`
- `def main(argv)`
- `def trim_pts_inside_mule(lidar_data, body_mask)`

**ati/perception/object_tracking/deep_sort/common.py**

- `def GiB(val)`
- `def _wrapper()`
- `def add_help(description)`
- `def allocate_buffers(engine)`
- `def do_inference(context, bindings, inputs, outputs, stream, batch_size)`
- `def do_inference_v2(context, bindings, inputs, outputs, stream)`
- `def find_sample_data(description, subfolder, find_files, err_msg)`
- `def get_data_path(data_dir)`
- `def locate_files(data_paths, filenames, err_msg)`
- `def retry(n_retries)`
- `def retry_call(func, args, kwargs, n_retries)`
- `def wrapper(func)`

**ati/perception/object_tracking/deep_sort/generate_detections.py**

- `def create_box_encoder(model_filename, input_name, output_name, batch_size)`
- `def encoder(image, boxes)`
- `def extract_image_patch(image, bbox, patch_shape)`
- `def generate_detections(encoder, mot_dir, output_dir, detection_dir)`
- `def main()`
- `def parse_args()`

**ati/perception/object_tracking/deep_sort/iou_matching.py**

- `def iou(bbox, candidates)`
- `def iou_cost(tracks, detections, track_indices, detection_indices)`

**ati/perception/object_tracking/deep_sort/linear_assignment.py**

- `def gate_cost_matrix(kf, cost_matrix, tracks, detections, track_indices, detection_indices, gated_cost, only_position)`
- `def matching_cascade(distance_metric, max_distance, cascade_depth, tracks, detections, track_indices, detection_indices)`
- `def min_cost_matching(distance_metric, max_distance, tracks, detections, track_indices, detection_indices)`

**ati/perception/object_tracking/deep_sort/nn_matching.py**

- `def _cosine_distance(a, b, data_is_normalized)`
- `def _nn_cosine_distance(x, y)`
- `def _nn_euclidean_distance(x, y)`
- `def _pdist(a, b)`

**ati/perception/object_tracking/deep_sort/preprocessing.py**

- `def non_max_suppression(boxes, classes, max_bbox_overlap, scores)`

**ati/perception/object_tracking/follow_me.py**

- `def deepsort_track(frame_bgr, detections, tracker, frame_d)`
- `def exit_handler(sig, frame)`
- `def main(argv)`
- `def print_initialized_and_follow_me_id()`
- `def publish_generic(sock)`
- `def send_msg_to_peripherals(sock, pattern)`
- `def yolov4_trt_deepsort(frame_bgr, frame_id, rgb_ts, frame_d, tracker, score_threshold, iou_threshold, holistic)`

**ati/perception/object_tracking/object_tracking.py**

- `def debug_logger(str, debug)`
- `def exit_handler(sig, frame)`
- `def main(argv)`

**ati/perception/object_tracking/object_tracking_utils.py**

- `def get_obj_pixels_in_bbox(obj_box, k_means_sub_sample, k_means_max_dist, k_means_max_iter, k_means_acc)`
- `def get_xyzr_from_depth(bbox, depth_frame, depth_frame_pc)`
- `def load_class_names(namesfile)`

**ati/perception/object_tracking/thumb_detection.py**

- `def check_thumb_inside(thumb, width, initialize_x_range)`
- `def check_thumpsUp_or_Down(hand_lms, thr1, thr2)`
- `def main(argv)`
- `def thumb_detected(left_thumb, right_thumb, width, initialize_x_range)`

**ati/perception/object_tracking/track_utils.py**

- `def get_obj_pixels_in_bbox(obj_box, k_means_sub_sample, k_means_max_dist, k_means_max_iter, k_means_acc)`

**ati/perception/object_tracking/yolo_with_plugins.py**

- `def _nms_boxes(detections, nms_threshold)`
- `def _postprocess_yolo(trt_outputs, img_w, img_h, conf_th, nms_threshold, input_shape, letter_box)`
- `def _preprocess_yolo(img, input_shape, letter_box)`
- `def allocate_buffers(engine)`
- `def do_inference(context, bindings, inputs, outputs, stream, batch_size)`
- `def do_inference_v2(context, bindings, inputs, outputs, stream)`
- `def get_input_shape(engine)`

**ati/perception/object_tracking/yolov4_utils.py**

- `def bbox_iou(box1, box2, x1y1x2y2)`
- `def get_color(c, x, max_val)`
- `def load_class_names(namesfile)`
- `def nms_cpu(boxes, confs, nms_thresh, min_mode)`
- `def plot_boxes_cv2(img, boxes, savename, class_names, color)`
- `def post_process(img, conf_thresh, nms_thresh, output, class_names, input_w, input_h)`
- `def read_truths(lab_path)`
- `def sigmoid(x)`
- `def softmax(x)`

**ati/perception/obstacle_detection/drivable_region.py**

- `def main(argv)`

**ati/perception/obstacle_detection/drivable_utils.py**

- `def get_img_from_cluster(grid)`
- `def get_img_from_grid(grid)`
- `def get_normalised_cluster(grid)`
- `def get_polygon_edge_points(xs, ys, dist)`

**ati/perception/obstacle_detection/payload_safety.py**

- `def main()`

**ati/perception/offline/pkl_utils.py**

- `def store_as_pkl(psd, lidar_data, cam_datas, folder)`

**ati/perception/payload_detection/payload_detect.py**

- `def main(argv)`

**ati/perception/payload_detection/payload_detect_stub.py**

- `def main(argv)`

**ati/perception/payload_detection/payload_detection_utils.py**

- `def compute_width_and_center(points_xy, mean, principal_dir, yaw_vec, payload_height)`
- `def estimate_payload_angle(points_xy)`
- `def get_detection_model(config, model_path)`
- `def get_payload_config(config)`
- `def get_warmpup_data(config)`
- `def get_yaw_from_rot_mat(R)`
- `def publish_payload_pose(pub_sock, payload_pred)`
- `def publish_payload_pose_stub(pub_sock, front_pose, payload_config)`
- `def should_detect_payload(topic, raw_msg)`

**ati/perception/payload_detection/payload_pose_estimation.py**

- `def get_3d_points_in_extents(xyz, corners)`
- `def get_cuboid_corners(center, rotation, width, length, height)`
- `def is_pallet_pose_valid(lidar_points_world, pallet_front_world, pallet_yaw_world, width, pallet_height, pallet_config, detection_config)`
- `def is_trolley_pose_valid(lidar_points_world, trolley_front_world, trolley_yaw_world, width, trolley_height, trolley_config, detection_config)`

**ati/perception/payload_detection/post_processing.py**

- `def draw_box(image_bgr, keypoints, color, thickness)`
- `def plot_coords(image_bgr, keypoints, keypoint_order, text)`

**ati/perception/payload_detection/publish_debug_hopt.py**

- `def main(args)`

**ati/perception/payload_detection/publish_debug_livox.py**

- `def main(args)`

**ati/perception/rgbd_camera/rgbd_utils.py**

- `def add_markers_to_img(img, uv, color)`
- `def depth_to_point_cloud_numba_internal(depth, depth_table, points, scale, width, height)`
- `def process_mask_numba(uv, bound_mask, binary_mask, temp_mask)`
- `def trim_image(img, trim, height, width)`

**ati/perception/rgbd_camera/stereo_flo_odo.py**

- `def main(argv)`
- `def publish_stereo_vo(sock, T, ts)`

**ati/perception/rgbd_camera/stereo_flo_odo_keyframe.py**

- `def main(argv)`
- `def publish_stereo_vo(sock, T, ts)`

**ati/perception/slip_estimation/slip_estimation.py**

- `def main(argv)`

**ati/perception/slip_estimation/slip_utils.py**

- `def compute_aL(aR, wR, wL, A)`
- `def compute_aR(aL, wR, wL, A)`
- `def get_rads_per_sec(right_motor_velocity, left_motor_velocity, radius_wheel)`
- `def get_skid_ratio(bounds, maximize)`
- `def get_slip_bounds(wL, wR, w, wheel_radius, trackwidth)`
- `def get_v_w(w_r, w_l, wheel_radius, track_width)`
- `def get_w_from_ticks(left_encoder_value, right_encoder_value, vehicle_type, encoder_resolution)`

**ati/perception/slip_estimation/utils.py**

- `def compute_aL(aR, wR, wL, A)`
- `def compute_aR(aL, wR, wL, A)`
- `def get_skid_ratio(bounds, maximize)`
- `def get_slip_bounds(wL, wR, w, wheel_radius, trackwidth)`
- `def get_v_w(w_r, w_l, wheel_radius, track_width)`
- `def get_w_from_ticks(left_encoder_value, right_encoder_value)`

**ati/perception/station_relocalisation/faiss_vpr.py**

- `def get_akaze_descriptor(akaze_object, frame_gray, mask, limit_keypts)`
- `def get_logistic_prob(val, x_transform_50_percentile, x_transform_80_percentile)`
- `def get_orb_descriptor(orb_obj, frame_gray, mask, limit_keypts)`
- `def get_sift_descriptor(sift_obj, frame_gray, mask, limit_keypts)`
- `def sort_kp_based_on_response(kps)`

**ati/perception/station_relocalisation/kiss_icp_setup.py**

- `def get4x4Pose(pose)`
- `def transform_points(T, points)`

**ati/perception/station_relocalisation/postprocess_run.py**

- `def calculate_distance(row, landmark_pose, dist_thresh, fov_radians)`
- `def get_landmark_ts_poses(run_name: str, map_folder: str, dist_thresh, num_frames_per_pose)`
- `def get_stations_info(map_folder)`
- `def main(args)`
- `def post_process(run_name: str, map_folder: str, create_faiss_index: bool)`

**ati/perception/station_relocalisation/recover_station.py**

- `def get_closest_station(found_pose: tuple, stations_info: dict)`
- `def get_faiss_requisites(config, map_folder, cam_str)`
- `def get_stations_info(map_folder)`
- `def main(args)`
- `def run_faiss_inference(faiss_vpr, cam_reader, vpr_metadata, actual_station_name, stations_info)`

**ati/perception/station_relocalisation/station_recovery_icp.py**

- `def compute_confidence(dist, min_dist, max_dist)`
- `def find_best_local_map(kiss_icp_obj, local_maps, frame, sigma, transformed_frame_dir)`
- `def rotation_mat_z(theta)`
- `def station_recovery_icp(map_folder: str, frame: np.ndarray, verbose: bool, transformed_frame_dir: str)`
- `def transform_points(T, points)`
- `def x_y_theta_from_matrix(matrix)`

**ati/perception/tests/data_loader.py**

- `def load_pkl_data(file_path)`
- `def save_pkl_data(obj_to_store, save_path)`

**ati/perception/tests/test_drivable_region.py**

- `def rotation_matrix_2d(theta)`

**ati/perception/trolley_detection/trolley_detection.py**

- `def get_lidar_data_stub()`
- `def main(argv)`

**ati/perception/trolley_detection/trolley_icp.py**

- `def find_line_ransac(p1)`
- `def find_plane(pts)`
- `def get_box_size(pts)`
- `def get_cluster(pts, trolley_offset, eps, hitch)`
- `def get_control_status_stub()`
- `def get_label_with_max_count(labels)`
- `def get_lidar_data_stub()`
- `def get_trolley_mesh(trolley_corners, r, mesh, z)`
- `def get_trolley_points(pts, trolley_corners, hitch_length, use_mesh, r, hitch_pt, z, debug, th_range, use_clustering)`
- `def icp_open3d(source, target, init_transform, tolerance, offset)`
- `def main(argv)`
- `def rotate_2d(pts, th, offset)`
- `def unrotate_2d(pts, th, offset)`

**ati/perception/trolley_detection/trolley_utils.py**

- `def get_numba_spec()`
- `def get_trolley_config_params(config)`
- `def score_rect(trolley, lidar_frame, t)`
- `def score_ring(trolley, lidar_frame, t)`
- `def search(trolley, lidar_frame, ts)`
- `def voxel_filter2d(points, voxel_size)`
- `def voxel_filter_slow(pts, voxel)`

**ati/perception/ultrasound/ultrasound.py**

- `def get_ultrasound_sensors(config)`
- `def process(d, u, theta)`
- `def process_ultrasound(distances, ultrasound_sensors, ultrasound_config)`

**ati/perception/utils/apriltag_station_setup.py**

- `def check_tag_ids(tag_ids, gen_tag_info)`
- `def get_tag_mem_id(tag_ids, gen_tag_info)`
- `def main(gen_tag_info_path, toml_folder)`
- `def write_to_toml(tag_mem_id, gen_tag_info, station_name, toml_folder)`

**ati/perception/utils/colorspace_hitch/hitch_segmentation.py**

- `def classify_hitch(rgb_img, nc, labels, stats, centroids, hsv_mask, hitch_classifier, num_pixels_threshold, roi_shape)`
- `def color_space_segmentation(rgb_img, hue_range, sat_range, val_range)`
- `def convert_cam_coordinates_to_right_hand_system(pts, cam_mat, img_shape)`
- `def get_hitch_from_ground_plane(hitch_center_ray, ground_plane_normal_cam, cam_height, hitch_height)`
- `def get_hitch_position(yratio0, yratio1, seg_stat, cam_mat, hitch_length)`
- `def template_hitch_detection(roi_gray, template0, template1, template0_hoffset, template1_hoffset, roi_shape)`

**ati/perception/utils/colorspace_hitch/main.py**

- `def main(argv)`
- `def publish_hitch_pose(sock, hitch_position_local, yelli_msg)`

**ati/perception/utils/lidar_utils.py**

- `def connected_components_numba(arr, degree, min_pts)`
- `def get_bbox(pts)`
- `def get_clusters_numba(pts, r, min_pts, tree)`
- `def limit_lidar_pts(data, xlim, ylim, zlim, return_indices)`

**ati/perception/utils/quaternion_utils.py**

- `def compose_multiple_gyro_to_quaternion(gyro_buffer, dts)`
- `def eular_to_quaternion(phi, theta, psi)`
- `def get_angle_axis_from_quaternion(quat)`
- `def get_cross_mat_from_vec(vec)`
- `def get_delta_quaternion_from_gyro(gyro, del_t)`
- `def get_derivate_quat_vec3(vec3)`
- `def get_derivative_q_c_wrt_q(q)`
- `def get_derivative_quat_rvec(rvec)`
- `def get_derivative_rot_mat_wrt_quat(q)`
- `def get_left_quaternion_matrix(p)`
- `def get_quat_cov_from_cov_eta(q, cov_eta, mean_eta)`
- `def get_quaternion_from_angle_axis(angle, axis)`
- `def get_quaternion_vel(angular_vel, e)`
- `def get_right_quaternion_matrix(p)`
- `def get_roll_pitch_yaw_from_quaternion(e)`
- `def get_rotation_matrix_from_quaternion(q)`
- `def get_yaw_pitch_roll_from_quaternion(e)`
- `def multiply_quaternion(q1, q2)`
- `def multiply_rot_derivative_vec(dR, vec)`
- `def quaternion_inv(q)`
- `def quaternion_normalize(q)`
- `def rotate_point(rotation, point)`
- `def rotate_pointcloud(rotation, pointcloud)`

**ati/perception/utils/tag_based_parking.py**

- `def get_marker_coords(marker_length)`
- `def get_tag_detector()`
- `def publish_tag_detections(tag_type, tag_id, corners, timestamp)`
- `def publish_tag_mule_pose(tag_type, tag_id, tag_mule_pose, timestamp)`

**ati/perception/utils/tag_detector.py**

- `def get_tag_coords(tag_length)`
- `def get_tag_detector()`
- `def publish_tag_detections(tag_type, tag_id, corners)`
- `def publish_tag_local(tag_type, tag_id, rvec, tvec)`

**ati/perception/utils/tag_ps4_setup.py**

- `def check_vehicle_motion(wheel_enc)`
- `def compute_tag_yelli_transform(qCA, tCA, qLC, tLC, yelli_pose)`
- `def get_tag_id_membership(all_tags, tag_id, tag_type)`
- `def indicator_lights(pub_sock)`
- `def main(argv)`
- `def write_to_config(qYA, tYA, mule_pose, tag_ids, tag_type, muleroot)`

**ati/perception/utils/tag_pub.py**

- `def main(argv)`

**ati/perception/utils/transform.py**

- `def apply_transform(A: Transform, B: Transform)`
- `def get_transform_from_config(config, ego_str, reference_str, get_factory, debug)`
- `def transform_from_reference_numba(pc, rotation, translation)`
- `def transform_to_reference_numba(pc, rotation, translation)`

**ati/perception/utils/write_config.py**

- `def add_val_to_config(toml_path, key, var, val, overwrite_line)`
- `def check_innermost_isdict(toml_dict)`
- `def recursive_key_search(toml_dict, key_split)`

**ati/peripherals/peripherals.py**

- `def main(argv) → Any`

**ati/peripherals/peripherals_utils.py**

- `def is_long_press(time_diff, duration)`

**ati/peripherals/trolley_loadcell.py**

- `def main(argv)`
- `def publish_loadcell_data(sock, data)`
- `def publish_loadcell_overload_fm(sock, data)`

**ati/safety/device_monitor.py**

- `def get_devices_to_monitor(config, vehicle_type)`
- `def main(argv)`

**ati/safety/system_monitor.py**

- `def copy_delfino_images()`
- `def handle_delfino_firmware_compatibility_error(message)`
- `def handle_epo_msg(orc, epo_pressed, message, sock)`
- `def main(argv)`
- `def send_peripherals(sock, epo_status)`
- `def update_system_fifo()`

**ati/safety/tpms_utils.py**

- `def handle_tpms_message(message)`
- `def raise_error(message, sensor, value)`

**ati/schema/__init__.py**

- `def decode_message(packet)`
- `def encode_message(topic, message)`

**ati/scripts/core_odometer.py**

- `def main(argv)`

**ati/scripts/core_recorder.py**

- `def create_new_folder(folder)`
- `def exit_handler(sig, frame)`
- `def main(argv)`

**ati/scripts/latency_monitor.py**

- `def main(debug)`
- `def send_msg(pub, topic, latency)`

**ati/scripts/record_data.py**

- `def process_lidar_and_yelli(dataset)`

**ati/scripts/record_sensors.py**

- `def copy_file(src, target, is_folder)`
- `def exit_handler(sig, frame)`
- `def get_field_names(field_list)`
- `def get_proto_vals(update, field_list)`
- `def main(argv)`
- `def recursive_get_proto_fields(msg_fields)`
- `def stop_recording()`

**ati/scripts/seed_odometry.py**

- `def main()`
- `def seed_odometry(distance)`

**ati/scripts/update_run_analytics.py**

- `def update_end_info(msg: list)`
- `def update_error_info(msg: list)`
- `def update_run_analytics(run_info: list)`
- `def update_start_info(msg: list)`
- `def update_table(command)`

**ati/scripts/utils/numpy_compat.py**

- `def _get_fields_and_offsets(dt, offset)`
- `def count_elem(dt)`
- `def structured_to_unstructured(arr, dtype, copy, casting)`
- `def unstructured_to_structured(arr, dtype, names, align, copy, casting)`

**ati/scripts/utils/point_cloud2.py**

- `def create_cloud(fields: Iterable[...], points: Iterable) → PointCloud2`
- `def dtype_from_fields(fields: Iterable[...]) → np.dtype`

**ati/scripts/watchdog.py**

- `def main(argv)`

**ati/slam/bbs_gpu/publish.py**

- `def main(argv)`
- `def publish()`

**ati/slam/bbs_gpu/publish_pose.py**

- `def angle_diff(a, b)`
- `def cross_track_error(station, current)`
- `def get_closest_station(found_pose: tuple, stations_info: dict)`
- `def get_stations_info(map_folder)`
- `def main(argv)`
- `def publish()`

**ati/slam/imu_tracker/ImuTracker.py**

- `def get_rolling_mean_var(new_val, arr, old_mean, old_var)`

**ati/slam/imu_tracker/quaternion_utils.py**

- `def eular_to_quaternion(phi, theta, psi)`
- `def get_angle_axis_from_quaternion(quat)`
- `def get_delta_quaternion_from_gyro(gyro, del_t)`
- `def get_quaternion_from_angle_axis(angle, axis)`
- `def get_quaternion_vel(angular_vel, e)`
- `def get_roll_pitch_yaw_from_quaternion(e)`
- `def get_yaw_pitch_roll_from_quaternion(e)`
- `def multiply_quaternion(q1, q2)`
- `def quaternion_inv(q)`
- `def quaternion_normalize(q)`
- `def rotate_point(self, rotation, point)`
- `def rotate_pointcloud(rotation, pointcloud)`

**ati/slam/lidar_marker3d/grid3d.py**

- `def odds(probability)`
- `def prob_from_odds(odds_val)`
- `def score_function(grid, grid_origin, pose, frame, grid_res, level_mapping)`
- `def search_fast(grid, grid_origin, poses, frame, grid_res, level_mapping)`

**ati/slam/lidar_marker3d/marker_loc.py**

- `def load_markers(folder)`
- `def main(argc, argv)`
- `def save_marker(folder, hgrids, roi_center)`

**ati/slam/lidar_marker3d/utils.py**

- `def generate_grid_res_array(lowest_level_grid_res, num_levels)`
- `def generate_hierarchical_search_spaces(grid_res_arr, search_windows, max_range)`
- `def generate_local_grid_search_space(search_windows, num_divs)`
- `def generate_local_search_space(grid_res, search_windows, max_range)`
- `def get_rotation_mat3d_from_roll_pitch_yaw(roll, pitch, yaw)`
- `def greedy_hierarchical_search(hgrids, frame_arr, current_pose, local_search_spaces, num_hit_th)`
- `def point_in_rectangle(rect, point)`
- `def transform_points3d_euler_rpy(pose3d, pts)`

**ati/slam/localization_check.py**

- `def convert_wheel_odo_delta_to_lidar_delta(wpose, lidar_y_offset)`
- `def extract_yelli_pose(update)`
- `def publish_generic(sock, name, values)`
- `def rotation_matrix_2d(theta)`
- `def transform_yelli_to_wheel(yelli_pose, lidar_offset)`

**ati/slam/yelli/__main__.py**

- `def main(args)`
- `def process_control_status(yelli_state, message)`
- `def process_imu(yelli_state, message)`
- `def process_lidar_frames(yelli_state, message)`
- `def process_mule_status(yelli_state, message)`
- `def process_odom(yelli_state, message)`

**ati/slam/yelli/grid.py**

- `def generate_neighbour_lookup_table()`
- `def odds(probability)`
- `def prob_from_odds(odds_val)`
- `def score_function(grid, grid_origin, pose, frame, grid_res, level_mapping, search_neighbours)`
- `def score_function_count_once(grid, grid_origin, pose, frame, grid_res, level_mapping)`
- `def score_function_z_grid_count_once(grid, z_grid, grid_origin, pose, frame, grid_res, level_mapping)`
- `def score_function_zgrid(grid, z_grid, grid_origin, pose, frame, grid_res, level_mapping)`
- `def search_fast(grid, grid_origin, poses, frame, grid_res, level_mapping, search_neighbours)`
- `def search_fast_count_once(grid, grid_origin, poses, frame, grid_res, level_mapping)`
- `def search_fast_zgrid(grid, z_grid, grid_origin, poses, frame, grid_res, level_mapping)`
- `def search_fast_zgrid_count_once(grid, z_grid, grid_origin, poses, frame, grid_res, level_mapping)`

**ati/slam/yelli/grid2cuda.py**

- `def find_count_once_score(scores, scores2d, grid_inds2d)`
- `def get_num_unique_inds_and_score(grid_inds, scores)`
- `def search_cuda(grid, nx, ny, ox, oy, poses, frame, grid_res, level_mapping, search_neighbours)`
- `def search_cuda_search_once(grid, nx, ny, ox, oy, poses, frame, grid_res, level_mapping, search_neighbours)`
- `def search_cuda_zgrid(grid, z_grid, nx, ny, ox, oy, poses, frame, grid_res, level_mapping)`

**ati/slam/yelli/grid_utils.py**

- `def array_shuffle(arr, shuffle_inds)`
- `def binary_search(val, arr, sort_inds, index_offset)`
- `def check_lidar_quadrants(frame, pts_th)`
- `def combine_poses(p1, p2)`
- `def combine_yelli_poses(p1, p2)`
- `def compute_half_res_grid(full_res_grid)`
- `def compute_half_res_grid_cuda(full_res_grid)`
- `def compute_hierarchical_grid(grid2d, num_levels)`
- `def filter_by_slope(frame, lidar_ht, slope_threshold, use_cuda)`
- `def generate_grid_res_array(lowest_level_grid_res, num_levels)`
- `def generate_hierarchical_search_spaces(grid_res_arr, x_search_window, y_search_window, angle_search_window, max_range)`
- `def generate_local_search_space(grid_res, x_search_window, y_search_window, angle_search_window, max_range)`
- `def get_2D_rotation_mat(theta)`
- `def get_angle_from_2D_rotation_mat(R)`
- `def get_closest_inds_from_ha_sorted_pts(sorted_frame)`
- `def get_closest_pts(frame)`
- `def get_closest_pts_numba(frame)`
- `def get_grid_params(grid_params, grid_res)`
- `def get_horizontal_segs(fr, H_index, H_th)`
- `def get_inverse_yelli_pose(pose)`
- `def get_inverse_yelli_rotation(theta)`
- `def get_inverse_yelli_transform(pose)`
- `def get_miss_pts(pts, step_size, num_miss_pts, num_skip_pts)`
- `def get_slopes(vfr, lidar_ht, V_index, D_index)`
- `def get_slopes_cuda(fr, lidar_ht, D_index)`
- `def get_sorted_vangles(fr, H_index, V_index, H_th)`
- `def get_sorted_vframe_slopes(frame, lidar_ht, D_index, V_index, H_index, H_th, use_cuda)`
- `def get_voxel_hash(points, voxel_size)`
- `def get_voxel_hash_gpu(points, voxel_size)`
- `def get_vsorted_frame_cuda(frame, V_index)`
- `def get_yelli_rotation(theta)`
- `def get_yelli_transform(pose)`
- `def hierarchical_search_v3(hgrids, pose_estimate, frame_arr, local_search_spaces, count_once, max_top_level_branches, score_th, debug)`
- `def imu_submap_pose_estimate(imu_tracker, time, submap_pose, pose)`
- `def insertion_sort(arr, sort_inds, index_offset)`
- `def inverse_pose(pose)`
- `def normalize_pose(theta)`
- `def random_sampling(points, voxels)`
- `def remove_hits_from_misses(miss_pts, hit_pts, grid_res, use_cuda)`
- `def sort_and_get_slopes(frame, lidar_ht, D_index, V_index, H_index, H_th)`
- `def sort_and_get_slopes_cuda(frame, lidar_ht, D_index, V_index, H_index, H_th)`
- `def voxel_sampling_filter(points, voxel_size, use_cuda)`

**ati/slam/yelli/hdf5_utils.py**

- `def copy_existing_tiles_to_new_grid(shifted_prev_txs, shifted_prev_tys, shifted_current_txs, shifted_current_tys, prev_grid, current_grid, grid_tile_size)`
- `def determine_quadrant(x, y)`
- `def get_fractional_tile_index(x, y, tile_size)`
- `def get_grid_and_tile_end_indexes(tile_ind, grid_tile_size, origin, grid_size)`
- `def get_grid_and_tile_start_indexes(tile_ind, grid_tile_size, origin)`
- `def get_grid_tile_start_end_indexes(tile_x_ind, tile_y_ind, origin_xy, shape_xy, grid_tile_size)`
- `def get_local_tile_inds_and_sorted_wrapped_ids(pose_xy, max_dist, tile_size)`
- `def get_max_min_tile_coord(txmin, tymin, txmax, tymax, tile_size)`
- `def get_max_tile_coord(tx, tile_size)`
- `def get_min_tile_coord(tx, tile_size)`
- `def get_new_inactive_keep_wrapped_tile_ids(wrapped_ids, prev_wrapped_ids)`
- `def get_num_tiles_on_disk(hdf5_file)`
- `def get_tile_ids_in_tile_array(tile_index_array, wrapped_ids)`
- `def get_tile_index(x, y, tile_size)`
- `def get_tile_index_from_wrapped_ids(wrapped_ids)`
- `def get_tile_indexs_around_pose(posexy, max_dist, tile_size)`
- `def get_tile_indexs_in_axis_aligned_box(min_extent, max_extent, tile_size, force_square)`
- `def get_tile_inds_and_sorted_wrapped_ids(posexy, max_dist, tile_size)`
- `def get_wrapped_tile_ids_around_pose(posexy, max_dist, tile_size)`
- `def get_wrapped_tile_index(x_tile, y_tile)`
- `def load_tile_index_array(hdf5_file)`
- `def load_tiles_to_display_grid_from_hdf5(wrapped_ids, shifted_txs, shifted_tys, tile_index_array, hdf5_file, grid, grid_tile_size, scale)`
- `def load_tiles_to_grid_from_hdf5(wrapped_ids, shifted_txs, shifted_tys, tile_index_array, hdf5_file, grid, grid_tile_size)`
- `def origin_shift_tiles(tile_xids, tile_yids, new_origin_x, new_origin_y)`
- `def read_meta_from_hdf5(dataset_name, hdf5_file)`
- `def segment_shift(x, xshift)`
- `def shift_tile_origin_to_bottom_left(txs, tys)`
- `def update_tile_array_to_be_written(local_tile_xs, local_tile_ys, wrapped_ids, tile_index_array, num_tiles_written, grid, grid_start_value, grid_tile_size)`
- `def write_index_array(tile_index_array, hdf5_file)`
- `def write_meta(map_meta, dataset_name, hdf5_file)`
- `def write_tiles_from_grid_to_hdf5_file(local_tile_xs, local_tile_ys, wrapped_ids, tile_index_array, num_new_tiles, grid, grid_tile_size, hdf5_file, compression)`
- `def write_tiles_to_hdf5_file(tiles_to_write, write_tile_index_array, hdf5_file)`

**ati/slam/yelli/map_update_utils.py**

- `def dump_map_update_metadata(run_dir, map_dir, update_id)`
- `def generate_map_metadata(run_dir)`
- `def get_next_update_id(map_folder)`
- `def save_map_update(multimap, folder, update_id, action_type, update_zslice, roi)`

**ati/slam/yelli/posegraph_utils.py**

- `def do_pose_graph_optimization(poses, constraints, submaps, pose_info_mat, loop_info_mat, robust_kernel, use_simple_posegraph)`
- `def generate_grid_res_array(lowest_level_grid_res, num_levels)`
- `def get_constraints_and_posegraph_poses(submap_manager, lpb, frame_filter_params, posegraph_params, node_poses, constraints, yield_progress)`
- `def get_robust_kernel(robust_kernel)`
- `def optimize_with_only_start_end_poses(submap_manager, lpb, frame_filter_params, posegraph_params, node_poses, constraints)`
- `def transform_remaining_poses(unopt_pose, opt_pose, poses)`

**ati/slam/yelli/utils.py**

- `def box_filter_frame(frame, min_dist, max_dist, zmin, zmax)`
- `def crop_actual_map(mmap, x, y, width, height)`
- `def filter_frame_beams(frame, min_dist, max_dist, beam)`
- `def filter_frame_z(frame, min_dist, max_dist, z_min, z_max)`
- `def generate_local_grid_search_space(x, y, theta, num_x, num_y, num_t)`
- `def generate_local_search_space(grid_res, x_search_window, y_search_window, angle_search_window, max_range)`
- `def grid_space(center, x, y, theta, num_x, num_y, num_t)`
- `def lidar_polar_to_xyz(frame)`
- `def rotation_matrix_2d(theta)`
- `def transform_grid_search_space(center, search_space)`
- `def transform_local_to_world(pose, points)`
- `def transform_world_to_local(pose, points)`
- `def voxel_filter2d(frame, voxel_size)`

**ati/slam/yelli/yelli_tracker.py**

- `def check_gyro_motion(gyro_tracker)`
- `def check_imu_motion(imu_tracker)`
- `def check_pose_divergence(pose0, pose1, threshold)`
- `def check_vehicle_motion(wheel_enc)`
- `def convert_wheel_odo_delta_to_lidar_delta(wpose, lidar_y_offset)`
- `def get_2D_rotation_mat(theta)`
- `def get_cupy_mempool()`
- `def get_map_version(map_folder)`
- `def get_map_zslice(map_folder)`
- `def get_wheel_pose_prob(poses, wpose, std_dev_x, std_dev_y, std_dev_t)`
- `def get_wheel_prediction(wheel_enc_buffer, wheel_enc_ts, pose, lidar_y_offset)`
- `def imu_pose_estimate(imu_tracker, time, pose)`
- `def is_inside_wheel_pose_zone(pose, zone_coords)`
- `def load_pose(db)`
- `def load_wheel_pose_zones()`
- `def point_in_rectangle(rect, point)`
- `def publish_min_pose(sock, frame_time, frame_id, pose, is_manual, raw_pose)`
- `def rounded_discrete_gaussian(x, mean, std)`
- `def save_pose(db, pose)`
- `def shrink_search_space(search_params)`
- `def within_bounds_pose_estimate_diff(prev_initial_pose, pose, initial_pose_diff_threshold)`

**ati/telemetry.py**

- `def main(argv)`
- `def report_event(config, message)`

**ati/tools/calc_cte.py**

- `def check_distance_criteria(day, run_id)`
- `def display_info(count_num_recov, display_details_data, global_cte_results, cte_results, recov_details)`
- `def get_counts_from_dict(value)`
- `def get_recovery_counts(cte_data, day, run_id)`
- `def main(day, count_num_recov, display_details_data)`
- `def process_runs(day, count_num_recov)`
- `def process_tracker_file(day, run_id)`

**ati/tools/diagnostics/brake_diagnostics.py**

- `def braking_distance_and_deceleration(dataset, rear_en_data, steer_en_data)`
- `def cal_braking_distance_and_deceleration_when_0_ticks_ref_at_certain_pts_of_the_run(ticks_when_ref_0_list, time_t)`
- `def cal_braking_distance_and_deceleration_when_0_ticks_ref_throughtout(rear_ticks, rear_time, index)`
- `def creating_pd_for_rear_encoder(low_level_control)`
- `def diagnose_encoder_brake_data(dataset, truncated)`
- `def fit_curve(speed_list, bd_list, dataset)`
- `def get_first_time_stamp_from_data(whole_data)`
- `def get_index_ref_0(rear_en_pd)`
- `def get_index_when_brakes_applied(index)`
- `def getting_ticks_when_ref_0_and_corresponding_timstamps(index, index_when_brakes_applied, rear_ticks, rear_time)`
- `def objective(x, a, b, c)`
- `def plotting_braking_distance_and_deceleration(dataset, braking_distance, deceleration, speeds_before_applying_brakes)`
- `def post_processing_encoder_data_for_brakes(low_level_control, whole_data, dataset)`
- `def print_braking_distance(dataset, braking_distance_list, max_braking_distance, min_braking_distance)`
- `def print_deceleration(dataset, deceleration, max_deceleration, min_deceleration)`
- `def print_speeds_just_before_applying_brakes(dataset, speeds_before_applying_brakes, max_speed_just_before_applying_brakes, min_speed_just_before_applying_brakes)`
- `def removing_empty_lists_in_ticks_when_ref_0_and_timestamps(ticks_when_ref_0_list, time_t)`

**ati/tools/diagnostics/camera_diagnostics.py**

- `def appending_to_text_file(dataset, statements)`
- `def get_data_of_front_cam(data)`
- `def get_data_of_rear_cam(data)`
- `def writing_to_text_file(dataset, statements)`

**ati/tools/diagnostics/diag_utils.py**

- `def _read_int(f)`
- `def draw_mule(ax, pose, run_config)`
- `def get_drivable_frame_id(nlidar, current_run_folder)`
- `def get_mule_pts(path, pose, run_config)`
- `def get_rotation_matrix(roll, pitch, yaw)`
- `def plot_planned_path(ax, current_run_folder)`
- `def rotation_matrix_2d(theta)`
- `def topview(data, xlim, ylim, zlim, ax, fig, alpha, show, useht, newdata, title, figsize, colorbar)`
- `def transform_local_to_world(pose, points)`
- `def voxel_centroid_fast(points, voxels)`
- `def voxel_filter(points, voxel_size)`

**ati/tools/diagnostics/diagnostics_summary.py**

- `def concatenating_same_day_csv_files(final_datasets, path_to_latest_day_folder, recorder_folder, start_epoch, end_epoch)`
- `def create_run_summary_folder(dataset, data_to_be_diagnosed)`
- `def creating_temp_data_before_running_diagnostics(final_datasets, latest_data_folder, recorder_folder, list_of_csv_files_to_be_concatenated, start_epoch, end_epoch)`
- `def get_creation_time_for_folders_in_data_folder(item)`
- `def get_creation_time_for_folders_in_day_folder(item1)`
- `def get_dates(sorted_items)`
- `def get_error_tags(test_results)`
- `def log_dataset_size_and_run_type(data_to_be_diagnosed, dataset_name)`
- `def make_tarfile(output_filename, source_dir)`
- `def process_slice_data_with_ts(dataset, recorder_folder, start_epoch_ts, end_epoch_ts)`
- `def quick_diagnostics()`
- `def run_and_upload_diagnostics_data_to_fm(dataset, truncated, start_ts, end_ts)`
- `def run_diagnostics(dataset, truncated, start_ts, end_ts)`
- `def sort_and_get_latest_day_folder(recorder_folder)`
- `def sort_and_get_same_day_data_folders(recorder_folder, latest_data_folder, start_epoch, end_epoch)`
- `def summary_diagnostics(dataset, tmpdir, truncated)`
- `def tag_dataset(dataset, error_tags)`
- `def writing_to_text_file(dataset, statements)`

**ati/tools/diagnostics/encoder_diagnostics.py**

- `def appending_to_text_file(dataset, statements)`
- `def cal_failure_percentage(data, en_data, spurious)`
- `def creating_pd_for_all_encoders(data)`
- `def diagnose_encoder_data(dataset, truncated)`
- `def diff_ticks_ref_and_ticks(en_data)`
- `def get_first_time_stamp_from_data(whole_data)`
- `def get_the_file_size(filepath)`
- `def get_time_for_3_encoder_readings(data)`
- `def post_processing_encoder_data(data, dataset, whole_data)`

**ati/tools/diagnostics/lidar_diagnostics.py**

- `def check_for_missing_sectors(sensor_exceptions, dataset)`
- `def check_for_stale_data_and_frame_rate(frames, dataset)`
- `def diagnose_lidar_data(dataset, truncated)`
- `def lidar_frame_rate_check(dataset, frames)`
- `def lidar_reachability_check(dataset, lidar_ip_address)`
- `def missing_sectors(dataset, sensor_exceptions)`
- `def stale_lidar_frames(dataset, frames)`

**ati/tools/diagnostics/mule_conveyor_sensor.py**

- `def main()`

**ati/tools/diagnostics/perf_diagnostics.py**

- `def diagnose_perf_data(dataset, truncated)`
- `def post_processing_battery_data(data, dataset)`
- `def post_processing_perf_data(data, dataset)`

**ati/tools/diagnostics/status_view.py**

- `def close_files()`
- `def g2w(x, ox)`
- `def get_ekf_pose(nlidar)`
- `def get_extended_score(map2d, xs, ys, dists, n)`
- `def get_neighbours(x, y, n)`
- `def get_yelli_grid_origin(map_dir)`
- `def get_yelli_matches(map_root, pts, dists)`
- `def get_z_slice(map_dir)`
- `def lidar_frame_pose(frame, pose, zmin, zmax, extended)`
- `def open_files(data_folder, display)`
- `def plot_status_view(dataset, truncated)`
- `def set_env(var, value)`
- `def show_cam_image(ax, ts, cam)`
- `def show_pts(ax, mask, c, s, alpha, sample)`
- `def status_view(data_folder, ref_folder, nlidar, zoom)`
- `def status_view_wrapper(data_folder, map_root, nlidar, zoom)`
- `def validate(pts, shape)`
- `def w2g(x, ox)`

**ati/tools/diagnostics/tracker_diagnostics.py**

- `def diagnose_tracker_data(dataset, truncated)`
- `def post_processing_tracker_data(tracker_data)`

**ati/tools/diagnostics/usb_devices_enumeration.py**

- `def extracting_bus_level_info_of_usb_devices()`
- `def list_of_usb_devices_enumerated(dataset)`
- `def process_usb_devices_string_output(usb_devices_string_output)`

**ati/tools/diagnostics/utils/diag_utils.py**

- `def _read_int(f)`
- `def add_name(a, b)`
- `def check_if_run_duration_longer_than_given_ts(list_of_files_to_be_concatenated, recorder_folder, path_to_latest_day_folder, temp_data_folder, start_epoch, end_epoch)`
- `def creating_one_pandas_data_frame_for_multiple_runs(list_of_files_to_be_concatenated, temp_data_folder, final_datasets, recorder_folder, path_to_latest_day_folder, start_epoch, end_epoch)`
- `def draw_mule(ax, pose, run_config)`
- `def dumping_pd_into_csv(df, path, filename)`
- `def duration_of_run(dataset)`
- `def get_drivable_frame_id(nlidar, current_run_folder)`
- `def get_end_indices(end_epoch, frames_data)`
- `def get_latest_date_indices_in_sorted_items(dates)`
- `def get_list_of_final_datasets(start_hour, end_hour, start_minute, end_minute, latest_datasets_based_on_day_folder)`
- `def get_list_of_latest_datasets_based_on_day_folder(latest_date_indices_in_sorted_items, sorted_items)`
- `def get_mule_pts(path, pose, run_config)`
- `def get_rotation_matrix(roll, pitch, yaw)`
- `def get_start_and_end_time_from_the_given_epoch_timestamp(start_epoch, end_epoch)`
- `def get_start_indices(start_epoch, frames_data)`
- `def plot_planned_path(ax, current_run_folder)`
- `def rotation_matrix_2d(theta)`
- `def topview(data, xlim, ylim, zlim, ax, fig, alpha, show, useht, newdata, title, figsize, colorbar)`
- `def transform_local_to_world(pose, points)`
- `def voxel_centroid_fast(points, voxels)`
- `def voxel_filter(points, voxel_size)`

**ati/tools/diagnostics/utils/drivable_grid.py**

- `def find_maximum(grids)`

**ati/tools/diagnostics/utils/encoder_plots.py**

- `def plotting_encoder_data(left_en_data, right_en_data, steer_en_data, rear_en_data, dataset)`

**ati/tools/diagnostics/utils/print_encoder_statements.py**

- `def print_abs_encoder_failure_analysis(dataset, abs_enc_failure_percentage, abs_enc_failure_i)`
- `def print_enc1_failure_ov_analysis(dataset, enc1_failure_ov_percentage, enc1_failure_ov_i, enc1_name, enc2_name)`
- `def print_encoder_disconnection_analysis(dataset, encoder_disconnection_percentage, encoder_disconnection_i, enc_name)`
- `def print_missing_enc_data_count(dataset, enc_missing_readings_count, enc_name)`
- `def print_motor_stall_analysis(dataset, motor_stall_percentage, motor_stall, motor_stall_i, last_motor_stall_time)`
- `def print_overshoot_count(dataset, overshoot_score_count, overshoot_score_i, enc_name)`
- `def print_runaway_analysis(dataset, runaway_percentage, runaway, runaway_i)`
- `def print_spurious_count_analysis(dataset, spurious_count_percentage, spurious_i, enc_name)`
- `def print_stall_count(dataset, stall_score_count, stall_score_i, enc_name)`
- `def print_steer_motor_controller_or_enc_failure_analysis(dataset, steer_motor_controller_or_enc_failure_percentage, abs_enc_steer_diff_steer_ref_i)`
- `def print_steer_motor_stall_analysis(dataset, steer_motor_stall_percentage, steer_motor_stall_i)`
- `def print_summary(dataset, spurious_count_left_percentage, spurious_count_right_percentage, left_encoder_disconnection_percentage, right_encoder_disconnection_percentage, left_failure_ov_percentage, right_failure_ov_percentage, motor_stall_percentage, motor_stall, runaway_percentage, runaway, abs_enc_failure_percentage, steer_motor_controller_or_enc_failure_percentage, steer_motor_stall_percentage)`

**ati/tools/diagnostics/yelli_diagnostics.py**

- `def diagnose_yelli_data(dataset, truncated)`
- `def post_processing_yelli_data(yelli_data)`

**ati/tools/gmaj_creator.py**

- `def create_gmaj(wpsj_path, gmaj_path)`
- `def get_station_dict(station_id, pose, name, tags)`
- `def get_stations_poses_dict(new_stations_info)`
- `def get_terminal_line_dict(line_id, t1, t2)`
- `def update_json_file(terminal_lines, stations, file_path, wpsj_checksum)`

**ati/tools/lidar_frames_to_pcd.py**

- `def convert_to_pcd(dataset_folder, lidar_type, max_frames, trim, pcd_store_path, max_x, max_y, min_y, max_z, min_z)`

**ati/tools/loadcell/libraries/Adafruit_SSD1306/scripts/make_splash.py**

- `def main(fn, id)`

**ati/tools/map_utils.py**

- `def convert_map_features(saveas)`
- `def download_map_files(config, file_names)`
- `def get_checksum(fname, fn)`
- `def get_map_checksum()`
- `def get_map_info()`
- `def get_map_zones()`
- `def import_camera_zone_data(map_dict, zone_type)`
- `def import_low_speed_zone_data(map_dict, zone_type)`
- `def import_map_features(map_dict, zone_type, attrs)`
- `def import_obstacle_avoidance_zone_data(map_dict, zone_type)`
- `def import_ramp_zone_data(map_dict, zone_type)`
- `def import_traffic_intersection_zone_data(map_dict, zone_type)`
- `def import_variable_padding_zone_data(map_dict, zone_type)`
- `def import_variable_stop_dist_zone_data(map_dict, zone_type)`
- `def load_map_features(feature, convert)`
- `def post_process_map_features(_dict)`

**ati/tools/mcap_visualisation/mcap_json.py**

- `def point_yeilder(ts_dt, frame)`

**ati/tools/mcap_visualisation/mcap_proto.py**

- `def append_file_descriptor(file_descriptor: FileDescriptor)`
- `def build_file_descriptor_set(message_class: Type[...]) → FileDescriptorSet`

**ati/tools/mcap_visualisation/mcap_ws.py**

- `def publish_to_ws()`

**ati/tools/mcap_visualisation/scene_update_prims.py**

- `def get_cube(position, orientation_q, size, color)`
- `def get_pose(position, orientation_q)`
- `def get_text(text, position, orientation_q, color, font_size)`

**ati/tools/perf_process_streamlit.py**

- `def calculate_statistics(proc_df, selected_metrics)`
- `def clean_and_sort_data(df)`
- `def clean_process_name(cmdline)`
- `def create_process_plot(proc_df, short_proc, selected_metrics)`
- `def create_visualizations(merged_df, selected_processes, selected_metrics)`
- `def display_process_statistics(proc_df, short_proc, selected_metrics)`
- `def get_metrics_list(df)`
- `def load_and_merge_data(procnames_path, procperf_path)`
- `def main()`
- `def merge_process_data(procnames_df, procperf_df)`
- `def plot_metric(ax, proc_df, metric, short_proc)`
- `def process_timestamps(df)`
- `def set_axis_limits(ax, proc_df, metric)`

**ati/tools/reader/lidar_pb.py**

- `def _read_int(f)`
- `def get_spherical_coordinates(frame)`

**ati/tools/reader/object_pb.py**

- `def convert_obj3d_to_bbox3d(obj3d)`

**ati/tools/reader/perception_sensors.py**

- `def is_data_sliced(dataset)`

**ati/tools/visualizer/body_mask.py**

- `def show_body_mask()`

**ati/tools/visualizer/camera.py**

- `def camera_view(ts)`
- `def disp_video(vis, cam, ts, ts_abs)`
- `def get_cam_videos(vis, cam)`
- `def get_depth_scale(run, cam)`
- `def get_depth_videos(vis, cam)`
- `def get_start_time(run_name, cam)`
- `def is_empty(depth_image)`

**ati/tools/visualizer/common.py**

- `def allow_download(data, fname, text)`
- `def callback1()`
- `def callback2()`
- `def camera_data_exists(vis)`
- `def choose_dir(prefix, default)`
- `def choose_lidar(vis)`
- `def close_files(vis)`
- `def convert_to_3d(img)`
- `def disp_camera_images(vis, rgb_image, depth_image, title, project_pts)`
- `def disp_rgb_image(vis, rgb_image, title)`
- `def draw(cx, dx)`
- `def draw_cube(cx, cy, cz, dx, dy, dz, dd)`
- `def draw_mule(vis, ax, pose)`
- `def draw_rectangle(ax, x, y, t, xw, yw)`
- `def find_pts_inside_mule(vis, pts, mule_mask)`
- `def g2w(x, ox)`
- `def generate_ground_plane(x, y, N, rear)`
- `def generate_plane(xlim, ylim, zlim)`
- `def get_cache_file()`
- `def get_camera_data(vis, frame_id, ts, cam, rgb_image, depth_image, depth_pts)`
- `def get_camera_list(vis)`
- `def get_custom_events()`
- `def get_data(vis, filename, n1, n2)`
- `def get_drivable_frame_id(vis, nlidar)`
- `def get_env(var, default_value)`
- `def get_extended_score(map2d, xs, ys, dists, n)`
- `def get_first_frame_ts(vis)`
- `def get_frame_id(vis, timestamp)`
- `def get_frame_id_from_datetime(timestamp, text)`
- `def get_frame_id_from_ts(s, t0, run_year)`
- `def get_frame_range(vis, st, start, end)`
- `def get_frame_time(vis, frame_id)`
- `def get_lidar_2d_frame(vis, nlidar)`
- `def get_lidar_frame(vis, nlidar, lidar_id, add_spherical)`
- `def get_lidar_frame_column_name(column)`
- `def get_lidar_frame_columns()`
- `def get_lidar_ht(vis, path)`
- `def get_lidar_type(vis)`
- `def get_map_scaling(vis, max_size_warning)`
- `def get_map_size(vis)`
- `def get_mule_pts(vis, pose, padding, z)`
- `def get_mule_pts2(config, inner, enlarge)`
- `def get_mule_pts_3d(vis, pose, fill, cuboids)`
- `def get_neighbours(x, y, n)`
- `def get_num_range(st, start, end, text)`
- `def get_outliers(vis, csv_file_name, column_name, max_time)`
- `def get_payload_detection_frames(vis)`
- `def get_payload_pts(vis, payload_pose, payload_dims, payload_padding)`
- `def get_perception_reader(vis)`
- `def get_platform_pts(vis, platform_pose, platform_dims, platform_padding)`
- `def get_pose(vis, nlidar, ekf)`
- `def get_poses(vis, start, end, ekf)`
- `def get_reference_path(vis, start, end, exclude_inplace)`
- `def get_roll_pitch(vis, nlidar)`
- `def get_run_config(vis, path, param, default)`
- `def get_run_year(vis)`
- `def get_session_file()`
- `def get_slow_mode(vis)`
- `def get_station(pose)`
- `def get_stoppage_summary(vis)`
- `def get_stoppages(vis)`
- `def get_summary(vis)`
- `def get_summary_cached(vis)`
- `def get_summary_data(vis, nrange, rows)`
- `def get_summary_uncached(vis)`
- `def get_timestamp_from_log(l, run_year)`
- `def get_total_dist(yelli)`
- `def get_trolley_vertices(trolley_cords, c, l, b, vehicle_params)`
- `def get_ultrasonic_frame(vis, nlidar)`
- `def get_vehicle_params(vis)`
- `def get_viewing_angle(default, d, anchor)`
- `def get_wheel_control_data(vis, start, end)`
- `def get_yelli_matches(map_root, pts, dists)`
- `def get_z_slice(map_dir)`
- `def get_zoom_pos(cx, cy, zoom, location)`
- `def is_empty(depth_image)`
- `def is_slice_data(vis)`
- `def is_valid_map_folder(d)`
- `def is_valid_run_folder(d)`
- `def keyword_search(pat, str_format, mule_log)`
- `def keyword_search2(pat, str_format, mule_log)`
- `def linux_to_local_datetime(ts, adj)`
- `def linux_to_local_time(ts, adj)`
- `def load_cache_file()`
- `def load_map(map_root)`
- `def log_session()`
- `def make_smooth(data, n)`
- `def norm_angle(th, eps)`
- `def plot_planned_path(vis, ax)`
- `def plot_poly(ax, xs, ys, c, ls)`
- `def plot_reference_path(vis, ax, nlidar, past, future, c, ls, lw, n)`
- `def plot_trolley(trolley_cords, fig, l, b, vehicle_params, style, row, col)`
- `def preprocess_trip_log(vis, data)`
- `def project_lidar_pts(vis, fig, lidar_pts, row, col)`
- `def read_mule_log(vis)`
- `def reset_session_state()`
- `def rotate_2d(pts, pose)`
- `def run_command(cmdline)`
- `def run_process(cmdline)`
- `def save_cache_file()`
- `def segment_points(pts, zmin, zmax, cx, cy, zoom)`
- `def select_dir(prefix, key, allow_full_folder)`
- `def select_lidar_column(prompt, default_column, anchor)`
- `def select_map(confirm, update, new_map)`
- `def select_run()`
- `def seq(x, threshold)`
- `def seq2(x, threshold)`
- `def set_axis_zoom(ax, xs, ys, name)`
- `def set_env(var, value)`
- `def set_live_data_flag()`
- `def set_run_config(check_live_data)`
- `def show_cam_image(ax, ts, cam)`
- `def show_mule_outline(vis, ax, pose, view)`
- `def stplot(fig)`
- `def str_format_def(l, s)`
- `def str_format_ts(l, s)`
- `def subdirectories(path)`
- `def update_from_older_config(vis)`
- `def valid(s, e)`
- `def valid_dir(d, key)`
- `def validate(pts, shape)`
- `def validate_frames(vis, start, end)`
- `def w2g(x, ox)`

**ati/tools/visualizer/control_view.py**

- `def control_view()`
- `def disp_zones(ax, title, zone_list)`
- `def get_csv_data(filepath)`
- `def get_encoder_data_vs_frame_id(ref, mask, frame1, frame2)`
- `def get_encoder_data_vs_time(ref, mask, time1, time2)`
- `def get_powerboard_data(ref_power, x_var, start, end, diff_time)`
- `def get_station_data(map_root)`
- `def get_station_symbol(theta)`
- `def isclose(t, v)`
- `def low_control_view()`
- `def plot(name, data, var, row, symbol, c, size, opacity, scale, offset, dash, ax, ay)`
- `def plot_currents(text)`
- `def plot_encoder(text, data, c, suffix)`
- `def plot_gradient(text)`
- `def plot_map_plotly(map_root, allow_zoom, show_features, show_stations, interactive, show_poses, show_routes, scale_map, show_map_values, ranges, fig)`
- `def plot_tracker(track, wheel)`
- `def plot_yelli_ekf_diff_plotly(vis, ekf, yelli)`
- `def read_csv_selection(vis, filename, n1, n2, sample)`
- `def sample_data(vis, csv_data, sample_size, ask)`
- `def show_stoppages(vis, fig, n1, n2)`
- `def show_velocities(vis, fig, tracker, col)`
- `def title2(text, x, ydata, c)`

**ati/tools/visualizer/csv.py**

- `def apply_filter(csv_data, col, fn, val)`
- `def ax_plot(ax, x, y, xlabel, ylabel, c, s)`
- `def csv_viewer(csv_file, direct)`
- `def custom_imu(vis, fig, data, c, x_col, smooth)`
- `def custom_lidar(vis, fig, data, column, x_col, smooth)`
- `def custom_low(vis, fig, data, col, x_col, smooth)`
- `def custom_low_control(vis, ax, data, c, x_col, smooth)`
- `def custom_ps(vis, ax, data, col, x_col, smooth)`
- `def custom_sensor_exc(vis, fig, data, col, x_col, smooth)`
- `def custom_sensor_exc_matplotlib(vis, ax, data, col, x_col, smooth)`
- `def custom_summary(vis, fig, data, y_col, x_col, smooth)`
- `def custom_trips(vis, ax, data, c, x_col, smooth)`
- `def get_bias(x, w)`
- `def get_custom_fn(csv_file)`
- `def get_data(vis, csv_file)`
- `def get_default_cols(csv_file)`
- `def get_dist(fname)`
- `def get_frame(fn)`
- `def get_process_label(label)`
- `def get_wheel_encoder_scale(vis)`
- `def maxrange(p)`
- `def moving_average(x, w)`
- `def moving_variance(x, w)`
- `def sample_data(csv_data, sample_size)`

**ati/tools/visualizer/display_point_cloud.py**

- `def add_trace(fig, trace)`
- `def disp_pts(name, pts, color, sz, cmin, cmax)`
- `def disp_pts_2d(points, flags, images, view_angle, project_pts, title, zrange, pose, fig)`
- `def disp_pts_3d(points, flags, images, view_angle, cam, title, color)`
- `def draw_ray(th0, th1, R, text)`
- `def draw_rect(x1, x2, y1, y2, c)`
- `def scat1(name, data, ix, iy, icolor, size, colors, zmin, zmax)`
- `def scat2(name, data, ix, iy, icolor, size, color)`
- `def scat3(name, data, ix, iy, size, color)`

**ati/tools/visualizer/lidar.py**

- `def add_image(fig, image, name, row, col, text)`
- `def add_mule_path(fig, mule_path, row, col)`
- `def callback()`
- `def detect_human_lidar_image(frame, W2, L2, nbeams, min_dist, min_range, min_width, min_ratio)`
- `def disp_360_degree_view_plotly(vis, frame, title, zoom, nbeams, colour)`
- `def disp_column(vis, frame, zoom, column, colour, title, log)`
- `def disp_front_view(vis, selected, cx, cy, zoom, zmin, zmax, ground, H)`
- `def disp_side_view(vis, selected, cx, cy, zoom, zmin, zmax, ground, H)`
- `def draw_circle(fig, x, y, w, row, col, color)`
- `def get_360_degree_image(vis, frame, zoom, nbeams, column)`
- `def get_event_details(nlidar)`
- `def get_opt(text, options, default)`
- `def get_path(vis, nlidar)`
- `def get_z_slice(map_dir)`
- `def highlight_obstacle(fig, dp, row, col)`
- `def is_obstacle(dp)`
- `def lidar_tilt(nlidar, zoom)`
- `def lidar_view(nlidar)`
- `def localize_plotly(vis, nlidar, zoom, options)`
- `def make_title(nlidar, pose, dp)`
- `def plot(name, x, y, color, lw, style)`
- `def plot_estimated(fig, estimated_trajectory, row, col)`
- `def plot_tracker(fig, tracker, poses, row, col)`
- `def policy_view(frame_id, zoom, options)`
- `def restack(img, wn, margin, extra)`
- `def save_fig(fig, imgdir, frame_id, prefix)`
- `def scat(name, x, y, color, size)`
- `def select_camera(vis, cams, location)`
- `def set_title(fig, title, row, total_rows)`
- `def set_zoom(fig, dp, zoom, title)`
- `def show_mule_outline(fig, mule, row, col)`
- `def show_payload_outline(fig, payload, row, col)`
- `def show_platform_outline(fig, platform, row, col)`
- `def validate(pts, shape)`

**ati/tools/visualizer/mcap_create.py**

- `def create_mcap()`

**ati/tools/visualizer/obstacle_detection.py**

- `def add_trace(fig, image, zmin, zmax, name, colorbar_y, colorbar, extents, row, col)`
- `def callback()`
- `def get_circle_pts(x, y, r, dth)`
- `def plot_3d(pts, size, opacity, name, color, margin)`
- `def plot_frenet_candidate_paths(vis, fig, frame_id, cand_paths, vehicle_params, mule_dims, show_mule_rectangle, show_all_paths, row, col)`
- `def show_obstacle_detection(frame_id)`

**ati/tools/visualizer/payload_detection.py**

- `def run_live_payload_detection(vis, data_folder, frame_id, config)`
- `def show_past_payload_data(vis, data_folder, frame_id)`
- `def show_payload_data()`

**ati/tools/visualizer/perf.py**

- `def get_cpu_usage(procperf_df, proc_name)`
- `def get_proc_name(row)`
- `def get_proc_name_pid_map(run_folder)`
- `def get_proc_perf_df(run_folder)`
- `def proc_perf()`

**ati/tools/visualizer/sanity.py**

- `def customize_timeline()`
- `def disp_combined_view(frames)`
- `def display_change_log()`
- `def display_sensor_fovs(vis, data_folder, ref_folder)`
- `def extend_mask(fov, mask, n)`
- `def get_first_frame_timestamp(vis)`
- `def get_frame_time(vis, n, hh, mm, ss, tol, rev, filename)`
- `def get_freq(f1)`
- `def get_pmv3_cuboids(lift_height, scissor_extension)`
- `def get_run_times(vis)`
- `def get_time_slice_data()`
- `def get_timestamp_line_number(vis, hh, mm, ss, tolerance, rev, file)`
- `def get_video_filename(tmpdir, run, video)`
- `def load_json(text, fname, colour, opacity)`
- `def log_view()`
- `def make_video(mp4, img_dir, prefix)`
- `def misc_tools()`
- `def process_slice_data(vis, path, start, end)`
- `def run_command(cmd)`
- `def sanity_check(show_info)`
- `def session_details()`
- `def setup_imgdir(tmpdir, run, video)`

**ati/tools/visualizer/selectrun.py**

- `def groupby_ext(files, sizes)`
- `def select_data()`

**ati/tools/visualizer/sensor_fov.py**

- `def display_sensor_fovs()`
- `def extend_mask(fov, mask, n)`
- `def get_pmv3_cuboids(lift_height, scissor_extension)`
- `def load_json(text, fname, colour, opacity)`

**ati/tools/visualizer/status.py**

- `def add_text(x, y, text, xanchor, yanchor, size)`
- `def disp_image(rgb_image, fig, row, col)`
- `def disp_lidar(vis, lidar_frame, fig, depth_pts, cx, cy, zoom, row, col)`
- `def status_view(frame_id, zoom, zoom_lidar, interactive, options)`
- `def status_view_wrapper(data_folder, map_root, nlidar, zoom)`

**ati/tools/visualizer/timeline.py**

- `def add_text(t)`
- `def callback_range_select()`
- `def callback_single_select()`
- `def get_selection(event, selection)`
- `def get_single_slection(event, n)`
- `def get_single_slection_text(event)`
- `def is_valid_selection()`
- `def show_timeline(x_col, nlidar, nrange, title, show, select, select_trip, rerun)`

**ati/tools/visualizer/visualizer.py**

- `def get_latest_folder(folder)`
- `def get_session_details()`
- `def logout()`
- `def main()`
- `def reset_vis()`

**ati/tools/visualizer_csv.py**

- `def plot(tracker, attributes, start, end)`

**ati_core/mule_services/ati_comms.py**

- `def append_eventlog(msg)`
- `def get_basic_info()`
- `def main()`
- `def send_error_to_fm(service_req)`

**ati_core/mule_services/usb_devices_enumeration.py**

- `def append_eventlog(msg)`
- `def extracting_bus_level_info_of_usb_devices()`
- `def list_of_usb_devices_enumerated()`

**epo/epo_v2.py**

- `def comparator(value)`
- `def create_core_logs_folder()`
- `def exit_epo_recorder_handler(sig, frame)`
- `def exit_handler_epo(signal, frame)`
- `def find_sequence(port, comparator, size)`
- `def find_sync(port, sync_sequences)`
- `def liveness_thread()`
- `def main(argv)`
- `def parse_electrifuel_packet(data)`
- `def print_sync_logs(value)`
- `def publish_update(bms_type, data, low_battery_fault)`
- `def read_daly_packet(ser)`
- `def read_electrifuel_packet(ser)`
- `def resync(port, sync_sequence)`
- `def shutdown(mule_env)`
- `def shutdown_thread()`
- `def start_serial_comms()`
- `def stop_recording()`

**epo/epo_v3.py**

- `def comparator(value)`
- `def create_core_logs_folder()`
- `def exit_epo_recorder_handler(sig, frame)`
- `def exit_handler_epo(signal, frame)`
- `def find_sequence(port, comparator, size)`
- `def find_sync(port, sync_sequences)`
- `def liveness_thread()`
- `def logging_mule_epo(sock, logger, sensors)`
- `def main(argv)`
- `def parse_electrifuel_packet(data)`
- `def print_sync_logs(value)`
- `def publish_update(bms_type, data, low_battery_fault)`
- `def read_EF_CAN_packet(ser)`
- `def read_daly_packet(ser, daly_packet)`
- `def read_electrifuel_packet(ser)`
- `def resync(port, sync_sequence)`
- `def shutdown(mule_env)`
- `def shutdown_thread()`
- `def start_serial_comms()`
- `def stop_recording()`

**epo/epo_v3_utils.py**

- `def checksum_calc(bytechunks)`
- `def parse57(data, bms_packet)`
- `def parse90(data, bms_packet)`
- `def parse91(data, bms_packet)`
- `def parse92(data, bms_packet)`
- `def parse93(data, bms_packet)`
- `def parse94(data, bms_packet)`
- `def parse9501(data, bms_packet)`
- `def parse9502(data, bms_packet)`
- `def parse9503(data, bms_packet)`
- `def parse9504(data, bms_packet)`
- `def parse96(data, bms_packet)`
- `def parse97(data, bms_packet)`
- `def parse98(data, bms_packet)`
- `def parseChunk(chunk, bms_packet)`
- `def parseDataInChunk(data, bms_packet)`
- `def processing_byte_0_in_faulty_condition_info(Byte_0, bms_packet)`
- `def processing_byte_1_in_faulty_condition_info(Byte_1, bms_packet)`
- `def processing_byte_2_in_faulty_condition_info(Byte_2, bms_packet)`
- `def processing_byte_3_in_faulty_condition_info(Byte_3, bms_packet)`
- `def processing_byte_4_in_faulty_condition_info(Byte_4, bms_packet)`
- `def processing_byte_6_in_faulty_condition_info(Byte_6, bms_packet)`
- `def processing_faulty_condition_codes_in_98_header(fault_byte_binary, bms_packet)`

**mule_analytics/alembic/env.py**

- `def run_migrations_offline() → Any`
- `def run_migrations_online() → Any`

**mule_analytics/alembic/versions/52893cd8232c_init_db.py**

- `def downgrade() → Any`
- `def upgrade() → Any`

**mule_analytics/core_db.py**

- `def connect()`
- `def get_engine(MULE_DB_URI)`
- `def get_session(MULE_DB_URI)`

**mule_analytics/db_utils.py**

- `def convert_utc_to_dt(utc_time)`
- `def drop_stale_tables()`
- `def get_alembic_version()`
- `def get_orc_status()`
- `def get_orchestrator()`
- `def get_previous_run_id()`
- `def str_to_dt(dt_str)`

**mule_analytics/get_events.py**

- `def retrieve_events()`

**mule_analytics/process_db.py**

- `def run()`

**mule_analytics/sw_history.py**

- `def get_build_info() → Dict`
- `def get_env_def(tag: str, val: str, log)`
- `def update_sw_history()`

**mule_comms/comms_orchestrator.py**

- `def check_if_redis_is_up(redis_url)`

**mule_comms/error_data_manager.py**

- `def handle_event_fatal_errors(ctx, msg)`
- `def main()`
- `def slice_error_data(err_info, error_data_duration)`
- `def update_error_data_to_fm(ctx, filename, file_path, incident_id)`

**mule_comms/fleet_bridge.py**

- `def connect_to_fm_ws(ctx, bus_reader)`
- `def fb_main()`

**mule_comms/fleet_bridge_utils.py**

- `def check_for_continuous_restarts(ctx)`
- `def check_readiness_of_mule(mule_mode, ctx)`
- `def compare_and_update_fleet_config(fleet_config, basic_fleet_info)`
- `def create_map_folder(map_name)`
- `def download_file(ctx, file_path_in_server, retry_after)`
- `def file_uploader(ctx)`
- `def get_all_async_tasks(ctx, ws, bus_reader)`
- `def get_app_context()`
- `def get_basic_info(ctx)`
- `def get_config()`
- `def get_file_hash_from_fm(ctx)`
- `def get_yelli_pose(ctx)`
- `def handle_map_change(map_name)`
- `def is_fm_server_up(ctx)`
- `def is_software_compatible(ctx)`
- `def process_msg_from_fm(ctx)`
- `def send_mule_message_to_fm(ctx)`
- `def send_mule_orc_down_msg(ctx)`
- `def send_request_to_fm(ctx, url, req_type, req_json, files, params, retry_after, response_type)`
- `def send_sherpa_status(ctx, bus_reader)`
- `def send_status_updates_on_zmq_bus_to_fm(ctx, bus_reader)`
- `def send_ws_ack(ctx, req, response, success)`
- `def sync_map_files(ctx, ws)`
- `def upload_config_files(ctx)`
- `def upload_file(ctx, files, params)`
- `def verify_fleet_files(ctx)`
- `def websocket_reader(ctx, ws)`
- `def websocket_writer(ctx, ws)`

**mule_comms/hmi_bridge/hmi_bridge.py**

- `def main()`

**mule_comms/hmi_bridge/hmi_bridge_utils.py**

- `def empty_queue(q: asyncio.Queue)`
- `def get_app_ctx()`
- `def get_mule_orc_down_msg(ctx)`
- `def hmi_to_mule_comms(ctx)`
- `def redis_channel_reader(ctx)`
- `def redis_channel_writer(ctx)`
- `def send_error_info(ctx)`
- `def send_network_stats(ctx)`
- `def send_sherpa_status(ctx, msg_reader)`
- `def send_updates(ctx, msg_reader)`

**mule_comms/hmi_bridge/hmi_modbus_client.py**

- `def main()`
- `def modbus_reader(aredis_conn, handler)`
- `def modbus_writer(aredis_conn, handler)`

**mule_comms/hmi_bridge/hmi_utils.py**

- `def shrink_message_type(message_type)`

**mule_comms/hmi_bridge/hmi_ws_server.py**

- `def handler(websocket)`
- `def ws_reader(websocket, aredis_conn)`
- `def ws_writer(websocket, aredis_conn)`

**mule_comms/hmi_bridge/run_all_tests.py**

- `def main()`
- `def run_test_file(test_file)`

**mule_comms/hmi_bridge/tests/test_hmi_bridge.py**

- `def run_all_tests()`
- `def run_async_tests()`

**mule_comms/hmi_bridge/tests/test_hmi_bridge_utils.py**

- `def run_all_tests()`
- `def run_async_tests()`

**mule_comms/hmi_bridge/tests/test_hmi_handler.py**

- `def run_all_tests()`

**mule_comms/hmi_bridge/tests/test_hmi_modbus_client.py**

- `def run_all_tests()`
- `def run_async_tests()`

**mule_comms/hmi_bridge/tests/test_hmi_models.py**

- `def run_all_tests()`

**mule_comms/hmi_bridge/tests/test_hmi_tcp_utils.py**

- `def run_all_tests()`

**mule_comms/hmi_bridge/tests/test_hmi_utils.py**

- `def run_all_tests()`
- `def shrink_message_type(message_type)`

**mule_comms/hmi_bridge/tests/test_hmi_ws_server.py**

- `def run_all_tests()`
- `def run_async_tests()`

**mule_comms/send_event_updates_to_fm.py**

- `def send_event_updates_on_zmq_bus_to_fm()`

**mule_comms/utils/comms.py**

- `def get_mule_orchestrator()`
- `def handle_200(url, response, response_type)`
- `def handle_401(url, req_json, retry_after)`
- `def handle_409(url, req_json, retry_after)`
- `def handle_422(url, req_json, retry_after)`
- `def restart_mule_docker()`
- `def send_req_to_mule_orc(orc, command)`
- `def send_request(url, req_type, req_json, proxy, headers, cert_file, total_timeout, response_type, auth, params, files, retry_after)`
- `def stop_mule_docker()`
- `def switch_mule_mode(orc, mode)`
- `def write_to_maintenance_fifo(fifo_msg)`

**mule_comms/utils/log_utils.py**

- `def add_handler(log_name: str, log_config: dict)`
- `def add_log_formatter(log_config)`
- `def add_logger(log_name: str, log_config: dict, propagate)`
- `def get_log_config_dict()`
- `def get_other_loggers()`

**mule_comms/utils/misc.py**

- `def delete_extra_map_files(valid_filenames, map_folder)`
- `def dict_to_dataclass(temp: dataclass, input_dict: dict)`
- `def get_battery_level(soc)`
- `def get_checksum(fname, fn)`
- `def get_network_stats()`
- `def should_download_file(file_name, server_file_checksum, map_folder)`
- `def verify_map_files(map_folder, files_info)`
- `def write_to_file(folder, file, content)`

**simulators/mule_simulator/control_messages.py**

- `def animate_mule_trajectory(latest_folder, map_dir, tracker_data, initial_start_station_name, initial_end_station_name, trip_id, start_pose, start_station, end_pose, end_station)`
- `def appending_to_text_file(f, statements, dataset)`
- `def disp_map(map_dir, xlim, ylim, title)`
- `def find_latest_run_folder(folder_path)`
- `def get_hitch_station_attribute(station)`
- `def get_orchestrator()`
- `def get_unpark_merge_attribute(station)`
- `def init()`
- `def load_station_poses(map_path)`
- `def main(argv)`
- `def mule_command_update(end_pose, end_station_name, sock, trip_id, trip_leg)`
- `def mule_kinematics(cx1)`
- `def mule_path(x_list, y_list)`
- `def plot_p(i)`
- `def post_mule_msg(sock)`
- `def process_stations_info(stations)`
- `def read_from_db(db, entry, default)`
- `def sensor_exception_update(world_state)`
- `def simulate_mule(cx1)`
- `def simulation_loop(tick_function, dt, time_warp)`
- `def tick(world_state, dt, mule)`
- `def trip_termination_check_and_drive_mule(latest_folder, map_dir, round_trip, f, initial_start_pose, initial_end_pose, initial_start_station_name, initial_end_station_name, start_pose, end_pose, start_station, end_station, cx1, yelli, drivable_region, stations_poses, stations_names, stations_tags, sock, world_state, dt, mule, trip_id, trip_leg, i, j)`

**simulators/mule_simulator/control_sim_utils.py**

- `def add_noise_randomly_to_yelli(yelli_pose, yelli_pose_prev)`
- `def animate_mule_trajectory(latest_folder, map_dir, tracker_data, trip_data)`
- `def appending_to_text_file(f, statements, dataset)`
- `def creating_run_summary(datasets_folder)`
- `def disp_map(map_dir, xlim, ylim, title)`
- `def exponential_smoothing(y, ys_prev)`
- `def find_latest_run_folder(folder_path)`
- `def get_axial_park_stations_attr(grid_map)`
- `def get_grid_map(map_path)`
- `def get_stations_attributes(grid_map)`
- `def get_stations_poses_from_gmaj(station_attr)`
- `def get_stations_poses_from_v2_wps(station_attr, map_path)`
- `def init()`
- `def load_station_poses(map_path, route_application)`
- `def mule_path(x_list, y_list)`
- `def plot_mule_trajectory(latest_folder, map_dir, tracker_data, trip_data)`
- `def plot_p(i)`
- `def read_from_db(db, entry, default)`

**simulators/mule_simulator/fm_control_sim.py**

- `def creating_and_starting_threads(world_state, initial_pose)`
- `def main(argv)`
- `def mule_kinematics(cx1)`
- `def post_mule_indicator_msg(sock)`
- `def simulate_mule(cx1)`
- `def simulating_control_module(f, latest_folder, map_dir, initial_pose, stations_data, yelli, drivable_region, sensor_status, stoppages_message_status, threads, dt, world_state, sock, current_folder)`
- `def tick(world_state, dt, mule)`
- `def trip_termination_check_and_drive_mule(latest_folder, current_folder, map_dir, f, trip_data, cx1, yelli, drivable_region, stations_data, sock, world_state, dt, mule, last_trip_id, last_trip_leg_id)`
- `def updating_yelli_and_drivable_region_pose(yelli, drivable_region, mule)`

**simulators/mule_simulator/simulation_peripherals.py**

- `def main(argv)`
- `def post_lift_msg(sock, lift)`
- `def post_mule_dispatch_msg(sock, dispatch_timeout)`
- `def post_mule_hitch_msg(sock, hitch)`
- `def send_lift_confirmation_msg(sock, lift)`
- `def send_payload_pose(sock)`

**tools/BT_open_smart_door.py**

- `def connect_to_remote()`
- `def import_smart_door_zones()`
- `def is_odometry_valid(odo_obj)`
- `def main(argv) → Any`
- `def mule_nearby_smart_door(mule_pose, smart_door_zones)`
- `def send_open_door_msg(BT)`

**tools/camera_data_recorder.py**

- `def extract_move_to_timestamps(log_path)`
- `def process_dataset(dataset)`

**tools/open_smart_door.py**

- `def connect_to_serial_device(port)`
- `def import_smart_door_zones()`
- `def is_odometry_valid(odo_obj)`
- `def main(argv) → Any`
- `def mule_nearby_smart_door(mule_pose, smart_door_zones)`
- `def send_open_door_msg(serial_comms_obj, port)`

**tools/plot_lidar_frame.py**

- `def do_print(text)`
- `def plot_frame(datadir, frame_id, min_dist, zero_char, near_char, min_points, max_points, show, skip)`
- `def range_to_text(r)`

**tools/python_receiver/CAN_Parsing.py**

- `def makeByteArray(number, numBytes)`

**tools/python_receiver/CANmonitor.py**

- `def create_live_table(height, tableTitle) → Table`
- `def dataToHex(data)`
- `def dictToStr(d)`
- `def main()`
- `def makeLayout() → Layout`
- `def processMsg(msg: can.Message)`
- `def receive(bus, stop_event)`
- `def updateInterval(id, t)`
- `def updateLayout(layout, footerData) → Layout`

**tools/slice_data.py**

- `def copy(file_num, pos1, pos2, path, tempdir, lidar_id)`
- `def copy_critical_files(path, tempdir)`
- `def copy_file(path, tempdir, file_name)`
- `def copy_tail(path, tempdir, file_name, nlines)`
- `def dump_critical_data(run_path, temp_dir, nframes)`
- `def dump_error_data(err_info, last_n_secs, frames)`
- `def dump_tar_file(tar_file)`
- `def extract_camera_data(dir_path, frames, tempdir)`
- `def extract_csv_data(path, frames, tempdir)`
- `def extract_drivable_data(path, frames, tempdir)`
- `def extract_lidar_data(path, frames, tempdir)`
- `def extract_pb_data(pb_file, index_file, output_file, new_index_file, frames, tempdir)`
- `def extract_policy_data(path, frames, tempdir)`
- `def extract_toml(path, tempdir)`
- `def get_data(run_path, temp_dir, nframes, end_frame)`
- `def get_data_internal(run_path, temp_dir, nframes, end_frame, remove_temp_dir)`
- `def get_frame_pos(lidar_index, n)`
- `def get_frame_pos_next(lidar_index, n1, n2, is_last)`
- `def get_last_frame_id()`
- `def get_last_n_sec_frame_id(run_dir, n_sec)`
- `def get_lidar_file_size(path, file_num)`
- `def get_lidar_frame_pos(lidar_index, n)`
- `def get_lidar_timestamp(frame_index, nlidar)`
- `def get_lidar_type()`
- `def is_livox()`
- `def load_lidar_index(path)`
- `def make_tarfile(output_filename, source_dir)`
- `def makedir(slice_dir)`
- `def slice_csv(file, run_dir, output_folder, frames)`
- `def slice_log(file, run_dir, output_folder, frames)`
- `def slice_toml_json(file, run_dir, output_folder, frames)`

**tools/update_camera_firmware.py**

- `def update_realsense_firmware(firmware_file_path)`

**utils/assess_map.py**

- `def assess_map(map_name, data_dir, start_frame, max_frames, correct_roll_pitch, voxel_size, debug)`
- `def get_v_w(summary, frame_id)`
- `def moved_adequately(prev_pose, curr_pose)`
- `def norm_theta_diff(pose_err)`
- `def perturb_pose(pose)`
- `def plot_map(grid_map, alpha)`

**utils/auto_submap_update.py**

- `def auto_update_map(data_dir, cur_map_dir, output_dir, start_frame, end_frame)`
- `def combine_maps(multimaps, alpha)`
- `def compute_mask_beams(beams)`
- `def compute_submap(data_dir, beams, start_frame, end_frame)`
- `def get_min_map_size(multimaps)`
- `def load_data(dir_path)`
- `def merge_submap(multimap, submap, submap_mask)`
- `def plot_map(grid_map, alpha)`
- `def plotline(x0, y0, x1, y1, step, show, nclear)`
- `def plotline_high(x0, y0, x1, y1)`
- `def plotline_low(x0, y0, x1, y1)`
- `def prune_and_align(multimaps)`

**utils/control_utils.py**

- `def are_poses_close(pose1, pose2, dist_thresh, theta_thresh) → bool`
- `def batch_compute_score(history, new_measurements, old_score)`
- `def calculate_steering_angle(v, omega)`
- `def check_for_special_station_tags(station_tags, station_pose)`
- `def check_zone_orientation(zone_theta, mule_theta)`
- `def compute_score(history, new_measurement, old_score)`
- `def conv_secs_to_window_length(window_length, batch_interval_time)`
- `def debug_log(log_text, log_flag)`
- `def det(z1: np.ndarray, z2: np.ndarray) → float`
- `def direction_vector(ang)`
- `def extend_path(path)`
- `def extract_pose(msg: OdometryUpdate) → Union[...]`
- `def find_closest_pt_fast(xref: np.ndarray, yref: np.ndarray, pose_xy: np.ndarray) → int`
- `def find_distance(position1, position2)`
- `def find_distances_fast(turn: List, i: int, P_index: bool, traj_length: int) → List`
- `def get_all_zones()`
- `def get_angle(init_theta, ref)`
- `def get_control_message(control_status)`
- `def get_factored_vel(mule_pose, zones, velocity)`
- `def get_gradient_profile(ramp_zones: dict, current_pose: np.ndarray) → int`
- `def get_intersecting_zones(zones, ref_path)`
- `def get_local_path(ref1, ref_start_pose, start, res)`
- `def get_min_vel_factor(mule_pose, zones)`
- `def get_next_angle(pose_xy, zref)`
- `def get_process_time(t)`
- `def get_route_type_update_message(lift_status, route_type)`
- `def get_vel_factored_zones()`
- `def get_zone_specific_padding(mule_pose, zones, lifter_sensor_status)`
- `def get_zone_specific_stop_dist(mule_pose, zones)`
- `def import_regime_info(control_regime)`
- `def in_avoidance_zone(mule_pose, zones)`
- `def in_avoidance_zones(mule_pose, zones, zone_rects)`
- `def in_table_pickup_zone(mule_pose, zones)`
- `def inside_vel_factored_zone(mule_pose, zones)`
- `def intersect(pose_xy, theta, bed_pose)`
- `def is_inside_zone(mule_pose, rect_ob)`
- `def is_mule_path_and_zone_intersecting(path, zone, ignore_if_mule_inside)`
- `def load_value(db, field_name)`
- `def log_utils(DEBUG_LOG_FLAG)`
- `def mule_message(mule_status)`
- `def normalize(theta)`
- `def offset_path(path, offset)`
- `def predict_trajectory_fast(ref_trajectory: np.ndarray, start_pose: np.ndarray, forward: bool, P_index: bool) → np.ndarray`
- `def predict_trajectory_numba(ref_trajectory: np.ndarray, start_pose: np.ndarray, forward: bool, P_index: bool) → np.ndarray`
- `def rotation_matrix(theta)`
- `def run_tan_tracker_prediction(current_pose, ref_trajectory, cte, traj_length, forward, index, path, P_index)`
- `def save_value(db, field_name, index)`
- `def simul(z1, z2, b)`
- `def simulate_mule(actual_pose, v, w, dt)`
- `def smoothen(arr, win_size)`
- `def transform_local_to_world(x, y, theta, points)`
- `def transform_world_to_local(x, y, theta, points)`
- `def update_histories(history, new_scores)`
- `def update_history(history, new_score)`

**utils/create_tables.py**

- `def create_tables()`
- `def drop_tables()`
- `def update_sw_history(TAGNAME)`

**utils/generate_web_map.py**

- `def check_if_tiled_map(map_folder)`
- `def generate_map(map_folder, showposes, transparent)`
- `def load_tiled_map(map_folder, poses, update_poses, pad)`

**utils/geometry_utils.py**

- `def _compute_length_asymmetric_rectangle(pivot_pt, pivot_direction, length_front, length_rear, half_width)`
- `def _compute_symmetric_rectangle(pivot_pt, pivot_direction, half_length, half_width)`
- `def _find_intersection_pt(p1, q1, p2, q2)`
- `def _get_det(v0, v1, v2)`
- `def _is_inside_triangle(v0, v1, v2, p)`
- `def _is_intersecting_at_point(p1, q1, p2, q2)`
- `def _is_on_segment(p, q, r)`
- `def _make_triangle_ccw(v1, v2)`
- `def _process_triangle(v0, v1, v2)`
- `def _which_orientation(p, q, r)`
- `def angle(z)`
- `def angle_between_three_pts(p1, p2, p3)`
- `def angle_between_vectors(vec1, vec2)`
- `def angle_of_direction_vector(direction_vector)`
- `def are_lines_aligned(line1, line2, atol)`
- `def are_parallel_lines(line1, line2, atol)`
- `def calc_unit_vector(v)`
- `def calc_unit_vector_fast(v)`
- `def debug_log(log_text)`
- `def det(z1, z2)`
- `def direction_vector(ang)`
- `def direction_vector_btw_points(p1, p2)`
- `def distance_btw_two_pts(p1, p2)`
- `def fit_line(poses, p, q)`
- `def fit_path_mpc(current_pose, path)`
- `def fit_poly_path(py, px)`
- `def generate_smooth_path(wps, r)`
- `def get_path_curvature(xp, yp, signed)`
- `def get_points_at_dist_from_a_point_along_slope(point, slope, dist)`
- `def get_polygon_edges_from_vertices(vertices)`
- `def is_inside_polygon(r0, r1, r2, r3, p)`
- `def is_inside_rectangle(r0, r1, r2, r3, p)`
- `def is_pt_on_line_seg(pt, p1, p2, dist_tol)`
- `def length(z)`
- `def normalize_angle(ang)`
- `def point_projection_on_line_seg(pt, p1, p2)`
- `def point_to_line_seg_distance(pt, p1, p2)`
- `def polygon_edges_from_vertices(vertices)`
- `def rotate(p, q, theta)`
- `def rotate_line(line_direction, rot_ang)`
- `def rotation_matrix(theta)`
- `def round_numba(x)`
- `def simul(z1, z2, b)`
- `def transform_local_to_world(x, y, theta, points)`
- `def transform_world_to_local(x, y, theta, points)`
- `def yaw_angle_between_two_pts(p1, p2)`

**utils/get_lanes_on_map.py**

- `def circular_sub(angle_1, angle_2)`
- `def fit_ransac_reg(X, y, min_samples, residual_threshold, random_state)`
- `def generate_lanes_on_map(root_dir, map_name)`
- `def get_inlier_index(inlier_mask)`
- `def get_lane_stretch(lane_left_global_uniq, lane_right_global_uniq, lane_left_global_uniq_indices, lane_right_global_uniq_indices, slam_transform_lane)`
- `def get_unique_lanes(lane_left_global, lane_right_global)`
- `def save_map_lanes(lane_stretches_global, num_stretches, map_name)`
- `def transform_lane_pose_to_global_coord(df_lane_pose, df_slam_pose)`
- `def transform_point_2d(transform2d, point2d)`

**utils/get_lidar_offset_from_map.py**

- `def get_lidar_angle_offset(map_folder)`

**utils/get_realsense_info.py**

- `def get_realsense_config(device_serial_num, width, height, fps)`
- `def get_realsense_device_list()`
- `def main()`

**utils/get_rear_enc_lidar_angle_offset_from_map.py**

- `def fit_circle(pts)`
- `def get_enc_offset(map_folder, rear_std_dev_threshold)`

**utils/grid_mappingv1.py**

- `def score_function_fast(grid, z_grid, grid_origin, pose, frame)`
- `def search_cuda(grid, z_grid, nx, ny, ox, oy, poses, frame)`
- `def search_fast(grid, z_grid, grid_origin, poses, frame)`

**utils/handle_errors.py**

- `def _get_error_code(err_dict: Dict) → Dict`
- `def _get_unique_id(config: Dict, err_key: str)`
- `def cancel_threads(err_key: str)`
- `def handle_error(err_key, module, extra_info: dict, err_msg, run_folder)`
- `def write_to_errors_csv(module, err_key)`

**utils/lidar_pb2small.py**

- `def main(pb_file, frames)`
- `def read_frame_small(f)`
- `def read_frames_pb(file_name)`
- `def read_frames_small(file_name)`
- `def read_packet_pb(f)`
- `def write_frames(file_name, frames)`

**utils/live_map_gen.py**

- `def build_map(data_iter)`
- `def exit_handler(sig, frame)`
- `def get_cupy_mempool()`
- `def imu_pose_estimate(imu_tracker, time, pose)`
- `def main(args)`
- `def map_quality(grid_val, threshold)`
- `def plot_and_save_map(multimap, poses, map_name)`
- `def plot_map(grid_map, alpha)`
- `def preprocess_frame(frame, multimap, voxel_size, lidar_ht, correct_roll_pitch, roll, pitch)`
- `def read_data(sock)`
- `def select_best_pose(pose, scores)`

**utils/localize.py**

- `def cone_filter(frame, cone_angle, azimuth_range)`
- `def euler_to_quaternion(phi, theta, psi)`
- `def imu_pose_estimate(imu_tracker, time, pose)`
- `def load_data(dir_path)`
- `def localize_on_map(data_dir, map_name, localization_name)`
- `def plot_map(grid_map)`
- `def save_poses_to_6dof(frame_times, poses, outfile)`
- `def select_best_pose(pose, scores)`

**utils/log_utils.py**

- `def add_handler(log_name: str, log_config: dict)`
- `def add_log_formatter(log_config)`
- `def add_logger(log_name: str, log_config: dict, log_level, propagate)`
- `def add_stream_handler(log_name, log_config: dict)`
- `def get_log_config(all_logggers, log_level)`
- `def get_log_config_dict(all_logggers, log_level)`
- `def log_every_nsec(msg, nsec, log_name, level)`
- `def set_log_propogation(log_config, log_name, propagate)`
- `def set_root_logger_handler(log_config, logger_name)`

**utils/make_lidar_video.py**

- `def get_frames()`
- `def get_grid_lines(zoom)`
- `def get_mule_pts()`
- `def rotate(frame)`

**utils/map_creation_tools/create_map_api.py**

- `def add_spherical_coordinates(frame)`
- `def build_map(multimap, data_dir, tilt, correct_roll_pitch, correct_ego_motion, start_frame, max_frames, gyro_var_threshold, use_imu, skip, use_wheel_motion_check, posegraph_opt, mapping_config, tiled_map)`
- `def compute_imu_tracker_bias(data_dir, gyro_var_threshold)`
- `def compute_imu_trackers(data_dir, imu_tracker, frame_times)`
- `def compute_is_moving_check_and_pose(data_dir, frame_times)`
- `def convert_wheel_odo_delta_to_lidar_delta(wpose, lidar_y_offset)`
- `def dummy_yield()`
- `def filter_by_slope(frame, lidar_ht, slope_threshold)`
- `def filter_frame(frame, frame_id, zmin, zmax, max_dist, min_dist)`
- `def filter_frames(frames, voxel_size, zmin, zmax, max_dist, min_dist, slope_filter, roof_filter, slope_threshold, voxel_sampling, voxel_sampling_res)`
- `def filter_roi(pose, frame, rois)`
- `def get_frame(self, frame_id)`
- `def get_num_frames(data_dir)`
- `def get_v_w(summary, frame_id)`
- `def get_wheel_enc_prediction(vs, ws, dt)`
- `def get_wheel_pose_prob(poses, wpose, std_dev_x, std_dev_y, std_dev_t)`
- `def imu_pose_estimate(imu_tracker, time, pose)`
- `def load_imu_data(dir_path)`
- `def load_lidar(data_dir, start_frame, max_frames, skip, correct_roll_pitch, correct_ego_motion)`
- `def load_lidar_times(data_dir, start_frame, max_frames, skip)`
- `def load_summary_data(dir_path)`
- `def load_wheel_enc_data(dir_path)`
- `def map_from_poses(multimap, poses, frame_ids, data_dir, map_grid_res, map_creation_config, tiled_map, yield_progress)`
- `def num_frames(self)`
- `def open_lidar_data(data_dir)`
- `def optimize_map(submap_manager, map_dir, data_dir, map_creation_config, yield_progress)`
- `def preprocess_frames(frames, voxel_size, multimap, slope_filter, roof_filter, slope_threshold, voxel_sampling, voxel_sampling_res)`
- `def rounded_discrete_gaussian(x, mean, std)`
- `def scan_degenerate(fr)`
- `def select_best_pose(pose, scores)`
- `def update_map(multimap, poses, frame_ids, data_dir, rois)`
- `def voxel_filter2d(frame, voxel_size)`

**utils/map_creation_tools/create_map_cli.py**

- `def create_logger(map_dir)`
- `def create_map(data_dir, map_name, max_frames, start_frame, zmin, zmax, tilt, pruned, correct_roll_pitch, correct_ego_motion, debug, gyro_var_threshold, use_imu, skip_frames_step, use_cuda, use_wheel_motion_check, log2file, map_grid_res, submap_grid_resolution, level_lookup_type, assess, search_neighbours, max_dist, min_dist, posegraph_opt, slope_filter, roof_filter, slope_threshold, map_padding, transparent, use_wheel_pose_search_prob, voxel_sampling, voxel_sampling_res, degeneracy_check, tiled_map, tile_size, num_buffer_tiles, loop_closed, only_optimize_start_end_poses, deployment_manager)`
- `def generate_map_metadata(run_dir, map_creation_config)`
- `def get_prune_limits(grid_map, poses, map_padding)`
- `def get_redis_db(config)`
- `def map_quality(grid_val, threshold)`
- `def plot_and_save_map(multimap, poses, map_name, debug)`
- `def plot_and_save_tiled_map(multimap, poses, pad, map_name)`
- `def plot_constraints(poses, constraints, map_name)`
- `def plot_map(grid_map, alpha)`
- `def plot_tiled_map(multimap, poses, pad, ax)`
- `def post_process_map_data(multimap, map_name, data_dir, poses, frame_list, map_creation_config, tiled_map, transparent, debug, log2file)`
- `def prune_map(built_map, xlim, ylim, debug)`
- `def write_progress_to_redis_db(redis_db, build_stage: str, progress: float)`

**utils/map_creation_tools/create_map_from_fleet_run.py**

- `def extract_map_from_fleet_run(csv_path, start_frame, end_frame, sample_distance, return_threshold, travel_distance, stop_at_start)`
- `def generate_map_from_fleet(map_name, data_dir, zmin, zmax, map_grid_res, max_dist, min_dist, pruned, debug, slope_filter, slope_threshold, map_padding, start_frame, end_frame, tiled_map, tile_size, num_buffer_tiles, sample_distance, stop_at_start)`
- `def generate_webui_map(map_folder)`
- `def regenerate_webui_map(old_map_folder, new_map_folder)`

**utils/map_creation_tools/create_map_from_submap.py**

- `def get_prev_map_config(map_dir)`
- `def is_valid_dir(map_dir)`
- `def optimize_submaps(map_dir, data_dir, new_map_dir, use_prev_config, zmin, zmax, pruned, debug, log2file, map_grid_res, submap_grid_resolution, max_dist, min_dist, slope_filter, slope_threshold, map_padding, transparent, loop_closed, only_optimize_start_end_poses, voxel_sampling, voxel_sampling_res, level_lookup_type)`

**utils/map_creation_tools/deployment_manager_create_map.py**

- `def main()`

**utils/map_creation_tools/extend_map.py**

- `def generate_webui_map(map_folder)`
- `def get_constraints(mmap, static_poses, search_poses, search_frame_ids, lpb, search_config)`
- `def get_corresponding_map_poses(original_mmap, original_map_folder, insertion_map_folder, insertion_data_folder, transform, insertion_config)`
- `def get_frame(self, frame_id)`
- `def get_insertion_constraints(insertion_constraint_path)`
- `def get_optimised_poses(insertion_poses, constraints, constraint_wt, pose_wt)`
- `def get_run_dir_from_map_dir(map_dir)`
- `def merge_maps(original_map, insertion_map, insertion_data_dir, updated_map, candidate_selection_radius, transform, use_cuda, debug, slope_filter)`
- `def num_frames(self)`
- `def plot_and_save_map(multimap, map_folder, constraints, debug)`
- `def regenerate_webui_map(old_map_folder, new_map_folder)`
- `def save_constraints(constraints, updated_map_folder, update_id)`
- `def save_updated_map(updated_mmap, updated_map_folder, original_map_folder, insertion_data_dir, poses, frame_ids, roi, constraints, action_type, update_zslice)`

**utils/map_creation_tools/generate_lower_res_map.py**

- `def generate_lower_res_map(original_map_folder, new_map_folder, lower_res_ind)`

**utils/map_creation_tools/generate_new_map_from_old_map.py**

- `def generate_new_map(original_map, new_map, data_dir, zmin, zmax, map_grid_res, max_dist, min_dist, pruned, debug, slope_filter, slope_threshold, map_padding, start_frame, end_frame, tiled_map, tile_size, num_buffer_tiles)`
- `def generate_webui_map(map_folder)`
- `def get_update_data(map_dir)`
- `def get_update_map_data(map_dir)`
- `def is_updated_map_folder(map_dir)`
- `def regenerate_webui_map(old_map_folder, new_map_folder)`

**utils/map_creation_tools/generate_tiled_map.py**

- `def generate_tiled_map(original_map, new_tiled_map, tile_size)`

**utils/map_creation_tools/imu_slope.py**

- `def get_bias_free_gyro(gyro_raw, acc_raw)`
- `def get_cluster_box(pts, padding)`
- `def get_initial_acc_quaternion(acc, ideal_gravity_vec)`
- `def get_initial_quaternion_from_acc_yelli(initial_acc, theta, ideal_gravity_vec, ideal_yelli_vec)`
- `def get_poses_from_map(map_name, data_dir)`
- `def get_slope(map_name, data_dir, only_acc, zero_initial_acc_angle, slope_threshold, min_slope_length_threshold, padding, map_features_dest_dir)`
- `def moving_average(data, window_size)`

**utils/map_creation_tools/map_change_detection.py**

- `def bloat_mask_grid_2pow(grid, bloat_factor)`
- `def check_if_path_exists(folder, folder_var_name)`
- `def convert_grid2D_to_binary_image(grid2d, threshold)`
- `def decimate_grids(original_grid, hit_grid, miss_grid, decimation_level)`
- `def generate_new_hit_miss_grid(original_multigrid, fleet_run_map, dataset, poses, frame_ids)`
- `def get_common_cells(binary_img0, binary_img1)`
- `def get_extents_from_grid2d(grid2d)`
- `def get_map_change(original_hit_mask, new_mask, miss_mask, no_change_mask)`
- `def get_min_max_extents_from_poses(poses, pad)`
- `def get_no_change_mask(no_change_zones, grid_shape, grid_origin, grid_res)`
- `def get_poses_and_frame_ids(map_folder)`
- `def get_run_dir_from_map(map_folder)`
- `def get_zslice_from_map(map_folder)`
- `def map_change_stats(common_occupied_mask, new_occupied_mask, old_occupied_to_remove_mask, decimated_grid_res, map_change_folder, map_extents)`
- `def plot_and_save_binary_masks(new_occupied_mask, common_occupied_mask, old_occupied_to_clear_mask, change_stats, change_folder, map_extents, poses, pad)`
- `def plot_and_save_original_and_new_binary_masks(original_hit_mask, common_occupied_mask, new_occupied_mask, old_occupied_to_remove_mask, map_extents, poses, change_folder, pad)`
- `def plot_and_save_original_vs_updated_map(original_mmap, updated_mmap, poses, save_folder, pad)`
- `def save_map_change_info(new_miss_grid, new_hit_grid, common_occupied_mask, new_occupied_mask, remove_mask, original_hit_mask, change_stats, decimation_level, map_extents, poses, dataset, map_change_dir)`
- `def update_map(original_map, fleet_run_map, fleet_dataset, new_map, decimation_level, min_hit_threshold, min_miss_threshold)`
- `def update_map_from_binary_masks(original_multigrid, new_hit_grid, common_occupied_mask, new_occupied_mask, old_occupied_to_remove_mask, decimation_level)`

**utils/map_creation_tools/map_edit_functions.py**

- `def box_selection_callback(attr, old, new, roi_select, select_button)`
- `def checkbox_callback(multi_data_optim, label)`
- `def crop_actual_map(mmap, x, y, width, height)`
- `def crop_display_map(display_map_source, x, y, width, height)`
- `def folder_input_callback(folder_input)`
- `def generate_new_map(plot, roi_map_edit_source, new_map_folder_ip, new_map_name_ip, insertion_map_ip, data_dir_ip, data_dir_ip_2, inputx, inputy, inputt, input_zminmax, multi_data_optim)`
- `def get_dataset_from_map(map_dir)`
- `def get_display_map(gmap, disp_pix_size)`
- `def get_finished_data_dirs(map_dirs)`
- `def get_finished_frame_ids(map_dir)`
- `def get_finished_submaps(map_dirs: list)`
- `def get_ip_addr()`
- `def get_node_frames(map_dir)`
- `def get_node_poses(map_dir)`
- `def get_plot_ranges(dw, dh, originx, originy)`
- `def get_run_from_metadata(map_folder)`
- `def get_zmin_zmax(map_folder)`
- `def is_valid_data_folder(data_folder)`
- `def is_valid_map_folder(map_folder)`
- `def list_dir(ip_text, completions)`
- `def load_finished_submap(map_dir)`
- `def load_insertion_frame_id(map_dir)`
- `def load_insertion_map_callback(map_folder_ip, plot, poses_source, map_source, data_dir_ip, inputx, inputy, inputt, prev_transform)`
- `def load_map(map_folder)`
- `def load_map_callback(map_folder_ip, plot, poses_source, map_source, roi_map_edit_source, raw_map_data, input_zminmax, data_dir_ip)`
- `def load_poses(map_folder)`
- `def map_from_poses_multi(opt_poses, submap_manager, data_dirs, node_id_map, map_creation_config)`
- `def merge_map_wrapper(map_dirs, data_dirs, updated_map, transforms, zslice, plot)`
- `def remove_roi(grid, originx, originy, dw, dh, roi, grid_reset_value)`
- `def remove_roi_from_actual_map(mmap, x, y, width, height)`
- `def remove_roi_from_display_map(display_map_source, x, y, width, height)`
- `def reset_zoom(plot, map_source, raw_map_data)`
- `def roi_action(select_button, display_map_source, selection_source, roi_map_edit_source, raw_map_data, plot)`
- `def toggle_map_visibility(show_map_check, map_img0, insertion_map_imgs, poses0, insertion_poses)`
- `def transform2d_pixel_map(transform, grid, originx, originy, dw, dh, grid_start_value)`
- `def transform_display_insertion_map(plot, poses_source, map_source, inputx, inputy, inputt, prev_transform)`
- `def transform_submaps(mmap, transforms)`
- `def use_cuda()`
- `def zoom(display_map_source, raw_map_data, plot, x, y, width, height)`

**utils/map_creation_tools/map_zones.py**

- `def draw_zones(zone_source, rects, roi_type)`
- `def roi_action(select_button, display_map_source, selection_source, roi_map_edit_source, raw_map_data, plot, display_zone_source)`
- `def rotate_rect_callback(attr, new, selection_source, rect_id_source)`
- `def selection_source_callback(attr, old, new, selection_source, rect_angle_slider, rect_id_source)`
- `def write_to_file(plot, write_folder_ip, roi_map_edit_source)`

**utils/map_creation_tools/merge_maps.py**

- `def get_merged_graph_constraints(finished_submaps, nid_map, sid_map, unopt_poses, insertion_fr_ids, lidar_pbs, opt_score_threshold, level0_config)`
- `def merge_maps(map_dirs, transforms, data_dirs, updated_map, dist_th, score_th, x_search_window, y_search_window, angle_search_window, num_temp_constraints, use_simple_posegraph, skip_consecutive_node_dist, hierarchical_grid_num_levels, use_cuda, debug, pruned)`
- `def parse_transforms(ctx, param, value)`
- `def tuple_to_list(ctx, param, value)`

**utils/map_creation_tools/merge_utils.py**

- `def check_dirs(dirs)`
- `def dump_merged_meta(updated_map_dir, multimap, insertion_data_dirs, poses, frame_ids, constraints, update_zslice, action_type, roi)`
- `def generate_merged_map_metadata(run_dirs)`
- `def get_dataset_from_map(map_dir)`
- `def good_input(map_dirs: list, transforms: list)`
- `def load_best_scores(map_dir)`
- `def load_finished_submap(map_dir)`
- `def load_insertion_frame_id(map_dir)`
- `def load_node_poses(map_dir)`
- `def return_transforms(map_dirs)`

**utils/map_creation_tools/mock_dm_command.py**

- `def main(argv)`

**utils/map_creation_tools/prune_map.py**

- `def crop_map(map_folder, pruned_map_folder, map_padding)`
- `def plot_and_save_map(multimap, all_poses, map_name)`

**utils/map_creation_tools/regen_map.py**

- `def AutocompleteInput_callback(tio)`
- `def button_callback(tio, img_source, poses_source)`
- `def display_map(map_folder, img_source, poses_source)`
- `def load_map(map_folder)`
- `def load_map_meta(map_folder)`
- `def load_yelli_meta(map_folder)`
- `def new_map_callback(map_name_ip, tio)`

**utils/mule_utils.py**

- `def connect_to_serial_bus(port: int, baudrate, bytesize, timeout, period)`
- `def create_new_folder(folder: str)`
- `def get_build_info() → Dict`
- `def get_current_pose(odo_obj)`
- `def get_env_def(tag: str, val: str, log)`
- `def get_run_distance(run_folder: str) → float`
- `def opener_644(path, flags)`
- `def read_dict_var_from_redis_db(redis_db: redis.Redis, entry: str) → Dict`
- `def read_from_db(redis_db: redis.Redis, entry: str, default) → Any`
- `def read_list_var_from_redis_db(redis_db: redis.Redis, entry: str) → List`
- `def send_control_exception(sock, device_name, timeout)`
- `def send_control_pause_command(command)`
- `def write_mmts_req_fifo(fifo_msg)`

**utils/ouster_set_static_ip.py**

- `def main()`
- `def ouster_set_ip(ouster_id, static_ip)`
- `def ouster_verify_ip(ouster_id)`

**utils/pallet_mover_hydraulics_test.py**

- `def main(argv)`

**utils/perception/send_payload_detect_msg.py**

- `def publish_control_status(sock, status)`

**utils/plot_csv.py**

- `def fix_outliers(data, tol)`
- `def make_scale(scale, s1, s2)`
- `def make_smooth(data, n)`
- `def plot(i)`
- `def print_scale(start, end, ncols, hscale, values)`

**utils/posegraph_map/create_graph_map.py**

- `def build_map(data_dir, map_dir, max_frames, start_frame, pruned, tilt)`
- `def check_vehicle_motion(wheel_enc)`
- `def get_grid_params(grid_params, grid_res)`
- `def imu_pose_estimate(imu_tracker, time, pose)`
- `def transform_remaining_poses(unopt_pose, opt_pose, poses)`

**utils/posegraph_map/generate_constraints_and_optimize.py**

- `def generate_constraints_and_optimize(map_dir, data_dir)`
- `def transform_remaining_poses(unopt_pose, opt_pose, poses)`

**utils/posegraph_map/generate_map.py**

- `def generate_map(zmin, zmax, data_dir, map_dir, tilt, pruned)`
- `def generate_map_metadata(run_dir, tilt)`
- `def get_prune_limits(grid_map, poses)`
- `def plot_map(grid_map, alpha)`
- `def prune_map(built_map, xlim, ylim)`

**utils/posegraph_map/grid.py**

- `def odds(probability)`
- `def prob_from_odds(odds_val)`
- `def score_function(grid, grid_origin, pose, frame, grid_res)`
- `def score_function_count_once(grid, grid_origin, pose, frame, grid_res, level_mapping)`
- `def search_fast_count_once(grid, grid_origin, poses, frame, grid_res, level_mapping)`
- `def search_fastv2(grid, grid_origin, poses, frame, grid_res)`

**utils/posegraph_map/hierarchical_grid.py**

- `def compute_half_res_grid(half_res_grid, full_res_grid)`
- `def compute_hierarchical_grid(grid2d, num_levels)`
- `def generate_hierarchical_search_spaces(grid_res_arr, x_search_window, y_search_window, angle_search_window, max_range)`
- `def generate_local_grid_search_space(x, y, theta, num_x, num_y, num_t)`
- `def generate_local_search_space(grid_res, x_search_window, y_search_window, angle_search_window, max_range)`
- `def hierarchical_search_v2(hgrids, pose_estimate, frame, x_search_window, y_search_window, angle_search_window, max_range, score_th, debug)`
- `def transform_grid_search_space(center, search_space)`

**utils/posegraph_map/misc_utils.py**

- `def check_lidar_quadrants(frame, pts_th)`
- `def combine_yelli_poses(p1, p2)`
- `def get_2D_rotation_mat(theta)`
- `def get_angle_from_2D_rotation_mat(R)`
- `def get_inverse_yelli_pose(pose)`
- `def get_inverse_yelli_rotation(theta)`
- `def get_inverse_yelli_transform(pose)`
- `def get_yelli_rotation(theta)`
- `def get_yelli_transform(pose)`
- `def imu_submap_pose_estimate(imu_tracker, time, submap_pose, pose)`
- `def normalize_pose(theta)`

**utils/posegraph_map/posegraph.py**

- `def do_pose_graph_optimization(poses, constraints, submaps, use_simple_posegraph)`

**utils/ps4_utils.py**

- `def all_ok(controller)`
- `def assisted_manual(controller)`
- `def auto_unhitch_on_request(square, pub_sock)`
- `def check_key_from_ps4(key, ps4_controller)`
- `def check_key_match(report, key_from_ps4)`
- `def compute_control_commands(report)`
- `def connect_with_ps4(scanner, pub_sock)`
- `def convert_ps4_report_to_json(report)`
- `def find_adapter()`
- `def flash_ps4_led(sock, odometry, obs_policy, is_slowing)`
- `def flash_red(controller)`
- `def generate_ps4_key()`
- `def get_lift_msg(lift_signal)`
- `def get_obs_factored_velocity(safety_policy: SafetyPolicy, linear_velocity: float, angular_velocity: float)`
- `def get_socks()`
- `def get_unique_ps4_key(keys)`
- `def give_haptic_feedback(ps4_controller, json_report, pub_sock, small, big)`
- `def log_ps4_battery(report, last_log_time)`
- `def log_ps4_commands(data_logger, time_delay, linear_velocity, angular_velocity, command_velocity, pub_diff)`
- `def log_ps4_report(topic, msg, last_log_time)`
- `def maybe_log_latency_msg(last_report)`
- `def ps4_id_check(device_address)`
- `def publish_ps4_commands(drive_update, lift_msg, sock)`
- `def publish_ps4_connection(status, pub_sock, ps4_id, ps4_key_check)`
- `def publish_ps4_report(report, pub_sock, status, ps4_id, pub_diff)`
- `def run_key_confirmation(ps4_controller)`
- `def set_ps4_key_in_redis(value, key)`
- `def slow_down_flash(controller)`
- `def turn_off_indicator(controller)`
- `def update_ps4_led_state(ps4, ps4_controller)`

**utils/ps5_utils.py**

- `def _compute_trigger_force(val: int, min_force: int, max_force: int) → int`
- `def _haptic_run(dualsense, left: int, right: int, dur_ms: int)`
- `def all_ok(controller)`
- `def apply_mode(trigger, value: int)`
- `def assisted_manual(controller)`
- `def connect_with_ps5(pub_sock, ps5_id)`
- `def flash_red(controller)`
- `def haptic_connected(dualsense)`
- `def haptic_for_state(ref: int, dualsense)`
- `def haptic_quick(dualsense, left: int, right: int, dur_ms: int)`
- `def log_ps5_battery(report, last_log_time)`
- `def log_ps5_report(report)`
- `def map_to_byte(v)`
- `def maybe_log_latency_msg(last_report)`
- `def publish_ps5_connection(status, pub_sock, ps5_id)`
- `def publish_ps5_report(report, pub_sock, status, ps5_id)`
- `def read_ps5_report(dualsense)`
- `def slow_down_flash(controller)`
- `def turn_off_indicator(controller)`
- `def update_adaptive_triggers(dualsense, report: dict)`
- `def update_ps5_led_state(ps5, ps5_controller)`

**utils/recovery_utils.py**

- `def alert_FM_about_recovery(msg)`
- `def fetch_std_err(proc_name)`
- `def set_ignore_errors()`

**utils/regenerate_config.py**

- `def regenerate_config()`

**utils/rotation_utils.py**

- `def get_r2(th)`
- `def get_rotation_matrix(roll, pitch, yaw)`
- `def rotate2(x, y, th, centroid)`
- `def to_global(xs, ys, pose)`
- `def to_local(xs, ys, pose)`

**utils/runner.py**

- `def delfino_data(motor, ticks_ref, pwm, ticks, error, int_error, derivative)`
- `def delfino_error(code)`

**utils/serial_utils.py**

- `def connect_to_serial_bus(port, baudrate, bytesize, timeout, period)`

**utils/system_profiler.py**

- `def main()`
- `def save_system_profile_data(FLAGS)`

**utils/time_slice.py**

- `def get_run_folder(incident_folder, incident)`
- `def get_time_slice(incident_date, incident_time, num_frames)`

**utils/undistort_images.py**

- `def get_video_id(string)`
- `def main()`
- `def process_images(FLAGS)`
- `def str2bool(v)`

**utils/upload_health_report.py**

- `def upload_file(file_path, file_name, file_type, append)`
- `def upload_health_report(file_name)`

**utils/validate_config.py**

- `def debug_print(s)`
- `def load_valid_params(d, dict_param, prefix)`
- `def validate(k, v)`
- `def validate_dict(d, prefix)`

**utils/visa_utils.py**

- `def _get_relevant_path(path: np.ndarray, safe_dist: float) → np.ndarray`
- `def _is_sez(zone: dict) → Any`
- `def about_to_gate_crash(path: np.ndarray, zone: dict) → bool`
- `def about_to_gate_crash_rect(path: np.ndarray, apply_box) → bool`
- `def add_visa_to_redis_db(redis_db: redis.Redis, visa_info: dict) → Any`
- `def am_i_unparking(entry_gate: int) → bool`
- `def check_wakeup_visa_type(exc_zone_dict: dict, pose: np.ndarray) → str`
- `def generate_visa_request(zone_id: int, zone_name: str, visa_type: str) → dict`
- `def get_core_box(exc_zone_dict: dict)`
- `def get_crash_dict(zone_id, zone_name, visa_type)`
- `def get_inflated_box(exc_zone_dict: dict, offset)`
- `def get_safe_dist(visa_type, zone)`
- `def get_visas_held()`
- `def get_zone_dict(zones, ids)`
- `def get_zone_id(path: np.ndarray, exc_zones: list, enforce_visa: bool) → Union[...]`
- `def get_zone_names(exc_zones_dict)`
- `def get_zone_tags(exc_zones_dict)`
- `def import_ezs()`
- `def is_it_gate_crash(path: np.ndarray, exc_zone_dict: dict, visa_type: str) → bool`
- `def is_safe_distance_from_gate(zone: dict, path: np.ndarray, visa_type: str) → bool`
- `def is_unparking(zone_id: int) → bool`
- `def log_zone_names(zone_ids, zone_names_dict)`
- `def relative_distance_from_gate(zone: dict, path: np.ndarray, safe_dist: float) → float`
- `def release_all_visas_held()`
- `def release_visa(zone_id: str, zone_name: str, visa_type: str)`
- `def remove_visa_from_redis_db(redis_db: redis.Redis, visa_info: dict) → Any`
- `def send_visa_release_msg(sock, released_visa)`
- `def should_i_release_visa(path: np.ndarray, exc_zone_dict: dict, visa_type: str) → bool`
- `def st_poses_from_zones(exc_zones_dict: dict) → np.ndarray`
- `def update_redis_visa_pose(redis_db: redis.Redis, pose: np.ndarray) → Any`

**utils/write_to_config.py**

- `def add_to_config(toml_path, key, var, val, src, update_eventlog)`
- `def append_eventlog(msg, date_str)`
- `def delete_from_config(toml_path, key, var)`
- `def update_change_log(config, key, var, val, src, date_str, operation)`
- `def update_dict(_dict, key, val, delete)`

**utils/write_to_fifo.py**

- `def write_to_maintenance_fifo(fifo_msg)`

### Exported Classes

**ati/common/bus.py**

- `class AsyncBus(object)`
  - `run(self)`
  - `run_background(self)`
  - `stop_thread(self)`
  - `subscribe(self, topic, callback)`
- `class Bus(object)`
  - `close(self)`
  - `recv(self)`
  - `send(self, topic, message)`
  - `subscribe(self, topic)`

**ati/common/config.py**

- `class Config`
  - `add_keys(section, kv, dict_cum)`
  - `get_consolidated(self)`
  - `list_fq_params(self, d)`
- `class ConfigLoader`
  - `get_config(self)`
  - `reload_config(self)`
- `class Singleton(type)`

**ati/control/actuator/actuator.py**

- `class Actuator(ActuatorFactory)`
  - `update(self, args, gradient_profile, obstacle_speed_factor, last_obstruction_time, paused, visa_factor, safety_exception_indicator)`
  - `update_actuators(self, args, gradient_profile, obstacle_speed_factor, last_obstruction_time, paused, visa_factor, safety_exception_indicator) → ActuatorFactory`
- `class ActuatorFactory(object)`
  - `indicators(self)`
  - `motors(self)`
  - `sound(self)`
  - `webui(self)`
- `class DefaultActuators(ActuatorFactory)`
  - `indicators(self)`
  - `sound(self)`
- `class IdleActuators(ActuatorFactory)`
  - `indicators(self)`
  - `motors(self)`
  - `sound(self)`
- `class InplaceActuators(ActuatorFactory)`
  - `indicators(self)`
- `class LowBatteryActuators(ActuatorFactory)`
  - `indicators(self)`
- `class PausedActuators(ActuatorFactory)`
  - `indicators(self)`
  - `sound(self)`

**ati/control/bridge/cx/auto_hitch_trolley_ops_cx.py**

- `class AutoHitchTrolleyOpsCx(TrolleyOpsCx)`
  - `basic_checks(self)`
  - `check_if_auto_hitch_needed(self, old_pose)`
  - `check_termination(self)`
  - `drop_hitch_while_moving(self)`
  - `get_auto_hitch_station(self, trolley_detect_pose, cur_pose, runtime_braking_distance)`
  - `get_trolley_hitch_pose_from_lidar(self, cur_pose)`
  - `get_unhitch_pose(self)`
  - `hitch_trolley(self)`
  - `is_cur_station_trolley_detect(self, cur_pose)`
  - `reset_hitch_status_at_end_trip(self)`

**ati/control/bridge/cx/auto_unhitch_trolley_ops_cx.py**

- `class AutoUnitchTrolleyOpsCx(TrolleyOpsCx)`
  - `basic_checks(self)`
  - `drop_hitch_while_moving(self)`
  - `get_unhitch_pose(self)`
  - `reset_hitch_status_at_end_trip(self)`

**ati/control/bridge/cx/cx_abc.py**

- `class CxABC(ABC)`
  - `basic_checks(self)`
  - `check_if_reset(self)`
  - `check_path_state(self, cur_pose)`
  - `check_terminate_current_trip(self, waiting_for_a_trip)`
  - `check_termination(self)`
  - `check_tracker_mode(self)`
  - `drive_mule(self)`
  - `execute_payload_parking(self)`
  - `execute_table_parking(self)`
  - `get_dynamic_inplace_path(self)`
  - `handle_postprocess(self, seg_args)`
  - `initialize_control_module(self)`
  - `make_mule_move(self)`
  - `maybe_update_visa_obj(self)`
  - `pause_after_inplace(self)`
  - `publish_control_trip_status(self, trip_active)`
  - `publish_trip_status_msg(self, stoppage_reason)`
  - `stop_mule(self)`
  - `update_cur_pose(self)`
  - `update_path_state(self)`
  - `update_trip_status_msg(self, stoppage_reason)`
- `class TrackerState`
  - `set(self, state_vector)`

**ati/control/bridge/cx/cx_utils.py**

- `class StoppagesInfo`
  - `to_dict(self)`
- `class TripInfo`
  - `to_dict(self)`
- `class TripStatus`
  - `to_dict(self)`

**ati/control/bridge/cx/follow_me_cx.py**

- `class FollowMeCx(CxABC)`
  - `basic_checks(self)`
  - `check_termination(self)`
  - `get_local_plan(self, cur_pose, goal_pose)`
  - `publish_current_goal_pose(self)`
  - `reset_trip_status_at_end_trip(self)`
  - `update_follow_me_path(self)`
  - `update_path_state(self)`

**ati/control/bridge/cx/pallet_ops_cx.py**

- `class PalletOpsCx(CxABC)`
  - `check_termination(self)`
  - `execute_payload_parking(self)`
  - `get_station_front_pose(self)`
  - `publish_control_status(self, status)`

**ati/control/bridge/cx/tote_dispatch_cx.py**

- `class ToteDispatchCx(CxABC)`
  - `basic_checks(self)`
  - `check_for_errors(self)`
  - `check_if_reset(self)`
  - `update_loadcell_status(self)`

**ati/control/bridge/cx/trolley_ops_cx.py**

- `class TrolleyOpsCx(CxABC)`
  - `alert_at_start_of_new_trip(self)`
  - `basic_checks(self)`
  - `check_termination(self)`
  - `reset_trip_status_at_end_trip(self)`
  - `start_alert_timer(self)`

**ati/control/bridge/path_state/path_state_abc.py**

- `class PathStateABC(ABC)`
  - `am_i_in_special_regime(self)`
  - `check_if_parking_unparking(self)`
  - `check_termination(self)`
  - `compute_inplace_path(self, cur_pose)`
  - `get_action_mode(self)`
  - `get_cur_tracker(self, policy, tracker_state)`
  - `get_current_mode(self)`
  - `get_current_regime_and_route_type(self)`
  - `get_dest_pose(self)`
  - `get_eta(self)`
  - `get_nearest_index(self, pose)`
  - `get_next_switch_ind(self)`
  - `get_progress(self)`
  - `get_stations_objects_poses(self) → Union[...]`
  - `has_path_change_event_occured(self, cur_pose, to_pose, to_station_name, trip_id, trip_leg_id, move_to_ack)`
  - `has_tracker_changed(self)`
  - `is_cur_regime_parking(self)`
  - `is_next_segment_reverse(self)`
  - `is_previous_segment_reverse(self)`
  - `is_set(self)`
  - `maybe_update(self, cur_pose)`
  - `maybe_update_move_action_idx(self)`
  - `maybe_update_path_indices(self, cur_pose)`
  - `prepare_route(self, start_pose, end_pose, to_station_name, reattempt)`
  - `publish_reached_status(self)`
  - `publish_trip_status(self, trip_status_msg)`
  - `reattempt_route(self, cur_pose)`
  - `save_path_state_in_redis_db(self)`
  - `set_path_state(self, path_components, segment_regime_mapping, segment_route_type_mapping, to_station_name, dynamic_inplace)`
  - `update_local_path_indices(self)`
  - `update_path_state(self, to_pose, start_pose, to_station_name)`
  - `update_pose(self, cur_pose)`
  - `update_reached_msg(self)`
  - `update_regime(self)`
  - `update_route_for_inplace(self)`

**ati/control/bridge/path_state/path_state_auto_hitch.py**

- `class AutoHitchTrolleyOpsPS(PathStateABC)`
  - `check_for_auto_hitch_activation(self)`
  - `prepare_auto_unhitch_release_route(self, start_pose, end_pose, to_station_name, reattempt)`
  - `prepare_trolley_parking_route(self, cur_pose, trolley_pose, return_pose, trolley_pickup_station_name)`
  - `reset(self, terminate_trip)`

**ati/control/bridge/path_state/path_state_follow_me.py**

- `class FollowMePS(PathStateABC)`
  - `check_local_termination(self)`
  - `get_nearest_local_index(self, pose)`
  - `is_set(self)`
  - `reset(self, terminate_trip)`
  - `update_local_path_indices(self, cur_pose)`

**ati/control/bridge/path_state/path_state_pallet_ops.py**

- `class PalletOpsPS(PathStateABC)`
  - `prepare_payload_docking_route(self, cur_pose, payload_pose, payload_length, return_pose, payload_pickup_station_name, current_mode, cte, te)`
  - `reset(self, terminate_trip)`

**ati/control/bridge/path_state/path_state_tote_dispatch.py**

- `class ToteDispatchPS(PathStateABC)`
  - `reset(self, terminate_trip)`
  - `try_reparking(self, cte, te, cur_pose)`

**ati/control/bridge/path_state/path_state_trolley_ops.py**

- `class TrolleyOpsPS(PathStateABC)`
  - `prepare_auto_unhitch_release_route(self, start_pose, end_pose, to_station_name, reattempt)`
  - `reset(self, terminate_trip)`

**ati/control/bridge/path_state/path_state_utils.py**

- `class ControlState`
- `class PathComponents`
- `class State`
  - `update(self, state)`

**ati/control/bridge/router_planner_interface.py**

- `class RoutePlannerInterface`
  - `allow_recovery(self)`
  - `create_router(self, route_graph_json_path, terminal_lines, stations, fm, route_application)`
  - `get_route_and_regimes(self, start_pose, end_pose, reattempt, recovery, auto_unhitch_drop, auto_hitch_pickup, task)`
  - `update_last_trip_in_redis(self, start_pose, end_pose)`

**ati/control/controls_comms/comm_threads.py**

- `class BaseThread(Thread)`
  - `stop(self)`
- `class ConveyorStatusGather(BaseThread)`
  - `get_conveyor_status_reading(self)`
  - `reset(self)`
  - `run(self)`
- `class DestDataGather(BaseThread)`
  - `get_pose(self)`
  - `reset_receiver(self)`
  - `run(self)`
- `class FmApiKeyErrorGather(BaseThread)`
  - `get_fm_api_key_error(self)`
  - `run(self)`
- `class FmAutoHitchGather(BaseThread)`
  - `get_auto_hitch_command(self)`
  - `run(self)`
- `class FmInitGather(BaseThread)`
  - `get_init(self)`
  - `run(self)`
- `class GoalPoseGather(BaseThread)`
  - `get_pose(self)`
  - `reset_receiver(self)`
  - `run(self)`
- `class HitchPoseGather(BaseThread)`
  - `get_hitch_pose(self)`
  - `run(self)`
  - `stop(self)`
- `class LoadCellGather(BaseThread)`
  - `get_load_cell_reading(self)`
  - `run(self)`
- `class PauseGather(BaseThread)`
  - `get_pause_command(self)`
  - `run(self)`
- `class PayloadPoseGather(BaseThread)`
  - `get_payload_pose(self)`
  - `run(self)`
  - `stop(self)`
- `class ResetGather(BaseThread)`
  - `get_reset(self)`
  - `run(self)`
- `class TablePoseGather(BaseThread)`
  - `get_table_pose(self)`
  - `run(self)`
  - `stop(self)`
- `class TerminateTripGather(BaseThread)`
  - `get_terminate_trip(self)`
  - `reset_terminate_trip(self)`
  - `run(self)`
- `class UnhitchTimeoutGather(BaseThread)`
  - `get_unhitch_timeout(self)`
  - `run(self)`

**ati/control/controls_comms/fm_communicator.py**

- `class FMCommunicator`
  - `notify_trip_completion(self, destination_pose, data_source)`
  - `publish_alert_at_start(self, topic)`
  - `publish_control_status(self, mode, regime_info, data_source)`
  - `publish_mule_status(self, mode, data_source)`
  - `publish_parking_status(self, is_precision_parking, data_source)`
  - `publish_reached_status(self, reached_msg, data_source)`
  - `publish_tote_reset_ack(self, prev_task, data_source)`
  - `publish_trip_status(self, trip_status_msg, data_source)`
  - `publish_trip_status_update(self, trip_status)`
  - `publish_unhitch_signal(self, topic)`
  - `receive_auto_hitch_command(self)`
  - `receive_auto_unhitch_timeout(self)`
  - `receive_conveyor_status_data(self)`
  - `receive_current_pose(self)`
  - `receive_destination_pose(self)`
  - `receive_fm_api_key_error(self)`
  - `receive_fm_init(self)`
  - `receive_goal_pose(self)`
  - `receive_hitch_pose(self)`
  - `receive_pause_command(self)`
  - `receive_payload_pose(self)`
  - `receive_reset_data(self)`
  - `receive_table_pose(self)`
  - `receive_terminate_trip(self)`
  - `reset_goal_pose_receiver(self)`
  - `reset_receiver(self)`
  - `send_init_message(self, init_message, data_source)`
  - `send_tracker_error_message(self, cte_flag, cte, te_flag, te, path_deviation_flag, path_deviation, theta_discontinuity_flag, dte, data_source)`

**ati/control/dynamic_router/auto_hitch_park_solver.py**

- `class AutoHitchParkSolver(RouteSolverABC)`
  - `compute_reattempt_route(self, start_pose, end_pose)`

**ati/control/dynamic_router/axial_cross_park_solver.py**

- `class AxialCrossParkSolver(RouteSolverABC)`
  - `compute_reattempt_route(self, start_pose, end_pose)`

**ati/control/dynamic_router/core_routes_solver.py**

- `class CoreRoutesSolver(RouteSolverABC)`
  - `compute_reattempt_route(self, start_pose, end_pose)`
  - `compute_sub_routes(self, start_pose, end_pose, task)`

**ati/control/dynamic_router/graph_builder.py**

- `class GridRoute`
  - `allow_recovery(self)`
  - `dump_exclusion_zone_json(self, json_path)`
  - `generate_path_wps_for_viz(self, start_pose, dest_poses)`
  - `get_edge_analytics(self)`
  - `get_route_length(self, start_pose, end_pose, reattempt)`
  - `set_globals(self, route_application)`
  - `solve_route(self, start_pose, end_pose, reattempt, recovery, auto_unhitch_drop, auto_hitch_pickup, need_redis, task)`
  - `update_lanes(self)`

**ati/control/dynamic_router/graph_builder_utils.py**

- `class GraphObjectUtils`
  - `generate_graph_object_json(terminal_lines, stations_info, gmaj_checksum, dynamic_router_release, graph_object_path, directed_graph)`
- `class Station`
  - `to_dict(self)`
- `class TerminalLine`
  - `to_dict(self)`

**ati/control/dynamic_router/grid_map_utils.py**

- `class Line`
  - `angle(self)`
  - `angle_between_lines(self, line)`
  - `get_point_at_length(self, d)`
  - `orthogonal_direction(self)`
  - `reduce_length_by(self, z, distance_to_reduce)`
- `class LineSeg`
  - `add_lanechange(self, pt, lc_length, offset, l, transit_length, thresh)`
  - `align_along_wall(self, wall_angle, l, thresh)`
  - `check_relevant_lines(self, l, thresh)`
  - `delete_lane_change(self, lc_start_id, l)`
  - `delete_split_lane(self, split_start_id, l)`
  - `extend_upto_a_line(self, constraint_line)`
  - `find_constraint_lines(self, l)`
  - `find_relevant_lines(self, l, thresh)`
  - `is_same_point(self, a, b, tol)`
  - `match_edge_line_terminals(self, line)`
  - `move_parallel(self, dist, l, thresh)`
  - `plot_pts(self)`
  - `project_onto_a_line(self, line)`
  - `rotate_about_end_pt(self, theta, l, about_start_pt, thresh)`
  - `rotate_about_mid_pt(self, theta, l, thresh)`
  - `split_lane(self, pt, offset1, offset2, transit_length, l, thresh)`
  - `swap(self)`
  - `update_direction(self)`
  - `update_length(self)`
  - `update_lineseg_properties(self)`

**ati/control/dynamic_router/lifter_park_solver.py**

- `class LifterParkSolver(RouteSolverABC)`
  - `compute_reattempt_route(self, start_pose, end_pose)`

**ati/control/dynamic_router/lifter_pm_park_solver.py**

- `class PalletMoverParkSolver(RouteSolverABC)`
  - `compute_reattempt_route(self, start_pose, end_pose)`

**ati/control/dynamic_router/map_editor_utils.py**

- `class Line`
  - `angle(self)`
  - `angle_between_lines(self, line)`
  - `get_point_at_length(self, d)`
  - `orthogonal_direction(self)`
  - `reduce_length_by(self, z, distance_to_reduce)`

**ati/control/dynamic_router/pallet_mover_park_solver.py**

- `class PalletMoverParkSolver(RouteSolverABC)`
  - `compute_reattempt_route(self, start_pose, end_pose)`

**ati/control/dynamic_router/park_solver_v5.py**

- `class ParkSolverV5(RouteSolverV5WPS)`
  - `compute_reattempt_route(self, start_pose, end_pose)`

**ati/control/dynamic_router/route_solver_abc.py**

- `class RouteSolverABC(ABC)`
  - `compute_sub_routes(self, start_pose, end_pose, task)`
  - `find_optimal_route(self, unpark_routes, park_routes, start_station_obj, end_station_obj)`
  - `get_aptap_route_wps(self, start_pose, end_pose, start_node, end_node)`
  - `get_core_route(self, start_pose, end_pose, start_station_obj, end_station_obj)`
  - `get_route(self, start_pose, end_pose, exclusion_zones, reattempt, recovery, auto_unhitch_drop, auto_hitch_pickup, need_redis, task)`
  - `get_route_length(self, start_pose, end_pose, reattempt)`
  - `update_stations_info(self)`

**ati/control/dynamic_router/route_solver_v5wps.py**

- `class RouteSolverV5WPS`
  - `allow_recovery(self)`
  - `compute_sub_routes(self)`
  - `find_optimal_route(self)`
  - `generate_path_wps_for_viz(self, start_pose, dest_poses)`
  - `get_aptap_route_wps(self, start_pose, end_pose, start_node, end_node)`
  - `get_core_route(self, start_pose, end_pose, start_node, end_node)`
  - `get_path_lines_and_cumulative_dist(self)`
  - `get_route_and_regimes(self, start_pose, end_pose, reattempt, recovery, task, need_redis)`
  - `get_route_length(self, start_pose, end_pose, task)`
  - `get_unpark_park_routes(self)`
  - `get_visa_obj(self)`
  - `nodes_pnc(self, unpark_nodes, park_nodes)`
  - `post_process_route(self)`
  - `set_globals(self)`
  - `update_last_trip_in_redis(self)`

**ati/control/dynamic_router/standalone_router.py**

- `class StandaloneGraphBuilder`
  - `build_graph(self) → nx.DiGraph`
  - `get_request_config(_config_file)`
- `class StandaloneRouter`
  - `compute_route_with_all_outputs(self, start_pose: List[...], end_pose: List[...], start_task: Optional[...], end_task: Optional[...]) → Tuple[...]`
  - `get_dense_path(self, start_pose: List[...], end_pose: List[...], start_task: Optional[...], end_task: Optional[...]) → Tuple[...]`
  - `get_route_wps_for_viz(self, start_pose: List[...], end_pose: List[...], start_task: Optional[...], end_task: Optional[...]) → Tuple[...]`
- `class StandaloneRouterConfig`
  - `get(self, path: str, default)`

**ati/control/dynamic_router/trolley_ops_solver.py**

- `class TrolleyOpsSolver(RouteSolverABC)`

**ati/control/dynamic_router/v2_wps_routes_solver.py**

- `class V2WpsSolver(RouteSolverABC)`
  - `get_core_route(self, start_pose, end_pose, recovery, need_redis)`
  - `get_route(self, start_pose, end_pose, exclusion_zones, reattempt, recovery, auto_unhitch_drop, auto_hitch_pickup, need_redis, task)`
  - `get_route_length(self, start_pose, end_pose, reattempt)`
  - `get_station_dists(self, pose)`
  - `get_station_id(self, pose)`
  - `get_station_id_with_thresh(self, pose)`
  - `set_globals(self)`

**ati/control/dynamic_router/v5wps_utils.py**

- `class Edge`
  - `get_dir(self)`
- `class Node`
  - `get_conso_edges(self)`
- `class Route`
  - `fetch_best_route(self, optimal_index, optimal_wps, optimal_core_route, optimal_cand_route)`
- `class Station`
  - `get_dir(self)`
  - `get_parking_nodes(self)`
  - `get_unparking_nodes(self)`

**ati/control/instrumentation/load_cell.py**

- `class LoadCell`
  - `check_overload(self, load)`
  - `compute_load(self, load_cell_value)`
  - `get_load_cell_reading(self)`
  - `publish_load_cell_reading(self, sock, load_value, overload)`

**ati/control/instrumentation/load_cell_calibration.py**

- `class LoadCellCalib`
  - `check_overload(self, load)`
  - `compute_load(self, load_cell_value)`
  - `get_load_cell_reading(self)`
  - `publish_load_cell_reading(self, sock, load_value, overload)`

**ati/control/instrumentation/sound_controller.py**

- `class SoundController(object)`
  - `play_sound(self, new_sound)`
  - `stop_sound(self)`

**ati/control/logger/trip_logs.py**

- `class TripLogger`
  - `reset_timers_at_end_of_trip(self)`
  - `set_timer(self, current_trip_status)`
  - `update_policy_log(self, policy_obj, is_idle_flag)`
  - `update_trip_log(self, policy_obj, is_idle_flag)`
  - `update_trip_log_msg(self)`
  - `update_trip_status(self, policy_obj, path_state_obj, cur_pose)`
  - `update_trip_timer(self, current_trip_status)`

**ati/control/low_control/auto_unhitch.py**

- `class AutoUnhitch(object)`
  - `unhitch_on_request(self, hitch)`

**ati/control/low_control/low_control.py**

- `class WheelController(object)`
  - `get_wheel_commands(self)`
  - `set_steer_angle(self, steering)`
  - `set_velocity(self, linear_velocity, angular_velocity)`
  - `set_with_ps4_command(self, linear_velocity, angular_velocity, gradient)`
  - `update(self, ps4_control)`
  - `update_for_calibration(self, linear_velocity, steering)`

**ati/control/low_control/pid.py**

- `class PID(object)`
  - `reset(self)`
  - `update(self, error)`

**ati/control/misc/ez.py**

- `class EZGate`
  - `to_dict(self)`
- `class VisaApp`
  - `to_dict(self)`

**ati/control/misc/tote_error_handler.py**

- `class ToteErrorHandler`
  - `check_for_error(self, comms, waiting_for_a_trip)`
  - `check_for_tote_count_error_at_start(self)`
  - `check_load_cell_for_tote_count_error_at_start(self)`
  - `check_load_cell_if_tote_present(self)`
  - `check_totes_moved(self)`
  - `get_latest_load_reading(self, comms)`
  - `get_latest_tote_count(self, comms)`
  - `handle_conveyor_initial_check(self, error)`
  - `load_last_tote_count_from_redis(self)`
  - `publish_tote_status_update_to_fleet(self)`
  - `reset(self, complete_reset)`

**ati/control/misc/unhitch_monitor.py**

- `class UnhitchMonitor`
  - `check_for_unhitch_timeout(self)`
  - `run_monitor(self)`

**ati/control/misc/visa_permit_updater.py**

- `class VisaPermitUpdater(Thread)`
  - `add_to_visas_held(self, visa_info)`
  - `am_i_allowed(self, zone_id, visa_value)`
  - `process_release_msg(self, visa_info)`
  - `process_req_granted_msg(self, visa_info)`
  - `process_visa_msg(self, msg)`
  - `release_visa(self, released_visa)`
  - `remove_from_visas_held(self, visa_info)`
  - `reset(self)`
  - `run(self)`
  - `stop(self)`

**ati/control/move.py**

- `class MoveMule`
  - `move_mule(self, path_state, current_tracker, tracker_state, pose)`

**ati/control/planner/bezier.py**

- `class Bezier1D`
  - `calc_first_derivative(self)`
  - `calc_second_derivative(self)`
- `class Bezier2D`
  - `calc_curvature(self)`
  - `calc_yaw(self)`
  - `get_pts_per_bezier(self, points)`
  - `stack_control_points(self, wps1, wps4, golden_ratio)`

**ati/control/planner/frenet.py**

- `class Frenet`
  - `calc_cartesian_paths(self, fplist)`
  - `calc_frenet_parameters(self, fp, s0, c_d, c_d_d, c_d_dd, di, Ti, tv)`
  - `calc_frenet_paths(self, c_d, c_d_d, c_d_dd, s0)`
  - `check_path_collision(self, fp, t_fp)`
  - `convert_cart_pose_to_frenet(self)`
  - `get_bezier_index(self, s)`
  - `get_candidate_paths(self)`
  - `get_mule_vels(self, v, w)`
  - `get_obst_pts(self, grid)`
  - `get_trolley_pose(self, v, w, pose)`
  - `load_frenet_configs(self)`
  - `plan(self, pose, path_state, v, w, frenet_mode, trolley)`
  - `post_process(self, candidates)`
  - `set_lat_vel_acc(self, cand_path)`
- `class Trolley`

**ati/control/planner/frenet_polynomials.py**

- `class Frenet_path`
  - `calculate_costs(self)`
- `class quartic_polynomial`
  - `calc_first_derivative(self, t)`
  - `calc_point(self, t)`
  - `calc_second_derivative(self, t)`
  - `calc_third_derivative(self, t)`
  - `squared_jerk_integral(self, t)`
- `class quintic_polynomial`
  - `calc_first_derivative(self, t)`
  - `calc_point(self, t)`
  - `calc_second_derivative(self, t)`
  - `calc_third_derivative(self, t)`
  - `compute_coefficients(self, T)`
  - `squared_jerk_integral(self, t)`

**ati/control/planner/full_trajectory.py**

- `class TrajectoryInfo`

**ati/control/redis_updater/redis_updater_tote_dispatch.py**

- `class ToteDispatchRedisUpdater`
  - `reset_redis(self, path_state, cur_pose)`
  - `to_dict(self)`
  - `update_init_status_msg_from_redis(self)`
  - `write_init_status_msg_to_redis(self, path_state, cur_pose, complete_reset, visas_held)`

**ati/control/redis_updater/redis_updater_trolley_ops.py**

- `class TrolleyOpsRedisUpdater`
  - `reset_redis(self, path_state, cur_pose)`
  - `to_dict(self)`
  - `update_init_status_msg_from_redis(self)`
  - `write_init_status_msg_to_redis(self, path_state, cur_pose, complete_reset, visas_held)`

**ati/control/regimes/regime_factory.py**

- `class GetInplace(RegimeFactory)`
  - `get_tracker(self, policy, state, tracker_regime)`
- `class GetMPC(RegimeFactory)`
  - `get_tracker(self, policy, state, tracker_regime)`
- `class GetTanTracker(RegimeFactory)`
  - `get_tracker(self, policy, state, tracker_regime)`
- `class RegimeFactory(ABC)`
  - `GetTracker(self) → Tracker`

**ati/control/regimes/regimes.py**

- `class Default`
  - `activate(self, path_state, tracker_state, data_logger)`
- `class Features`
  - `activate_feature_factory(self, path_state, tracker_state, data_logger)`
- `class PrecisionParking`
  - `activate(self, path_state, tracker_state, data_logger)`

**ati/control/safety/drive_current_monitor.py**

- `class DriveCurrentMonitor(Thread)`
  - `get_mahalanobis_dist(self, measurement)`
  - `get_rms_dist(self, state, new_measurement)`
  - `is_anomaly(self, measurement)`
  - `monitor(self)`
  - `moving_average(self, x, w)`
  - `run(self)`
  - `update_anomaly_window(self, new_measurement)`

**ati/control/safety/ez_policy.py**

- `class VisaSupport`
  - `compute_visa_factor(self, path: np.ndarray) → float`
  - `maybe_apply_for_wakeup_parking_visa(self, pose: np.ndarray) → Any`
  - `update_visa_agent_from_redis(self)`
  - `update_visa_obj(self, visa_obj: VisaApp) → Any`

**ati/control/safety/imu_divergence.py**

- `class AsyncBusReader(Thread)`
  - `msg_callback(self, topic, msg)`
  - `publish_stats(self)`
  - `run(self)`

**ati/control/safety/polygon_policy.py**

- `class DrivingPolicy`
  - `apply_zone_specific_padding(self, pose, variable_padding_zones)`
  - `check_for_stale_runaway_heartbeat(self, sensor_status_msg)`
  - `check_path_intersection_with_zone(self, path, zones)`
  - `check_stoppage_debounce(self)`
  - `clear_payload_info(self, mule_mask, payload_mask, path_mask)`
  - `close_sockets(self)`
  - `closest_collision(self, grid, pose, path_mask, sensor_grid, reverse, local_frame)`
  - `compute_speed_factors(self, path, data_age, path_mask, d_grid, pose, obstacle_info)`
  - `corrected_velocity(self, path, pose, inplace_policy, exception_sectors, reverse, local_frame, trolley_path)`
  - `extend_path(self, path)`
  - `get_drivable_info(self)`
  - `get_obstacle_factor(self, d_grid, pose, path_mask, sensor_grid, reverse, local_frame)`
  - `get_obstacle_info(self, obstacles_world, distances, obstacle_points, sensor_grid, pose, sensor_list, local_frame)`
  - `get_path_mask(self, path, d_grid, inplace_policy, reverse)`
  - `get_traffic_intersection(self, path)`
  - `get_trolley_dimensions(self, config)`
  - `get_zone_specific_stop_dist(self, pose)`
  - `is_low_speed_zone(self, pose)`
  - `is_ramp_zone(self, pose)`
  - `is_special_camera_zone(self, pose)`
  - `process_data_age(self, drivable_info)`
  - `process_device_monitor_exception(self, exception_msg, sensor_status_msg)`
  - `process_lidar_exception(self, exception_msg, sensor_status_msg)`
  - `process_runaway_exception(self, exception_msg, sensor_status_msg)`
  - `process_sensor_exceptions(self, sensor_id, exception_msg, sensor_status_msg)`
  - `process_tote_sensor_exception(self, exception_msg, sensor_status_msg)`
  - `publish_drivable_region_policy_msg(self, drivable_info, obstacle_info, speeds, d_grid, path_mask, pose, path, start_time)`
  - `publish_mule_status_msg(self, obstacle_info)`
  - `publish_obstacle_info(self, obstacle_info)`
  - `publish_policy_msgs(self, speeds, drivable_info, pose, obstacle_info, d_grid, path_mask, path, start_time)`
  - `publish_stoppage_message(self, speeds, drivable_info, pose)`
  - `set_globals(self, stop_dist)`
  - `stop_for_safety_exceptions(self)`
  - `stop_for_sensor_exceptions(self)`
  - `stoppage_wait_time(self, vel_factor)`
  - `update_avoidance_params(self)`
  - `update_gradient_profile(self, pose)`
  - `update_path_and_mule_dims(self, pose, path, reverse, inplace_policy)`
  - `update_stop_dist(self, pose, zone_stop_dist, zone_slow_dist)`
- `class PolicyStubs`

**ati/control/safety/runaway_utils.py**

- `class DataGatherer`
  - `process_encoder_data(self, topic, message)`
  - `process_gyro_bias(self, topic, message)`
  - `process_gyro_data(self, topic, message)`
  - `process_rear_wheel_hall_sensor(self, topic, message)`
  - `process_yelli_data(self, topic, message)`
- `class DriveMotor(Motor)`
  - `check_score_for_anamoly(self)`
  - `process_enc_message(self, use_outlier_rejection, sensor_data)`
  - `publish_buffer_data(self)`
- `class GyroMonitor(Thread)`
  - `check_for_anamoly(self)`
  - `check_for_msg_latency(self, enc_msg, last_message_time, motor_name)`
  - `get_v_w_from_enc_values(self)`
  - `monitor_gyro(self)`
  - `publish_exception(self, sum_divergence, raise_fatal_error)`
  - `run(self)`
  - `update_scores(self, new_measurement)`
- `class Motor(Thread)`
  - `check_for_msg_latency(self, enc_msg, last_message_time, motor_name)`
  - `check_new_exception_event(self)`
  - `check_score_for_anamoly(self)`
  - `handle_exception(self, sensor_data)`
  - `monitor_motor(self, sensor_data_objs)`
  - `process_enc_message(self, use_outlier_rejection, sensor_data)`
  - `run(self)`
  - `update_exception_event_types(self)`
- `class SteerMotor(Motor)`
  - `check_score_for_anamoly(self)`
  - `process_enc_message(self, use_outlier_rejection, sensor_data)`
  - `publish_buffer_data(self)`
- `class VelocityMonitor(Thread)`
  - `check_for_anamoly(self)`
  - `convert_rpm_to_velocity(self)`
  - `get_mahalanobis_distance(self, measurement)`
  - `is_outlier(self, new_measurement)`
  - `monitor_velocity(self)`
  - `run(self)`
  - `update_outlier_window(self, new_measurement)`
  - `update_scores(self, new_measurement)`
- `class YelliMonitor(Thread)`
  - `check_for_anamoly(self)`
  - `check_yelli_threshold(self)`
  - `get_v_w_from_ticks(self)`
  - `monitor_yelli(self)`
  - `run(self)`

**ati/control/scripts/open_loop_utils.py**

- `class CyclesTest(OpenLoopSteering)`
  - `run_flag(self)`
  - `run_iteration(self)`
- `class OpenLoopSteering`
  - `run_flag(self)`
  - `run_iteration(self)`
- `class StairCaseTest(OpenLoopSteering)`
  - `run_flag(self)`
  - `run_iteration(self)`

**ati/control/sockets/pose_sockets.py**

- `class AprilTagSock(PoseSock)`
  - `create_subscription(self)`
  - `terminate_subscription(self)`
- `class PoseSock(ABC)`
  - `create_subscription(self)`
  - `terminate_subscription(self)`
- `class YelliSock(PoseSock)`
  - `create_subscription(self)`
  - `terminate_subscription(self)`

**ati/control/tracker_library/drive_inplace.py**

- `class InPlaceTracker(object)`
  - `set_time(self, time)`
  - `update(self, mule_pose)`

**ati/control/tracker_library/inplace_tracker_module.py**

- `class InplaceTracker(Tracker)`
  - `check_deviation_from_pose(self, mule_pose, ref_pose, path_state)`
  - `terminate(self)`
  - `track(self, ref_path, mule_pose, v, w, path_state)`

**ati/control/tracker_library/lmpc_tracker.py**

- `class LMpcSolver(object)`
  - `get_cost_function(self, A, B, curr_state)`
  - `get_mpc_model(self, traj, control)`
  - `get_ref_traj_slice(self, traj, control)`
  - `get_velocity_limit(self, ref_trajectory, policy_factor)`
  - `load_weights(self, config)`
  - `quadprog_solve_qp(self, P, q, G, h)`
  - `solve(self, state, ref_trajectory, policy_factor, pose, dt, ignore_path_density_check, frenet_meta)`
  - `track(self, H, F, control_slice, vtarget)`

**ati/control/tracker_library/mpc_tracker.py**

- `class MpcSolver(object)`
  - `check_density(self, ref_trajectory)`
  - `exp_filter(self, new_data, policy_factor, ref_path)`
  - `fit_path(self, current_pose, path)`
  - `load_weights(self, config)`
  - `rotation_matrix(self, theta)`
  - `solve(self, state, ref_trajectory, policy_factor, pose, dt, ignore_path_density_check, frenet_meta)`
  - `track(self, v0, k0, path, v_min, v_t, dt, state)`
  - `transform_world_to_local(self, x, y, theta, points)`

**ati/control/tracker_library/mpc_tracker_module.py**

- `class MpcContext`
- `class MpcTracker(Tracker)`
  - `call_tracker_solver(self, t0, ref_path, mule_pose, path_state, lmpc)`
  - `check_for_frenet(self, ref_path)`
  - `execute_tracker_command(self, t0, v, w, stop_mule_flag)`
  - `get_frenet_path(self, ref_path, mule_pose, path_state)`
  - `get_nearest_index(self, pose, path)`
  - `get_ref_path(self, ref_path, actual_mule_pose, mule_control_pose, path_state)`
  - `get_ref_path_for_lmpc(self, ref_path)`
  - `is_recovery_reqd(self, mule_pose, ref_path)`
  - `mule_near_zone_end(self, ref_path, path_state)`
  - `update_cte_threholds(self, in_avoidance_zone, avoidance_offset)`
  - `update_solver_vmin(self)`
  - `update_tracker_params_for_segment(self, new_segment)`
  - `update_weights_for_casadi(self)`
- `class MpcTrackerState`

**ati/control/tracker_library/tan_tracker_module.py**

- `class TanTracker(Tracker)`
  - `call_tracker_solver(self, t0, ref_path, mule_pose, stop_mule_flag, path_state)`

**ati/control/tracker_library/tracker_abc.py**

- `class Tracker(ABC)`
  - `execute_tracker_command(self, t0, v, w, stop_mule_flag)`
  - `is_mule_stopping(self, ref_path, mule_pose, path_state, has_frenet_planned, trolley_info)`
  - `print_tracker_log(self, v, w, t0)`
  - `slow_down_for_tracker_switch(self, dist_to_switch)`
  - `terminate(self)`
  - `track(self, ref_path, mule_pose, v, w, path_state)`

**ati/control/trip_status/trip_status_abc.py**

- `class TripStatusABC(ABC)`
  - `update_trip_status(self, path_state, cur_pose, tracker_state, policy)`

**ati/control/trip_status/trip_status_tote_dispatch.py**

- `class ToteDispatchTripStatus(TripStatusABC)`
  - `to_dict(self)`

**ati/control/trip_status/trip_status_trolley_ops.py**

- `class TrolleyOpsTripStatus(TripStatusABC)`
  - `to_dict(self)`

**ati/drivers/can_bus/can_python_drivers/CAN_Parsing.py**

- `class CAN_Node(ABC)`
  - `CAN_Rx_IDs(self)`
  - `parseMsg(self, msg)`
- `class ParseRule`
  - `apply(self, msg)`

**ati/drivers/can_bus/can_python_drivers/can_hall_sensor.py**

- `class HallData`

**ati/drivers/can_bus/can_python_drivers/linakactuator.py**

- `class Linak_LA(CAN_Node)`
  - `CAN_Rx_IDs(self)`
  - `getReady(self)`
  - `parseMsg(self, msg)`
  - `parseTPDO1(self, msg)`
  - `setpos(self, pos)`
  - `stop_actuation(self)`
  - `switcherr(errcode)`

**ati/drivers/hall_sensor.py**

- `class HallData`

**ati/drivers/isaac_sim/isaac_sim_bridge.py**

- `class InvalidMessage(Exception)`
- `class RecvBus(object)`
  - `close(self)`
  - `recv(self)`
  - `subscribe(self, topic)`
- `class SherpaSensors(Enum)`
- `class mule_sensor_status_thread(Thread)`
  - `run(self)`
  - `sensor_status_update(self)`
  - `stop(self)`
- `class receive_camera_msg_from_isaac_sim_thread(Thread)`
  - `run(self)`
  - `sensor_data_update(self, msg)`
  - `stop(self)`
- `class receive_encoder_data_from_isaac_sim_thread(Thread)`
  - `calc_velocities(self, v_mps, v_ref_mps, theta_steer_deg, theta_steer_ref_deg)`
  - `get_radius_of_curvature(self, angle_deg)`
  - `get_velocity_from_hub_and_curv(self, hub_v_mps, rad_curv_m, angle_deg)`
  - `rpm_to_rps(self, rpm)`
  - `run(self)`
  - `sensor_data_update(self, sensor_data)`
  - `stop(self)`
  - `vw_to_rpm(self, v, w)`
- `class receive_lidar_data_from_isaac_sim_thread(Thread)`
  - `publish_livox_packet(self)`
  - `publish_lut_and_lidar_frame(self)`
  - `run(self)`
  - `sensor_data_update(self, lidar_data)`
  - `stop(self)`
- `class send_control_commands_to_isaac_sim_thread(Thread)`
  - `control_commands_update(self)`
  - `run(self)`
  - `stop(self)`
- `class stoppages_message_thread(Thread)`
  - `run(self)`
  - `stop(self)`
  - `stoppages_message_update(self)`

**ati/drivers/realsense/cam_recorder.py**

- `class CameraImageRecorder(object)`
  - `get_camera_config(self)`
  - `save_frames(self)`
  - `save_image(self, cam, img, count, save)`
- `class GenericPBRecorder`
  - `callback(self, topic, update)`
  - `get_new_fd(self)`
- `class MonocularDepthEstimateRecorder(GenericPBRecorder)`
- `class MultiCameraRecorderGstreamer(object)`
  - `get_camera_config(self)`
  - `get_pipeline_str(self, camera_str_id)`
  - `initialize_gst_pipeline(self, pipeline_str, Gst)`
  - `run_gstreamer(self)`
- `class MultiDepthPBRecorder(object)`
  - `get_config_tags(self)`
  - `get_file_names(self, camera_id_str)`
  - `run_depth_recorder(self, rgbd_config, depth_fd, time_fd)`
  - `run_v4l2_depth_recorder(self, rgbd_config, depth_fd, time_fd)`
- `class MultiDepthRecorderGstreamerTrunc(object)`
  - `run_gstreamer(self, camera_id)`
- `class MultiDepthRecorderRust(object)`
  - `run_rust(self)`
- `class StereoRecorderGstreamer(MultiCameraRecorderGstreamer)`
  - `get_camera_config(self)`
  - `get_pipeline_str(self, camera_str_id)`
  - `initialize_gst_pipeline(self, pipeline_str, Gst)`

**ati/drivers/realsense/realsense_config.py**

- `class GstConfig`
  - `append_to_gst_str(self, append_str)`
  - `get_gst_pipeline_str(self, fps, input_format, appsrc_name, output_format, width, height, loopback_device, secondary_loopback_device)`
  - `set_gst_strs(self, rgbd_driver_config)`
- `class RGBDDriverConfig`
  - `get_publish_config(self)`

**ati/drivers/realsense/rs_gst.py**

- `class RSDevice`
  - `apply_depth_filters(self)`
  - `enable_advanced_mode(self)`
  - `enable_streams(self)`
  - `get_camera_params(self)`
  - `get_device_temp(self)`
  - `get_frames(self)`
  - `get_rs_device(self)`
  - `init_rs_pipeline(self)`
  - `log_advance_config(self)`
  - `perform_hardware_reset(self)`
  - `raise_cam_data_not_recvd_error(self)`
  - `set_empty_frames(self)`
  - `set_laser_power(self, sensor)`
  - `set_visual_preset_and_laser_pwr(self)`
  - `setup_depth_filters(self)`
  - `setup_generic_filters(self)`
  - `start_rs_pipeline(self)`
  - `stop_realsense_pipeline(self)`
- `class V4L2Publisher(Thread)`
  - `check_for_eos(self)`
  - `get_appsrc(self, appsrc_name)`
  - `init_gst_pipeline(self)`
  - `publish_msg_in_zmq_bus(self)`
  - `publish_rs_frames_to_v4l2(self)`
  - `push_color_image(self)`
  - `push_depth_image(self)`
  - `push_ir_frames(self)`
  - `run(self)`
  - `set_ts(self)`
  - `setup_appsrcs(self)`
  - `setup_gst_pipeline(self)`
  - `start_gst_pipeline(self)`
  - `stop(self)`
  - `stop_gst_pipeline(self)`

**ati/drivers/rplidar/rplidar.py**

- `class RPLidarManager`
  - `is_healthy(self, timeout)`
  - `read_frames(self, timeout)`
  - `read_scans(self, timeout)`
  - `reset(self)`
  - `start(self)`
  - `stop(self)`

**ati/drivers/wheel_calibration.py**

- `class EncoderDebug(object)`
  - `run(self, _, update)`

**ati/orchestrator/orch_mode.py**

- `class OrchestratorMode(object)`
  - `add_cmd_recovery(self, proc_name, all_commands, all_recovery)`
  - `create_run_analytics(self, start_time, run_folder_path, is_current)`
  - `create_run_folder(self)`
  - `end_old_run(self)`
  - `end_run(self)`
  - `get_run_info_txt(self, run_analytics, full, include_only)`
  - `mode_info_str(self)`
  - `record_run_data(self, run_analytics, run_folder_path)`
  - `run(self)`
  - `set_cmds(self)`
  - `start_run(self)`
  - `write_error_info(self)`
  - `write_to_run_info(self, msg, run_folder_path)`

**ati/orchestrator/orchestrator.py**

- `class Orchestrator`
  - `get_mode_kwargs(self)`
  - `init_redis_conn(self)`
  - `is_busy(self)`
  - `is_mode_valid(self, mode)`
  - `load_map(self)`
  - `publish_mode_info(self)`
  - `reload_config(self)`
  - `reset_pose(self, pose, switch_to_off)`
  - `run(self)`
  - `run_core(self)`
  - `run_states(self)`
  - `set_new_mode(self)`
  - `set_state_transition(self, transition_reason, new_run_name)`
  - `signal_handler(self, signum, frame)`
  - `start_publish_mode_thread(self)`
  - `status(self)`
  - `stop(self)`
  - `stop_current_run(self, transition_reason, new_run_name)`
  - `stop_mode_publish_thread(self)`
  - `switch(self, mode, user, run_name)`
  - `switch_to_error(self, user, error_info, error_dict)`
  - `wait_for_mode_change(self)`

**ati/orchestrator/orchestrator_slave.py**

- `class Orchestrator`
  - `get_mule_orc_client(self)`
  - `init_aredis_conn(self)`
  - `maybe_switch_mule_to_error_mode(self)`
  - `monitor_mode_change(self, set_mode)`
  - `process_mode_info(self, mode_info)`
  - `set_env_vars(self)`
  - `signal_handler(self, signum, frame)`
  - `start(self)`
  - `subscribe_to_mode_info(self)`
  - `unsubscribe_to_mode_info(self)`

**ati/orchestrator/process_group.py**

- `class ProcessGroup(object)`
  - `did_process_die_with_error(self, returncode)`
  - `get_error_key(self, std_err_str)`
  - `get_processes(self)`
  - `get_status(self)`
  - `handle_error(self, dead_proc_name)`
  - `kill(self)`
  - `list_proc(self, msg)`
  - `proc_communicate(self, proc_name, proc)`
  - `process_error(self)`
  - `run(self)`
  - `run_recovery(self, dead_proc_name)`
  - `set_stop_flag(self)`
  - `start(self)`
  - `start_proc(self, proc_cmd, std_out, std_err)`
  - `stop(self)`
  - `stop_processes(self)`
  - `terminate(self)`
  - `wait_for_proc_termination(self)`

**ati/perception/body_mask.py**

- `class BodyMask`
  - `get_ego_mask(self, frame, sensor_str_fq)`
  - `load_body_masks(self, mask_folder)`

**ati/perception/calibration/base_calibrator.py**

- `class BaseCalibrator`
  - `assign_data_reader(self)`
  - `calibrate(self)`
  - `calibrate_roll_pitch(self)`
  - `calibrate_yaw(self)`
  - `calibrate_z(self)`
  - `check_calibration(self)`
  - `get_calibration_diff(self)`
  - `get_data(self, transform, trim, remove_ceiling)`
  - `load_config(self, config_name)`
  - `reset_data_reader(self)`
  - `save_calibration(self)`
  - `update(point_cloud)`
  - `visualize(self)`

**ati/perception/calibration/camera_calibrator.py**

- `class CameraCalibrator(BaseCalibrator)`
  - `assign_data_reader(self)`
  - `calibrate(self)`
  - `calibrate_depth_scale(self)`
  - `check_calibration(self)`
  - `get_calibration_diff(self)`
  - `get_data(self, transform: Optional[...], trim, remove_ceiling)`
  - `reset_data_reader(self)`
  - `save_calibration(self)`

**ati/perception/calibration/imu_calibrate.py**

- `class ImuCalibrator`
  - `calculate_sliding_window_variance(self)`
  - `check_latency(self)`
  - `compute_variance(self, data_buffer)`
  - `get_imu_extrinsics(self)`
  - `get_imu_transforms(self, ip, port)`
  - `get_variance(self)`
  - `process_imu_data(self, row)`
  - `write_to_config(self)`

**ati/perception/calibration/lidar_calibrator.py**

- `class LidarCalibrator(BaseCalibrator)`
  - `assign_data_reader(self, dataset)`
  - `calibrate(self)`
  - `check_calibration(self)`
  - `get_calibration_diff(self)`
  - `get_data(self, transform: Optional[...], trim, remove_ceiling)`
  - `save_calibration(self)`

**ati/perception/calibration/motion_model.py**

- `class BaseMotionModel`
  - `predict(self, s, P, u, dt)`
- `class BicycleMotionModel(BaseMotionModel)`
  - `predict(self, s, P, u, dt)`
- `class UnicycleMotionModel(BaseMotionModel)`
  - `predict(self, s, P, u, dt)`

**ati/perception/calibration/relative_calibrator_ICP.py**

- `class RelativeCalibratorICP`
  - `assign_data_reader(self, dataset)`
  - `calibrate(self, ref_transform)`
  - `get_data(self, reader, transform: Optional[...], trim)`
  - `multiscale_icp(self, source, target)`
  - `reset_data_reader(self)`
  - `update(frame_idx)`
  - `visualize(self, ref_transform, calibrated_relative_transform)`

**ati/perception/calibration/relative_calibrator_fixed.py**

- `class RelativeCalibratorFixed`
  - `calibrate(self, calibrated_reference: Transform)`

**ati/perception/calibration/run_vehicle_lidar_and_steering_calibration_online.py**

- `class LiveEKF`
  - `handle_lidar(self, x, y, th, timestamp, ref)`
  - `handle_steering(self, delta_rad, timestamp)`
  - `handle_velocity(self, v, timestamp)`

**ati/perception/calibration/state_estimator.py**

- `class StateEstimator`
  - `get_covariance(self)`
  - `get_innovation(self)`
  - `get_state(self)`
  - `predict(self, u)`
  - `update(self, z, R_cov)`

**ati/perception/depth_estimation/depth_estimator.py**

- `class DepthEstimator`
  - `get_inverse_depth(self, color_frame)`
  - `get_quantised_inverse_depth(self, color_frame)`
  - `preprocess_img(self, color_frame)`

**ati/perception/depth_estimation/monocular_depth_on_stoppage.py**

- `class MonoDepthOnStoppage`
  - `get_cam_obst_history(self)`
  - `is_msg_valid(self, topic, msg)`
  - `maybe_reset_obst_history(self)`
  - `process_obst_info(self, topic, msg)`
  - `publish_mono_depth(self, data_reader, cam_id)`
  - `should_publish_mono_depth(self)`

**ati/perception/detection/leg_clustering.py**

- `class legClustering(ModelABC)`
  - `detect(self)`
  - `get_lidar_frame(self, msg)`
  - `publish_pose(self, centroid)`
  - `receive_current_pose(self)`

**ati/perception/detection/model_abc.py**

- `class ModelABC(ABC)`
  - `detect(self)`

**ati/perception/detection/sample_model.py**

- `class Model_1(ModelABC)`
  - `detect(self)`
  - `get_lidar_frame(self, msg)`
  - `publish_pose(self, centroid)`

**ati/perception/ekf/augmented_ekf.py**

- `class EkfLive`
  - `background_publish_thread(self)`
  - `get_state(self)`
  - `predict(self, motion_model)`
  - `publish_ekf(self, update_types)`
  - `publish_thread(self)`
  - `state_update(self, measurement, measurement_model)`

**ati/perception/ekf/ekf.py**

- `class Ekf`
  - `predict(self, motion_model)`
  - `state(self, state: GaussianState)`
  - `state_update(self, z, measurement_model)`
- `class GaussianState`

**ati/perception/ekf/measurement_models.py**

- `class AccMagMeasurementModel(MeasurementModel)`
  - `get_err(self, measurement, predicted_state)`
  - `get_observation_mat(self, x)`
  - `normalize(self, state)`
  - `predict(self, x)`
- `class FrontDualEncMeasurementModel(MeasurementModel)`
  - `get_err(self, measurement, predicted_state)`
  - `get_observation_mat(self, x)`
  - `get_reverse_sensor_model(self, x)`
  - `normalize(self, state)`
  - `predict(self, x)`
- `class GyroMeasurementModel(MeasurementModel)`
  - `get_err(self, measurement, predicted_state)`
  - `get_observation_mat(self, x)`
  - `get_reverse_sensor_model(self, x)`
  - `normalize(self, state)`
  - `predict(self, x)`
- `class LocalisationMeasurementModel(MeasurementModel)`
  - `get_err(self, measurement, predicted_state)`
  - `get_observation_mat(self, x)`
  - `normalize(self, state)`
  - `predict(self, x)`
- `class MeasurementModel`
  - `get_err(self, measurement, predicted_state)`
  - `get_observation_mat(self, x)`
  - `normalize(self)`
  - `predict(self, x)`
- `class MeasurementParams`
- `class RearHubMeasurementModel(MeasurementModel)`
  - `get_err(self, measurement, predicted_state)`
  - `get_observation_mat(self, x)`
  - `get_reverse_sensor_model(self, x)`
  - `normalize(self, state)`
  - `predict(self, x)`
- `class YelliConfig`
- `class YelliMeasurementModel(MeasurementModel)`
  - `get_R_yelli(self, measured_pose)`
  - `get_err(self, measurement, predicted_state)`
  - `get_observation_mat(self, x)`
  - `normalize(self, state)`
  - `predict(self, x)`

**ati/perception/ekf/motion_models.py**

- `class CTRVAModel(MotionModel)`
  - `get_F(self, x)`
  - `get_G(self, theta, theta_ac, size)`
  - `get_Q(self, x)`
  - `predict(self, x)`
- `class CTRVAParams`
- `class CTRVModel(MotionModel)`
  - `get_F(self, x)`
  - `get_G(self, theta, size)`
  - `get_Q(self, x)`
  - `predict(self, x)`
- `class CTRVParams`
- `class ConstantVWModel(MotionModel)`
  - `get_Q(self)`
  - `predict(self, x)`
- `class GyroModel(MotionModel)`
  - `predict(self, x)`
- `class MotionModel`
  - `predict(self)`
- `class ProcessParams`
- `class VWParams`
- `class WheelConfig`
- `class WheelOdoModel(MotionModel)`
  - `predict(self, x)`
  - `update_control_signals(self, wr, wl)`

**ati/perception/ekf/msg_processor.py**

- `class MsgProcessor`
  - `get_attr(self, attr)`
  - `is_attr_new(self, attr_id)`
  - `process_msg(self, msg_meta, topic, msg)`

**ati/perception/ekf/sensor_fusion.py**

- `class SensorFusion`
  - `predict(self, data, timestamp)`
  - `reset(self, pose, measurement_type)`
  - `state(self)`
  - `update(self, data, timestamp, measurement_type)`
  - `validate_prediction(self, alt_state_vec)`

**ati/perception/ekf/sensor_readers/sensors.py**

- `class Wheel_enc_debug`
  - `callback(self, topic, msg)`
- `class Yelli_data`
  - `callback(self, topic, msg)`

**ati/perception/ekf/trolley_ekf/trolley_ekf.py**

- `class EKFDataGather`
  - `read_pose(self, topic, msg)`
  - `read_trolley_angle(self, topic, msg)`
  - `read_vel(self, topic, msg)`
- `class TrolleyTracker(Thread)`
  - `is_valid_detection(self)`
  - `norm_angle(self)`
  - `run(self)`
  - `validate(self, v, err_value)`

**ati/perception/ekf/trolley_ekf/trolley_ekf_utils.py**

- `class TrolleyKF`
  - `get_hitch_point(self, pose, L)`
  - `load_config(self, config)`
  - `predict(self, control, curr_pose, current_time, detect_angle)`
  - `predict_covariance(self, control)`
  - `update(self, measurement)`
  - `update_trolley_cords(self, hitch_pose, D, si)`

**ati/perception/ekf/v_w_ekf.py**

- `class EkfVW`
  - `check_update_threshold(self, measurement, measurement_model)`
  - `mahalanobis_dist(self, measurement, measurement_model)`
  - `predict(self, ts)`
  - `state(self)`
  - `update(self, measurement, measurement_model)`

**ati/perception/ekf/v_w_ekf_live.py**

- `class GenericReader(Thread)`
  - `get_data(self, message_name)`
  - `is_message_new(self, message_name)`
  - `run(self)`
- `class WheelEncoderReader(Thread)`
  - `get_data(self, sensor_id)`
  - `is_message_new(self, sensor_id)`
  - `run(self)`

**ati/perception/ekf/v_w_ekf_live2.py**

- `class GenericReader(Thread)`
  - `get_data(self, message_name)`
  - `is_message_new(self, message_name)`
  - `run(self)`
- `class WheelEncoderReader(Thread)`
  - `get_data(self, sensor_id)`
  - `is_message_new(self, sensor_id)`
  - `run(self)`

**ati/perception/ekf/v_w_ekf_live2sensor_rejection.py**

- `class GenericReader(Thread)`
  - `get_data(self, message_name)`
  - `is_message_new(self, message_name)`
  - `run(self)`
- `class WheelEncoderReader(Thread)`
  - `get_data(self, sensor_id)`
  - `is_message_new(self, sensor_id)`
  - `run(self)`

**ati/perception/lidar/lidar_class.py**

- `class Dataset`
  - `animate(nlidar)`
  - `disp(self, data, n, xlim, ylim, figsize, start, end, showcarto, transform, apply, superimpose, shownum, highlight1, highlight2, title, alpha)`
  - `display_kerbs(self, n, xlim, ylim, figsize, showcarto, title, ypos, nsmooth, predict, offset, alpha, alpha2)`
  - `get_camera_image(self, nlidar, undistort, skew, show)`
  - `get_data(self, nlidar, debug, show, last, step, xlim, ylim, zlim, show_camera, undistort, skew, remove_ground, title, rem_obstacles, show_obstacles)`
  - `get_data_frames(self, nlidar, show, debug, last, step, xlim, ylim, zlim, show_camera, undistort, skew, title, remove_ground, rem_obstacles, show_obstacles)`
  - `get_frame_number(self, time)`
  - `get_kerbs(self, lrange, last, step, xlim, maxdiff, method, ht)`
  - `get_lidar_data(self, nlidar, flipxy)`
  - `get_lidar_data_merge(self, frames, frange, offset, debug)`
  - `get_lidar_data_single(self, n, dx, dy, flipxy)`
  - `get_pcd(self, n, dropzeros)`
  - `get_visualizer_images(self, time, xlim, ylim, zlim, h, w, dpi, fname, ref_data_file)`
  - `getcarto(self, nlidar, offset, debug)`
  - `getimage(self, nlidar, offset, debug)`
  - `load_kerbs_all(self, fname)`
  - `makevideo(self, frames, xlim, ylim, zlim, h, w, showmap, fname, ref_data_file)`
  - `makevideo_lidaronly(self, frames, xlim, ylim, zlim, cxlim, cylim, showmap, camera, fname, ref_data_file)`
  - `maplidar(self, start, end, step, debug, remove_ground, from_end, xlim, ylim, zlim)`
  - `plot_carto(self, start, end, nevery, show, figsize, ax)`
  - `savemap(self, fname, pts)`
  - `set_map(self, mapfile, rotate_theta, n, show)`
- `class Logging`
  - `info()`

**ati/perception/lidar/lidar_config.py**

- `class LidarConfig`
  - `get_lidar_type(self)`
  - `init_drivable_config(self)`
  - `init_missing_sectors_config(self)`
  - `init_ouster_configs(self)`
  - `is_livox(self)`
  - `is_ouster(self)`
  - `set_min_pc_len(self)`

**ati/perception/lidar/lidar_data_processor.py**

- `class LidarDataProcessor`
  - `add_spherical_coordinates(self, frame)`
  - `clear_shooting_pts(self, lidar_data, mule_box)`
  - `find_missing_sectors(self, lidar_data)`
  - `is_lidar_blocked(self, lidar_data)`
  - `perform_motion_correction(self, frame, v, w, dt)`
  - `perform_tilt_correction(self, frame, roll, pitch, yaw)`

**ati/perception/lidar/lidar_utils.py**

- `class Limits`
  - `set(self, x, y, z)`
- `class Plane`
  - `update(self, normal, plane, inliers, outliers, mean_dist)`

**ati/perception/lidar/livox_reader.py**

- `class LivoxLidar`
  - `reset(self)`
  - `transform_pts(self, pts)`
- `class LivoxLidarReader`
  - `get_frame(self)`
  - `get_packet_lidar_ids(self)`
  - `process_frame(self)`
  - `process_packet(self, packet)`
  - `reset(self)`
  - `reset_buffer(self)`
  - `set_v_w(self, v, w)`

**ati/perception/lidar_2d/rplidar_config.py**

- `class RPLidarConfig`
  - `init_drivable_config(self)`

**ati/perception/mlmodels/tensorrt_utils.py**

- `class HostDeviceMem(object)`
- `class TrtModel(object)`
  - `evaluate_inference_time(self, num_inference)`
  - `reshape_outputs(self, outputs)`
  - `run_inference(self, inputs)`

**ati/perception/mlmodels/tf_utils.py**

- `class tfModel`
  - `get_frozen_graph(self)`
  - `infer_saved_model(self, input)`
  - `load_model(self)`
  - `update_trainables(self, trainable, train_bns)`

**ati/perception/mlmodels/trt_int8_quantizer.py**

- `class EntropyCalibrator(trt.IInt8EntropyCalibrator2)`
  - `get_batch(self, x)`
  - `get_batch_size(self)`
  - `read_calibration_cache(self)`
  - `write_calibration_cache(self, cache)`

**ati/perception/object_detection/trt_yolo.py**

- `class TrtYolo`
  - `infer_yolo(self, color_frame, frame_id, frame_time)`
  - `init_config(self)`
  - `publish_bbox2D(self, frame_id, frame_time, bbox, obj_type, score)`

**ati/perception/object_detection_3d/pointpillar.py**

- `class PointPillarDetector`
  - `detect_objects(self, frame)`
  - `get_objects_with_class_name(self, class_name)`
  - `preprocess_frame(self, frame)`
  - `set_f_intensity(self, lidar_type)`
  - `subsample_frame(self, frame, desired_size)`

**ati/perception/object_tracking/deep_sort/common.py**

- `class HostDeviceMem(object)`

**ati/perception/object_tracking/deep_sort/detection.py**

- `class Detection(object)`
  - `get_class(self)`
  - `get_confidence(self)`
  - `to_tlbr(self)`
  - `to_xyah(self)`

**ati/perception/object_tracking/deep_sort/generate_detections.py**

- `class ImageEncoder(object)`
  - `preprocess_input(self, input)`

**ati/perception/object_tracking/deep_sort/kalman_filter.py**

- `class KalmanFilter(object)`
  - `gating_distance(self, mean, covariance, measurements, only_position)`
  - `initiate(self, measurement)`
  - `predict(self, mean, covariance)`
  - `project(self, mean, covariance)`
  - `update(self, mean, covariance, measurement)`

**ati/perception/object_tracking/deep_sort/nn_matching.py**

- `class NearestNeighborDistanceMetric(object)`
  - `distance(self, features, targets)`
  - `partial_fit(self, features, targets, active_targets)`

**ati/perception/object_tracking/deep_sort/track.py**

- `class Track`
  - `get_class(self)`
  - `get_confidence(self)`
  - `is_confirmed(self)`
  - `is_deleted(self)`
  - `is_tentative(self)`
  - `mark_missed(self)`
  - `predict(self, kf)`
  - `to_tlbr(self)`
  - `to_tlwh(self)`
  - `update(self, kf, detection)`
- `class TrackState`

**ati/perception/object_tracking/deep_sort/tracker.py**

- `class Tracker`
  - `gated_metric(tracks, dets, track_indices, detection_indices)`
  - `predict(self)`
  - `update(self, detections)`

**ati/perception/object_tracking/yolo_with_plugins.py**

- `class HostDeviceMem(object)`
- `class TrtYOLO(object)`
  - `detect(self, img, conf_th, nms_threshold, letter_box)`

**ati/perception/obstacle_detection/drivable_callbacks.py**

- `class DrivableDataCallbacks`
  - `add_callback(self, topic, callback_fn)`
  - `control_status_callback(self, topic, msg)`
  - `encoder_callback(self, topic, msg)`
  - `is_msg_stale(self, topic, msg)`
  - `lidar_2d_callback(self, topic, msg)`
  - `livox_lidar_callback(self, topic, msg)`
  - `monocular_depth_callback(self, topic, msg)`
  - `ouster_lidar_callback(self, topic, msg)`
  - `route_type_update_callback(self, topic, msg)`
  - `rs_camera_callback(self, topic, msg)`
  - `set_dummy_data(self)`
  - `set_topics_and_callbacks(self)`
  - `setup_cam_readers(self)`
  - `setup_lidar_2d_reader(self)`
  - `setup_lidar_reader(self)`
  - `setup_tof_reader(self)`
  - `setup_ultrasound_reader(self)`
  - `start_cam_readers(self)`
  - `start_listening(self)`
  - `tof_callback(self, topic, msg)`
  - `ultrasound_callback(self, topic, msg)`
  - `unset_dummy_data(self)`
  - `yelli_callback(self, topic, msg)`

**ati/perception/obstacle_detection/drivable_detectors.py**

- `class MasterDrivableDetector`
  - `add_camera_drivable_detector(self, cam_str)`
  - `add_lidar_drivable_detector(self, mode)`
  - `segment_2d_lidar_obstacles(self, lidar_2d_data, lidar_2d_config)`
  - `segment_camera_obstacles(self, cam_data)`
  - `segment_lidar_obstacles(self, lidar_data)`
  - `set_detector_limits(self, mode, on_ramp)`
  - `set_lidar_detector_limits(self, mode)`
  - `setup_vehicle_params(self)`
  - `toggle_on_ramp_behaviour(self, on_ramp)`
  - `validate_lidar_limits(self, lidar_limits, mode)`

**ati/perception/obstacle_detection/drivable_grid.py**

- `class DriveGrid2D`
  - `add_mule_box(self, grid, pose, mule_box)`
  - `add_pts_cupy(self, pts, pose, sensor_id, prob, default_prob, grid, ht_grid, sensor_grid)`
  - `apply_nogo(self)`
  - `blur(self, k)`
  - `cp2np(self)`
  - `get_grid_bytes(self)`
  - `get_grid_corners(self)`
  - `get_ht_grid_bytes(self)`
  - `get_sensor_grid_bytes(self)`
  - `get_sensor_src_id(self, sensor_src)`
  - `np2cp(self)`
  - `process_objects(self, objects)`
  - `reset(self)`
  - `reset_grids(self, clear_ground)`
  - `transform_grid_to_local(self, frame)`
  - `transform_grid_to_world(self, frame)`
  - `transform_local_to_world(self, pose, frame)`
  - `transform_world_to_grid(self, frame)`
  - `update_with_msg(self, drivable_region)`
  - `validate(self, data)`
  - `validate_xyz(self, data)`

**ati/perception/obstacle_detection/drivable_region.py**

- `class DrivableRegion(DrivableDataCallbacks)`
  - `add_drivable_detectors(self)`
  - `add_grnd_pts(self, pose)`
  - `add_obst_pts(self, pose)`
  - `cleanup_lidar_data(self)`
  - `is_data_stale(self)`
  - `is_data_valid(self)`
  - `is_lidar_blocked(self)`
  - `log_and_publish(self)`
  - `perform_ego_pts_check(self)`
  - `perform_safety_checks(self)`
  - `perform_vehicle_specific_tasks(self)`
  - `perform_zone_specific_tasks(self)`
  - `process_2d_lidar_data(self)`
  - `process_cam_data(self)`
  - `process_control_status(self)`
  - `process_lidar_data(self)`
  - `process_new_msg(self, topic, msg)`
  - `process_sensor_data(self)`
  - `process_sensor_data_and_update_grid(self)`
  - `process_tof_data(self)`
  - `process_ultrasound_data(self)`
  - `publish_drivable_debug(self)`
  - `publish_drivable_grid(self)`
  - `publish_missing_sectors_exception(self)`
  - `publish_msg(self, topic, msg)`
  - `publish_safety_exception(self, exception_msg, frame_id, module, priority, expiry_duration)`
  - `publish_sensor_exception(self, sensor_id, message_id, ts, frame_id, data, msg, field, value)`
  - `record_processing_times(func)`
  - `reset(self)`
  - `run_if_not_offline(func)`
  - `set_mule_box(self)`
  - `setup_ego_pts_configs(self)`
  - `setup_lidar_block_params(self)`
  - `setup_lidar_data_processor(self)`
  - `setup_no_go_zones_configs(self)`
  - `timeit_wrapper(self)`
  - `update(self)`
  - `update_grid(self)`
  - `warmup(self)`
  - `wrapper(self)`

**ati/perception/obstacle_detection/obstacle_grid.py**

- `class DrivableDetector`
  - `get_ego_mask(self, frame)`
  - `get_ego_pts(self, frame)`
  - `get_zero_grid(self, dtype)`
  - `init_bin_counts(self)`
  - `init_cluster_grid(self)`
  - `off_ramp(self)`
  - `on_ramp(self, max_gradient_deg)`
  - `preprocess_frame(self, frame)`
  - `remove_ego_pts(self, frame)`
  - `segment_obstacle_pts(self, frame)`
  - `trim_frame(self, frame)`

**ati/perception/obstacle_detection/obstacle_validator.py**

- `class CamObstacleValidator`
  - `classify_near_and_far_pixels(self, cam_data)`
  - `get_obstacles_projected_onto_img(self, obstacle_pts)`
  - `get_valid_obstacles(self, cam_data, obstacle_pts)`
  - `get_vis_outputs(self)`
  - `is_data_in_sync(self, cam_data)`
  - `reset(self)`

**ati/perception/obstacle_detection/payload_safety.py**

- `class DataReader(Thread)`
  - `add_callback(self, topic, callback_fn)`
  - `get_control_status(self)`
  - `get_lidar_2d_data(self)`
  - `get_lift_status_from_db(self)`
  - `get_payload_status_from_db(self)`
  - `lidar_2d_callback(self, topic, msg)`
  - `lift_status_callback(self, topic, msg)`
  - `payload_pose_callback(self, topic, msg)`
  - `run(self)`
- `class PayloadSafety`
  - `check_for_object_under_payload(self, lidar_2d_data, control_status)`
  - `create_lidar_2d_ego_mask(self, consolidated_frames, control_status)`
  - `is_data_stale(self, lidar_2d_data)`
  - `publish_safety_exception(self, exception_msg, module, priority, expiry_duration)`
  - `publish_safety_exception_while_calibration(self)`
  - `reset(self)`
  - `run_if_not_offline(func)`
  - `wrapper(self)`

**ati/perception/payload_detection/ctx.py**

- `class PayloadDetectionContext`
  - `add_global_pose(self, payload_pred, mule_pose)`
  - `detect_payload(self, color_frame, cam_str, lidar_frame, frame_number)`
  - `get_closest_payload(self, valid_payloads, station_front_pose)`
  - `get_pose_pca(self, payload_pred)`
  - `get_pose_ransac(self, payload_pred)`
  - `get_valid_payloads(self, payload_preds, mule_pose)`
  - `keep_innermost_radial(self, points, center, bins)`
  - `preprocess_lidar_frame(self, lidar_frame, cam_str)`
  - `preprocess_output_mask(self, mask, input_img)`
  - `project_pc_on_payload(self, color_frame, lidar_frame, cam_str, front_face_mask, payload_pred)`
  - `record_debug(self, output_dir)`
  - `run_segmentation(self, bgr_frame)`
  - `validate_payload_distance(self, closest_distance, mule_pose, closest_payload_pose)`
  - `validate_payload_prediction(self, payload_pred)`
  - `warmup(self)`

**ati/perception/payload_detection/payload_config.py**

- `class PayloadConfig`
- `class PayloadDetectionConfig`
- `class PayloadPosePrediction`
  - `get_box_params(self)`
  - `shift_pose_along_payload(self, pose, dist)`
  - `update_poses(self)`

**ati/perception/payload_detection/publish_debug_hopt.py**

- `class MinimalPublisher(Node)`
  - `get_img_from_grid(self, data)`
  - `get_img_from_grid_1(self, data)`
  - `get_rplidar_frame(self)`
  - `make_cuboid_marker(self, payload_pose, pallet_yaw, z_offset, rgba)`
  - `make_foxglove_pc(self, xyz, rgba)`
  - `plot_cluster_map(self, cluster_map)`
  - `publish_xyz_points_to_topic(self, xyz, color, fields, ts, publisher)`
  - `timer_callback(self)`

**ati/perception/payload_detection/publish_debug_livox.py**

- `class MinimalPublisher(Node)`
  - `make_cuboid_marker(self, payload_pose, pallet_yaw, z_offset, rgba, pallet_w, pallet_d)`
  - `make_foxglove_pc(self, xyz, rgba)`
  - `publish_xyz_points_to_topic(self, xyz, color, fields, ts, publisher)`
  - `timer_callback(self)`

**ati/perception/payload_detection/sdg_pallet_detection.py**

- `class SDGPalletDetect`
  - `check_model(self)`
  - `find_peak(self, heatmap)`
  - `get_extents_bbox(self, kps)`
  - `get_pallet_keypoints(self, input_frame)`
  - `infer_frame(self, frame)`
  - `nms(self, keypoints, confidence)`
  - `postprocess_frame(self, heatmap, vectormap, scale)`
  - `preprocess_frame(self, frame)`

**ati/perception/rgbd_camera/camreader.py**

- `class BaseCamReader(Thread)`
  - `cap_read(self)`
  - `get_data(self)`
  - `handle_error(self)`
  - `open(self)`
  - `set_cv2_props(self)`
  - `stop(self)`
  - `wait_for_cam_msg_on_bus(self)`
- `class CamReader(BaseCamReader)`
  - `run(self)`
- `class DepthCamReader(BaseCamReader)`
  - `get_depth_frame(self)`
  - `process_depth_image(self)`
  - `run(self)`

**ati/perception/rgbd_camera/data_processor.py**

- `class CamDataProcessor`
  - `convert_depth_image_to_point_cloud(self, depth_image, remove_zeros)`
  - `depth_to_point_cloud_cupy(self, depth, remove_zeros, num_threads)`
  - `depth_to_point_cloud_fast(self, depth_img, remove_zeros)`
  - `depth_to_point_cloud_no_reshape(self, depth_img)`
  - `depth_to_point_cloud_numba(self, depth_img, remove_zeros)`
  - `get_frame(self, depth_image, remove_zeros, transform_flag)`
  - `get_pc_in_pixel_coords(self, pc, transform_flag)`
  - `get_pc_inside_mask(self, pc, binary_mask)`
  - `set_depth_table(self)`
  - `set_limits(self, limits)`
  - `set_use_cuda(self, use_cuda: bool)`
  - `transform_frame(self, frame)`
  - `trim_img(self, img)`

**ati/perception/rgbd_camera/rgbd_config.py**

- `class RGBDConfig`
  - `init_drivable_config(self)`
  - `init_obstacle_validator_config(self)`
  - `max_blind_spot_radius(self)`

**ati/perception/rgbd_camera/stereo_flo_odo_keyframe.py**

- `class BufferedCamData(Thread)`
  - `get_data_at_ts(self, ts)`
  - `run(self)`
- `class KeyFrameChecker`
  - `add(self, time, v)`
  - `is_keyframe(self)`

**ati/perception/rgbd_camera/v4l2_publisher.py**

- `class V4L2Publisher(Thread)`
  - `check_for_eos(self)`
  - `get_gst_pipeline_str(self)`
  - `init_gst_pipeline(self)`
  - `latency_check(self)`
  - `log_I_am_alive(self)`
  - `publish_data_to_loopback(self)`
  - `push_data(self, data_bytes: bytes)`
  - `run(self)`
  - `set_data(self, data_bytes)`
  - `set_ts(self)`
  - `setup_appsrcs(self)`
  - `setup_gst_pipeline(self)`
  - `start_gst_pipeline(self)`
  - `stop(self)`
  - `stop_gst_pipeline(self)`

**ati/perception/sensor_bag.py**

- `class SensorBag`
  - `add_transform(self, config, sensor_str_fq, use_factory_transform)`
  - `get_cam_data(self, sensor_str_fq)`
  - `get_lidar_2d_data(self, sensor_str_fq)`
  - `get_lidar_2d_merged(self)`
  - `get_lidar_data(self, sensor_str_fq)`
  - `get_merged_lidar_frame(self)`
  - `get_ultrasound_merged(self)`
  - `list_cameras(self)`
  - `list_lidar_2ds(self)`
  - `list_lidars(self)`
  - `list_ultrasounds(self)`
  - `update_cam_data(self, sensor_str_fq, cam_data)`
  - `update_lidar_2d_data(self, sensor_str_fq, lidar_2d_data)`
  - `update_lidar_data(self, sensor_str_fq, lidar_data)`

**ati/perception/slip_estimation/slip_estimation.py**

- `class SlipEstimation`
  - `run(self)`

**ati/perception/station_relocalisation/faiss_vpr.py**

- `class FaissVpr`
  - `add_keypoint_info_to_frame(self, frame, keypoints)`
  - `bgr_to_gray(self, frame)`
  - `collate_descriptors(self, landmark_poses, landmark_ts)`
  - `create_faiss_index(self)`
  - `get_data_path(self, folder)`
  - `get_feature_descriptor(self)`
  - `get_frame_at_ts(self, ts)`
  - `get_keypts_for_frame(self, frame)`
  - `get_mask(self, frame)`
  - `init_video_parser(self)`
  - `init_video_recorder(self)`
  - `load_data(self, folder)`
  - `pre_process_descriptors(self, descriptors)`
  - `pre_process_img(self, frame)`
  - `run_inference(self, frame)`
  - `save_data(self, folder)`

**ati/perception/station_relocalisation/kiss_icp_setup.py**

- `class KissSetup`
  - `load_local_maps(self, save_folder)`
  - `process_run(self, save_while_processing, save_folder)`
  - `save_local_maps(self, save_folder)`
  - `setup(self, save_folder, save_while_processing)`

**ati/perception/tests/data_loader.py**

- `class PickledDataReader`
  - `data_yielder(self)`
  - `save_data(self, pickled_data)`

**ati/perception/tests/schema.py**

- `class PickledData`

**ati/perception/tests/test_drivable_region.py**

- `class TestDrivableRegion(unittest.TestCase)`
  - `plot_grids(self, grids, fig_title)`
  - `plot_top_side_views(self, frame, obstacles, fig_title)`
  - `setUp(self)`
  - `test_drivable(self)`
  - `validate_obst_pts_to_total_pts_ratio(self, detector, obstacles)`
  - `validate_pts_in_grid(self, pts, expected_val, ratio_thresh, desc)`

**ati/perception/tests/test_lidar_data_processor.py**

- `class TestLidarDataProcesor(unittest.TestCase)`
  - `setUp(self)`
  - `test_missing_sectors(self)`

**ati/perception/trolley_detection/trolley_detection.py**

- `class LidarReaderStub`
  - `read_lidar_frame(self, topic, msg)`
- `class TrolleyDetection(Thread)`
  - `crop_frame(self, lidar_frame)`
  - `detect_trolley(self, lidar_stub, search_angle)`
  - `init_trolley_params(self, config)`
  - `publish_trolley_update(self, frame_id, hw_ts, trolley_angle, detected, process_time, max_score)`
  - `run(self)`

**ati/perception/trolley_detection/trolley_icp.py**

- `class ControlStatusStub`
  - `read_control_status(self, topic, msg)`
- `class LidarReaderStub`
  - `read_lidar_frame(self, topic, msg)`
- `class TrolleyDetectionICP(Thread)`
  - `crop_frame(self, lidar_frame)`
  - `detect_trolley(self, lidar_stub, search_angle)`
  - `detect_trolley_init(self, lidar_frame)`
  - `publish_trolley_update(self, frame_id, lidar_ts, trolley_angle, detected, process_time, score, matches, msg)`
  - `reset_trolley_params(self)`
  - `run(self)`

**ati/perception/trolley_detection/trolley_utils.py**

- `class Trolley`
- `class TrolleyParams`

**ati/perception/ultrasound/ultrasound.py**

- `class Ultrasound`

**ati/perception/utils/aruco_parking.py**

- `class ArucoPose`
  - `disambiguate_mule_pose(self, mule_poses_info)`
  - `do_marker_check(self, marker_corners)`
  - `get_aruco_dict(self)`
  - `get_marker_params(self, config)`
  - `mule_pose(self, val)`
  - `publish_aruco(self, tvecs, rvecs, marker_ids, ts)`
  - `publish_aruco_mule_pose(self, marker_id, aruco_mule_pose, ts)`
- `class ImageMemmap`
  - `get_data(self)`

**ati/perception/utils/colorspace_hitch/hitch_segmentation.py**

- `class ColorspaceHitch`
  - `check_if_lidar_in_color_seg(self, lidar_hitch_pose_local, seg_stats)`
  - `detect(self, img, yelli_pose, lidar_hitch_pose_local)`
- `class HitchClassifier`
  - `classify(self, vec)`
  - `load_pickle_model(self, model_path)`

**ati/perception/utils/data_gather.py**

- `class CamGather(Thread)`
  - `get_data(self)`
  - `run(self)`
  - `stop(self)`
- `class DataGather(Thread)`
  - `get_data(self)`
  - `run(self)`
  - `stop(self)`
- `class DtQueue`
  - `add_data(self, data, ts)`
  - `clear(self)`
  - `get_data(self, from_ts, to_ts)`

**ati/perception/utils/tag_based_parking.py**

- `class ApriltagPose`
  - `get_marker_params(self, config)`
  - `mule_pose(self, val)`
- `class ArucoPose`
  - `disambiguate_mule_pose(self, mule_poses_info)`
  - `do_marker_check(self, marker_corners)`
  - `get_aruco_dict(self)`
  - `get_marker_params(self, config)`
  - `mule_pose(self, val)`
  - `publish_aruco(self, tvecs, rvecs, marker_ids, ts)`
  - `publish_aruco_mule_pose(self, marker_id, aruco_mule_pose, ts)`
- `class ImageMemmap`
  - `get_data(self)`

**ati/perception/utils/tag_detector.py**

- `class TagDetector`
  - `detect(self)`
  - `get_apriltag_detection(self, img)`
  - `get_aruco_detection(self, img)`
  - `get_aruco_dict(self)`
  - `get_pose(self, rvec, tvec, tag_id, pose_2d)`

**ati/perception/utils/tag_ekf.py**

- `class GyroMotionModel`
  - `predict(self, x)`
- `class TagEstimator`
  - `add_gyro(self, prev_ts, present_ts)`
  - `compute_tag_estimate(self, eqYL, tCA, tYA)`
  - `get_estimates(self)`
  - `get_inital_rotation(self, qCA, tag_id)`
  - `gyro_bias_callback(self, topic, msg)`
  - `imu_callback(self, topic, msg)`
  - `intialize_ekf(self, qCA, tag_id)`
  - `publish_tag_estimate(self, tag_estimate, ts, tag_id)`
  - `reset_ekf(self)`
  - `run(self)`
  - `set_parking(self)`
  - `unset_parking(self)`
- `class TagMeasurementModel`
  - `get_err(self, measurement, predicted_state)`
  - `get_observation_mat(self, x)`
  - `normalize(self, x)`
  - `predict(self, x)`
- `class TagPose`
  - `publish_pose(self, pose)`
  - `run(self)`
  - `set_parking(self)`
  - `unset_parking(self)`
- `class TagRotationEkf`
  - `add_gyro_data(self, gyro)`
  - `add_tag_rotation(self, qCA, qYA, qLC, pside)`
  - `get_tag_rotation(self)`

**ati/perception/utils/tag_ps4_setup.py**

- `class Encoder(object)`
  - `run(self, topic, update)`

**ati/perception/utils/tag_pub.py**

- `class MuleStatus(object)`
  - `run(self, topic, update)`

**ati/perception/utils/transform.py**

- `class Transform`
  - `get_relative_transform(self, reference_transform)`
  - `get_z(self)`
  - `rotation(self)`
  - `transform_from_reference(self, pc)`
  - `transform_to_reference(self, pc)`
  - `translation(self)`

**ati/peripherals/peripherals_utils.py**

- `class AutoUnhitch(Device)`
  - `activate_device(self) → Any`
  - `actuate_on_request(self, hitch: bool, ignore_current_check: bool) → Any`
  - `is_device_working(self)`
  - `maybe_send_delfino_cmd(self)`
  - `publish_delfino_unhitch_cmd(self)`
  - `read_device_current(self)`
  - `send_confirmation_msg(self)`
  - `send_failure_msg(self)`
- `class Conveyor(Device)`
  - `activate_device(self) → Any`
  - `send_conveyor_ack(self, ack)`
  - `send_conveyor_failure_msg(self)`
- `class Device(Thread)`
  - `run(self)`
- `class DispatchButton(Device)`
  - `activate_device(self) → Any`
  - `post_mule_msg(self) → Any`
  - `toggle_pause_state(self) → Any`
- `class Indicator(Device)`
  - `activate_device(self) → Any`
  - `generate_indicator_msg(self, pattern)`
  - `send_indicator_command(self, indicator_pattern)`
- `class LifterActuator(Device)`
  - `activate_device(self) → Any`
  - `actuate_on_request(self, lift_signal)`
  - `drop_prongs(self)`
  - `send_confirmation_msg(self, lift)`
  - `send_lifter_status(self, lift)`
- `class Speaker(Device)`
  - `activate_device(self) → Any`
- `class TimeoutDispatch(Device)`
  - `activate_device(self) → Any`
  - `post_mule_msg(self) → Any`

**ati/pyschema/bbox.py**

- `class BBox2D`
  - `get_bbox2D_schema(self)`
- `class BBox3D`
  - `add_global_pose(self, mule_pose)`
  - `get_corners(self)`
  - `get_label_str(self)`
  - `get_object3D_schema(self)`

**ati/pyschema/control_status.py**

- `class ControlStatus`
  - `is_reversing(self)`

**ati/pyschema/path_occupancy.py**

- `class PathOccupancy`

**ati/pyschema/payload_info.py**

- `class PayloadInfo`
  - `clear_pose(self)`
  - `corners(self)`
  - `update_info(self, pose, length, width)`
  - `xlim(self)`
  - `ylim(self)`

**ati/pyschema/pose.py**

- `class SherpaPose`
  - `get_global_pose(self, local_pose)`
  - `pose_2d(self)`
  - `pose_2d_schema(self)`

**ati/pyschema/sensor_data.py**

- `class CamData(SensorData)`
  - `from_front_cam(self)`
  - `from_rear_cam(self)`
- `class Lidar2DData(SensorData)`
- `class LidarData(SensorData)`
  - `is_empty(self)`
- `class SensorData`
- `class TofData(SensorData)`
- `class UltrasoundData(SensorData)`

**ati/pyschema/vehicle_config.py**

- `class VehicleParams`
  - `does_vehicle_lift_payload(self)`
  - `get_payload_frontface_pose_once_lifted(self, payload_width, payload_length, ref)`
  - `is_pronged_vehicle(self)`
  - `is_vehicle_lifter(self)`
  - `is_vehicle_pallet_mover(self)`
  - `is_vehicle_pivot_monofork(self)`
  - `set_vehicle_limits(self, mule_box)`

**ati/safety/device_monitor.py**

- `class BusReader(threading.Thread)`
  - `process_camera_msg(self, msg)`
  - `process_generic_msg(self, msg)`
  - `process_lidar_msg(self, msg)`
  - `process_wheel_enc(self, msg)`
  - `run(self)`

**ati/schema/__init__.py**

- `class InvalidMessage(Exception)`
- `class InvalidTopic(Exception)`

**ati/scripts/core_odometer.py**

- `class Odometer`
  - `update_db_if_needed(self)`
  - `update_distance(self, v, timestamp)`

**ati/scripts/record_sensors.py**

- `class ArucoMulePoseRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class ArucoRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class BatteryBusRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class BatteryRecorder(GenericRecorder)`
  - `data_callback(self, topic, update)`
- `class Bbox2DRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class BiasFreeGyroRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class CANHealthRecorder(ProtoReflectionRecorder)`
- `class CSVRecorder(object)`
- `class CanSendRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class CandPathRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class ControlBusRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class ControlStatusRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class CurrentsRecorder(ProtoReflectionRecorder)`
- `class DrivableRegionRecorder(object)`
  - `callback(self, topic, update)`
- `class DriveRecorder(ProtoReflectionRecorder)`
- `class EkfOdoRecorder(ProtoReflectionRecorder)`
- `class EkfVWRecorder(ProtoReflectionRecorder)`
- `class FrenetRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class GenericPBRecorder`
  - `callback(self, topic, update)`
  - `get_new_fd(self)`
- `class GenericRecorder(object)`
  - `cleanup(self)`
  - `data_callback(self, topic, update)`
- `class GyroBiasRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class HallSensorRecorder(ProtoReflectionRecorder)`
- `class HitchPoseRecorder(ProtoReflectionRecorder)`
- `class HumanObstacleRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class IMURecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class Lidar2dRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class LidarBaseRecorder(object)`
  - `callback(self, topic, update)`
  - `check_lookup(self)`
  - `lookup_callback(self, topic, update)`
- `class LidarCombinedRecorder(object)`
  - `callback(self, topic, update)`
- `class LidarExtraRecorder(LidarBaseRecorder)`
- `class LidarGroundRecorder(object)`
  - `callback(self, topic, update)`
- `class LidarIsaacRecorder(object)`
  - `callback(self, topic, update)`
- `class LidarPbRecorder(LidarBaseRecorder)`
- `class LidarSmallRecorder(LidarBaseRecorder)`
  - `check_lookup(self)`
- `class LidarSmallRecorderFull(LidarSmallRecorder)`
- `class LifterSensorStatusRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class LinakActuatorRecorder(ProtoReflectionRecorder)`
- `class LivoxLidarRecorder(object)`
  - `callback(self, topic, update)`
- `class MonocularDepthEstimateRecorder(GenericPBRecorder)`
- `class MotorCanDebugRecorder(ProtoReflectionRecorder)`
- `class MuleLogRecorder`
  - `flush(self)`
  - `log_writer(self)`
  - `maybe_write_entry(self)`
- `class NoRecorder(object)`
- `class Object3D(GenericPBRecorder)`
- `class ObstacleRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class OdoRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class PathOccupancyRecorder(object)`
  - `callback(self, topic, update)`
- `class PayloadPoseRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class PerfRecorder(object)`
  - `run(self)`
- `class PeripheralsRecorder(ProtoReflectionRecorder)`
- `class PowerBoardRecorder(ProtoReflectionRecorder)`
- `class ProcessPerfRecorder(object)`
  - `run(self)`
- `class ProtoReflectionRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class RouteTypeRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class SafetyExceptionRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class SensorExceptionRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class SlipRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class Status`
- `class StatusRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class SteerCurrentsRecorder(ProtoReflectionRecorder)`
- `class SummaryRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class SystemRecorder(ProtoReflectionRecorder)`
- `class TPMSensorRecorder(ProtoReflectionRecorder)`
- `class TablePoseRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class TagLocalRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class TagMulePoseRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class TagPoseRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class TagRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class TrolleyPoseRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class UltrasoundRecorder(CSVRecorder)`
  - `callback(self, topic, update)`
- `class WheelEncDebugRecorder(ProtoReflectionRecorder)`
- `class WheelEncRecorder(ProtoReflectionRecorder)`
  - `callback(self, topic, update)`

**ati/scripts/utils/recorder_bus.py**

- `class AsyncBus(object)`
  - `run(self)`
  - `run_background(self)`
  - `subscribe(self, topic, callback, queue_size)`
- `class QueueCallbackConsumer(threading.Thread)`
  - `run(self)`

**ati/scripts/utils/types.py**

- `class PointCloud2`
- `class PointField`

**ati/slam/imu_tracker/ImuTracker.py**

- `class ImuTracker`
  - `add_imu_data(self, imu_data)`
  - `get_cumulative_quaternion(self, gyro_buffer, dt)`
  - `get_gyro_quaternion(self, upto_time)`
  - `get_initial_gyro_bias(self, imu_data)`
  - `get_rolling_gyro_bias(self, imu_data)`
  - `get_z(self, debug)`
  - `publish_bias_free_gyro(self, gyro, ts)`
  - `publish_exception(self, msg_string, message_id)`
  - `publish_gyro_bias(self)`
  - `reset_imu_tracking_params(self)`
  - `reset_previous_timestamp(self, timestamp)`
  - `start_tracking_z(self)`
  - `stop_bias_publish_thread(self)`
  - `stop_tracking_z(self)`

**ati/slam/lidar_marker3d/grid3d.py**

- `class Grid3D`
  - `compute_level_mapping(self, start_level, max_levels)`
  - `get_score(self, pts)`
  - `insert_misses(self, miss_points, only_unknown)`
  - `insert_points(self, points, compact, resize)`
  - `maybe_resize_grid(self, grid_inds, compact)`
  - `search(self, pts, search_space)`
  - `set_grid(self, grid)`
  - `set_level_lookup_type(self, lookup_type)`
  - `transform_to_grid(self, points, only_grid_bounds)`
  - `update_max_score(self)`

**ati/slam/localization_check.py**

- `class WheelTracker`
  - `integrate_from_time(self, pose, lidar_y_offset)`
  - `reset(self)`
  - `trim_to_window(self, start_time, end_time)`
  - `update(self, msg)`

**ati/slam/yelli/grid.py**

- `class Grid2D`
  - `apply_median_filter(self, kernel_size)`
  - `compute_level_mapping(self, start_level, max_levels)`
  - `insert_misses(self, pose, miss_pts)`
  - `insert_points(self, pose, frame, resize)`
  - `linear_transform(self, t1)`
  - `search(self, frame, search_space, count_once)`
  - `set_grid(self, grid)`
  - `set_level_lookup_type(self, lookup_type)`
  - `set_neighbourhood_search(self, on)`
  - `set_zgrid(self, z_grid)`
  - `transform_local_to_grid(self, frame, pose)`
  - `transform_world_to_grid(self, frame)`

**ati/slam/yelli/grid2cuda.py**

- `class Grid2DCuda(Grid2D)`
  - `insert_misses(self, pose, miss_pts)`
  - `insert_points(self, pose, frame, resize)`
  - `search(self, frame, search_space, count_once)`
  - `set_as_numpy_grid(self)`
  - `set_grid(self, grid)`
  - `set_zgrid(self, z_grid)`

**ati/slam/yelli/hdf5_grid.py**

- `class Hdf5_grid`
  - `insert_misses(self, pose, miss_pts)`
  - `insert_points(self, pose, frame)`
  - `linear_transform(self, t1)`
  - `maybe_reload_grid(self, pose, blocking, write)`
  - `reload_grid(self, load_dist, pose, write)`
  - `search(self, frame, search_space, count_once)`
  - `set_level_lookup_type(self, lookup_type)`
  - `set_neighbourhood_search(self, on)`
  - `set_zgrid(self, z_grid)`
  - `write_current_grid(self)`
  - `write_metadata(self, map_meta)`

**ati/slam/yelli/multigrid.py**

- `class MultiGrid`
  - `apply_median_filter(self, kernel_size)`
  - `construct_hierarchical_grids(self, num_levels)`
  - `insert_misses(self, miss_beams, pose)`
  - `insert_points(self, beams, pose)`
  - `load_map(folder, dtype, level, min_dist, max_dist, zslice, cuda, level_lookup_type)`
  - `save_map(self, folder)`
  - `search(self, beams, search_space)`
  - `set_maps(self, grid_alpha)`
  - `set_neighbourhood_search(self, on)`
  - `split_frame(self, frame)`
  - `transform_scores(self)`
- `class MultiGridCuda(MultiGrid)`
  - `set_maps(self, grid_alpha)`
- `class Submap`
  - `compress_data(self)`
  - `decompress_data(self)`
  - `finish(self, min_score_threshold)`
  - `get_submap_score(self)`
  - `insert_misses(self, miss_pts, pose)`
  - `insert_points(self, frame, pose, frame_id, node_id)`
  - `search(self, frame, search_space, count_once)`
  - `set_level_lookup_type(self, lookup_type)`
- `class SubmapManager`
  - `finish(self)`
  - `get_current_submap(self)`
  - `insert_points(self, pose, points, frame_id, score)`
  - `load_finished_submaps(self, map_dir)`
  - `save(self, map_dir)`
- `class TiledMultiGrid(MultiGrid)`
  - `initialize_new_map(tiled_map_folder)`
  - `load_map(folder, level, min_dist, max_dist, zslice, cuda, level_lookup_type, num_buffer_tiles)`
  - `maybe_reload_grid(self, pose, blocking, write)`
  - `save_map(self)`
  - `write_current_grid(self)`

**ati/slam/yelli/posegraph_utils.py**

- `class Constraint`
- `class PoseGraphOptimization(g2o.SparseOptimizer)`
  - `add_edge(self, vertices, measurement, information, robust_kernel)`
  - `add_edge_from_state(self, vertices, information, robust_kernel)`
  - `add_vertex(self, id, pose, fixed)`
  - `get_pose(self, id)`
  - `optimize(self, max_iterations)`

**ati/slam/yelli/yelli_tracker.py**

- `class YelliState`
  - `calc_initial_pose_estimate(self, frame_id)`
  - `calc_next_pose_estimate(self, frame_id, frame_time)`
  - `check_imu_samples(self, frame_time, frame_id)`
  - `check_lidar_missing_sectors(self, message)`
  - `check_sufficient_points(self, filtered_frame, frame_id)`
  - `check_wheel_encoder_data(self, frame_id)`
  - `check_wrong_config(self)`
  - `get_topics(self)`
  - `initial_search(self, beams)`
  - `initialize_counters(self)`
  - `load_map(self)`
  - `maybe_crop(self)`
  - `maybe_reload_map(self)`
  - `post_process(self)`
  - `process_control_status(self, message)`
  - `process_imu(self, message)`
  - `process_lidar_frame(self, message)`
  - `process_mule_status(self, message)`
  - `process_wheel_encoder(self, message)`
  - `publish_debug(self, start_time)`
  - `publish_pose(self, processing_time, start_time)`
  - `read_livox_packet(self, message)`
  - `ready_pose_estimation(self, message)`
  - `regular_search(self, beams)`
  - `reset_params(self, processing_time)`
  - `stale_lidar_data(self, frame_time)`
  - `subscribe_topics(self)`

**ati/stubs/control_states.py**

- `class MuleStateMonitor(object)`
  - `record_mule_state(self, topic, msg)`

**ati/stubs/drivable.py**

- `class DrivableStub`
  - `record_drivable_region(self, topic, dr)`

**ati/stubs/encoder.py**

- `class EncoderStub(object)`
  - `get_encoder_data(self, topic, update)`

**ati/stubs/exceptions.py**

- `class SensorException(object)`
  - `get_safety_exception(self)`
  - `record_exceptions(self, topic, data)`
  - `record_safety_exception(self, topic, data)`
  - `record_sensor_status(self, topic, data)`

**ati/stubs/lifter_sensor.py**

- `class LifterSensorStub`
  - `get_lifter_sensor_status(self, topic, data)`

**ati/stubs/objects.py**

- `class ObjectsStub`
  - `filter_by_expiry_time(self)`
  - `get_objects(self)`
  - `process_objects(self, topic, msg)`

**ati/stubs/odometry.py**

- `class Odometry(object)`
  - `run(self, topic, update)`

**ati/stubs/pause_command.py**

- `class PauseCommandStub`
  - `get_pause_command(self, topic, data)`

**ati/stubs/payload_pose.py**

- `class PayloadPoseStub`
  - `dest_platform_pose_callback(self, topic, data)`
  - `payload_pose_callback(self, topic, data)`
  - `publish_close_to_payload_status(self, close_status)`
  - `start_platform_pose_callback(self, topic, data)`
  - `update_close_to_payload_status(self, mule_pose)`
  - `update_payload_pose(self, vehicle_params, mule_pose)`
  - `update_payload_pose_redis(self)`

**ati/stubs/route_type.py**

- `class RouteTypeStub`
  - `get_route_type_status(self, topic, data)`

**ati/tools/diagnostics/diag_utils.py**

- `class DrivablePb(GenericPb)`
  - `get_drivable(self, frame_id)`
- `class GenericPb`
  - `close(self)`
  - `list_frames(self)`
  - `num_frames(self)`
  - `num_packets(self)`
  - `reset(self)`
- `class LidarSmallPb(GenericPb)`
  - `get_frame(self, nl)`
  - `get_frame_extended(self, nl)`
  - `get_lookup(self)`
  - `get_version(self)`
  - `get_vertical_angles(self)`
  - `list_frames(self)`
  - `num_frames(self)`
- `class PathOccupancyPb(GenericPb)`
  - `get_data(self, frame_id)`
  - `num_frames(self)`
  - `process(self)`

**ati/tools/diagnostics/diagnostics_summary.py**

- `class DiagnosticsThread(threading.Thread)`
  - `run(self)`

**ati/tools/diagnostics/encoder_diagnostics.py**

- `class EncoderData`
  - `creating_np_array_for_encoder(self)`
  - `len_data_check(self)`
- `class enc_and_motor_check`
  - `abs_encoder_failure_check(self)`
  - `appending_results_to_text_file(self)`
  - `compute_score(self, history, measurement)`
  - `encoder_check(self)`
  - `encoder_disconnection_check(self, overshoot_score_list, en_data)`
  - `get_measurement(self, ticks, ticks_ref)`
  - `get_measurement_steer(self, ticks, ticks_ref)`
  - `get_overshoot_stall_count(self)`
  - `get_overshoot_stall_steer_score(self)`
  - `hub_motor_check(self)`
  - `missing_enc_data_check_at_low_level(self, enc_time)`
  - `motor_stall_check(self, encoder_1_stall_score_list, encoder_2_stall_score_list, encoder_1, encoder_2)`
  - `one_encoder_failure_when_other_reports_overshoot(self, encoder_1_overshoot_score_list, encoder_2_stall_score_list, encoder_2_data)`
  - `overall_check(self)`
  - `overshoot_count(self, overshoot_score_list, en_data)`
  - `printing_results_of_enc_and_motor_check(self)`
  - `process_abs_enc_message(self)`
  - `process_enc_message(self, en_data, spurious_i)`
  - `runaway_check_ov(self, encoder_1_overshoot_score_list, encoder_2_overshoot_score_list, encoder_1_data, encoder_2_data, diff_1, diff_2)`
  - `spurious_data_check(self)`
  - `stall_count(self, stall_score_list, en_data)`

**ati/tools/diagnostics/perf_diagnostics.py**

- `class BatteryData`
  - `creating_np_array_for_battery(self)`
- `class PerfData`
  - `creating_np_array_for_perf(self)`

**ati/tools/diagnostics/utils/diag_utils.py**

- `class DrivablePb(GenericPb)`
  - `get_drivable(self, frame_id)`
- `class GenericPb`
  - `close(self)`
  - `list_frames(self)`
  - `num_frames(self)`
  - `num_packets(self)`
  - `reset(self)`
- `class LidarSmallPb(GenericPb)`
  - `get_frame(self, nl)`
  - `get_frame_extended(self, nl)`
  - `get_lookup(self)`
  - `get_version(self)`
  - `get_vertical_angles(self)`
  - `list_frames(self)`
  - `num_frames(self)`
- `class PathOccupancyPb(GenericPb)`
  - `get_data(self, frame_id)`
  - `num_frames(self)`
  - `process(self)`

**ati/tools/diagnostics/utils/drivable_grid.py**

- `class DriveGrid2D`
  - `add_obstacle_points(self, pose, pts_list, mule_corners, use_cuda)`
  - `add_pts_cupy(self, pts, pose, grid, value, ht_grid)`
  - `apply_nogo(self, grid, sensor)`
  - `clear_mule_shape(self, grid, mule_corners)`
  - `create_db_grid(self)`
  - `get_grid_corners(self)`
  - `reset(self)`
  - `transform_grid_to_world(self, frame)`
  - `transform_local_to_world(self, pose, frame)`
  - `transform_world_to_grid(self, frame)`
  - `update(self, pose, ground, nonground, lidar_seq, fill, blur, nevery, decay)`
  - `validate(self, data)`
  - `validate_xyz(self, data)`

**ati/tools/gmaj_creator.py**

- `class WPS2Graph`
  - `get_gmaj_objects(self)`
  - `get_junction_pose(self, node_id)`
  - `get_stations_info_dict(self)`

**ati/tools/loadcell/libraries/Adafruit_GFX_Library/fontconvert/bdf2adafruit.py**

- `class Glyph`

**ati/tools/mcap_visualisation/ati_mcap.py**

- `class AtiMCap(McapCreator)`
  - `add_cam_obstacle_data(self)`
  - `add_lidar_obstacle_data(self)`
  - `add_obstacle_data(self)`
  - `create(self, fn_start, fn_end, step)`
  - `fetch_drivable_data(self, fn)`
  - `fetch_objects(self, fn)`
  - `fetch_sensor_data(self, fn)`
  - `init_drivable_reader(self)`
  - `init_mdd(self)`
  - `init_objects_reader(self)`
  - `register_all_feeds(self)`
  - `write_drivable_data(self)`
  - `write_objects(self)`

**ati/tools/mcap_visualisation/mcap_creator.py**

- `class McapCreator(MCapWriter)`
  - `add_bbox3d(self, bbox3d, add_text)`
  - `add_cube(self, cube_pb2)`
  - `add_text(self, text_pb2)`
  - `end_frame(self, ts)`
  - `register_drivable(self, sz)`
  - `register_ego_pcs(self, psd)`
  - `register_new_pc_channel(self, pc_channel_name)`
  - `register_obstacle_images(self, cam_ids, sz)`
  - `register_obstacle_pcs(self, psd)`
  - `register_perception_sensors(self, psd, online)`
  - `write_pc_with_transforms(self, ts, frame, msg_topic, metadata)`
  - `write_sensor_data(self, lidar_data, cam_datas)`

**ati/tools/mcap_visualisation/mcap_json.py**

- `class MCapWriter`
  - `get_pc_json(self)`
  - `register_pc_schema(self, name, topic)`
  - `write_pc(self, pc_json, frame_ts, frame, pc_id)`

**ati/tools/mcap_visualisation/mcap_proto.py**

- `class MCapWriter`
  - `add_all_channels_to_ws_server(self, server)`
  - `add_ws_frames_transforms_channel(self)`
  - `add_ws_img_channel(self, cam_str)`
  - `add_ws_pc_channel(self, point_cloud_src)`
  - `add_ws_scene_update_channel(self)`
  - `clear_frame_transforms(self)`
  - `get_timestamp(self, ts)`
  - `register_camera(self, cam_str, width, height, camera_matrix)`
  - `send_frame_transforms(self, ts)`
  - `set_pc_fields(self, point_cloud_src, pose, orientation_q)`
  - `update_frame_transforms(self, ts, parent_frame_id, child_frame_id)`
  - `write_camera_frame(self, cam_str, img_ts, img, encoding)`
  - `write_key_value_pair(self, ts, key, value, topic)`
  - `write_message(self, message, topic, ts)`
  - `write_pc(self, frame_ts, frame, point_cloud_src, metadata)`
  - `write_scene_update(self, src, ts, cubes, texts)`

**ati/tools/mcap_visualisation/mcap_ws.py**

- `class Listener(FoxgloveServerListener)`
  - `on_subscribe(self, server: FoxgloveServer, channel_id: ChannelId)`
  - `on_unsubscribe(self, server: FoxgloveServer, channel_id: ChannelId)`

**ati/tools/reader/camera.py**

- `class ColorPBReader(PBReaderBase)`
  - `get_nth_image(self, n)`
- `class DepthPBReader(PBReaderBase)`
  - `get_nth_image(self, n)`
- `class DepthTruncFromVideo`
  - `convert_to_depth_grayscale(self, ret, img)`
  - `get_image_at_time(self, ts)`
  - `get_next_image(self)`
  - `get_start_time(self, dataset)`
  - `get_vid_readers(self, vid_str)`
- `class Image_from_mp4`
  - `get_cam_start(self)`
  - `get_duration(self)`
  - `get_image_at_time(self, ts)`
  - `get_next_image(self)`
  - `get_vid_objects(self)`
- `class MonocularDepthPB(GenericPBV2)`
  - `get_inverse_depth_relative(self, ts)`
- `class PBReaderBase`
  - `get_image_at_time(self, ts)`
  - `get_nth_image(self, n)`
- `class StereoImage_from_mp4`
  - `get_cam_start(self)`
  - `get_duration(self)`
  - `get_image_at_time(self, ts)`
  - `get_next_image(self)`
  - `get_vid_objects(self)`
  - `split_rl(self, frame)`
- `class video_reader`
  - `get_frame_at_time(self, ts)`
  - `get_next_frame(self)`
  - `get_nth_frame(self, n)`
  - `reset(self)`
  - `video_duration(self)`

**ati/tools/reader/csv_reader.py**

- `class Bbox2DCSVReader`
  - `get_bbox2D(self, fn)`
- `class DebugCSVReader`
  - `get_frenet_paths(self, frame_id)`
  - `get_lifter_status(self, fn)`
  - `get_obstacle_stoppages(self)`
  - `get_payload_info(self, ts, delta_ts, local_coordinates)`
  - `get_pose(self, fn)`
  - `get_reference_path(self, n1, n2)`
  - `get_reference_path_dist(self, fn, d, before, max_frames)`
  - `get_roll_pitch(self, frame_number)`
  - `get_safety_exceptions(self, ts, delta_ts)`
  - `get_sensor_exceptions(self, ts, delta_ts)`
  - `get_v_w(self, frame_number)`
  - `get_yelli_path(self, n1, n2)`
  - `load_frenet_paths(self)`
  - `load_lifter_sensor_data(self)`
  - `load_payload_data(self)`
  - `load_safety_exceptions_data(self)`
  - `load_sensor_exceptions_data(self)`
  - `load_stoppage_data(self)`
  - `load_summary_data(self)`
  - `load_tracker(self)`
  - `load_trip_log_data(self)`
  - `load_yelli_data(self)`

**ati/tools/reader/drivable_reader.py**

- `class DrivableDataReader(GenericPb)`
  - `get_data(self, frame_id)`
  - `get_data_v1(self, frame_id)`
  - `get_drivable(self, frame_id, version)`

**ati/tools/reader/generic_pb.py**

- `class GenericPBV2`
  - `close(self)`
  - `get_data_fn(self, fn)`
  - `get_data_ts(self, ts, max_latency)`
  - `open_relevant_fds(self)`

**ati/tools/reader/lidar_pb.py**

- `class GenericLidarPb(GenericPb)`
  - `get_frame(self, frame_id)`
  - `get_lidar_type(self)`
  - `list_frames(self)`
  - `num_frames(self)`
- `class GenericPb`
  - `close(self)`
  - `list_frames(self)`
  - `num_frames(self)`
  - `num_packets(self)`
  - `reset(self)`
  - `store_as_bin_file(self, frame, file_path)`
  - `store_as_pcd_file(self, frame, file_path)`
- `class GroundMaskPb(GenericPb)`
  - `get_mask(self, frame_id)`
- `class LidarCompletePb(LidarSmallPb)`
  - `get_frame(self, nl)`
  - `get_frame_extended(self, nl)`
- `class LidarExtraPb(GenericPb)`
  - `get_frame(self, nl)`
- `class LidarSmallPb(GenericLidarPb)`
  - `apply_transforms(self, frame, transforms, config)`
  - `get_frame(self, nl, ext, apply_transforms, transforms, config)`
  - `get_frame_extended(self, nl, apply_transforms, transforms, config)`
  - `get_lookup(self)`
  - `get_version(self)`
  - `get_vertical_angles(self)`
- `class LivoxLidarPb(GenericLidarPb)`
  - `get_frame(self, frame_id)`
  - `get_next_raw_packet(self)`
  - `get_packet(self, packet_id)`
  - `get_packet_at_time(self, ts)`
  - `get_packet_ext(self, packet_id)`
  - `get_packets(self, packet_id, n)`
  - `get_packets_ext(self, packet_id, n)`
  - `get_version(self, packet)`
  - `list_frames(self)`
  - `num_frames(self)`
- `class LivoxMergedLidarPb(GenericLidarPb)`
  - `close(self)`
  - `get_individual_frame(self, frame_id, lidar_id, n)`
  - `get_packets(self, lidar_pb, packet_id, n)`
  - `list_frames(self)`
  - `num_frames(self)`
- `class PathOccupancyPb(GenericPb)`
  - `get_data(self, frame_id)`
  - `num_frames(self)`
  - `process(self)`
- `class SingleBeamLidarPb(GenericPb)`
  - `get_frame(self, frame_id)`
  - `get_frame_ts(self, ts)`
  - `num_frames(self)`
  - `process(self)`
  - `set_inverted(self, inverted)`

**ati/tools/reader/object_pb.py**

- `class ObjectPB(GenericPBV2)`
  - `get_bbox3ds(self, fn)`
  - `get_objects(self, fn)`

**ati/tools/reader/path_occupancy_reader.py**

- `class PathOccupancyReader(GenericPb)`
  - `get_data(self, fn)`
  - `get_path_occupancy(self, frame_id)`
  - `get_payload_info(self, path_occupancy)`
  - `get_platform_info(self, path_occupancy)`
  - `is_payload_info_present(self, path_occupancy)`
  - `is_platform_info_present(self, path_occupancy)`
  - `num_frames(self)`

**ati/tools/reader/perception_sensors.py**

- `class ConsolidateCamReader`
  - `fetch_color_data(self, ts)`
  - `fetch_data(self, ts)`
  - `fetch_depth_data(self, ts)`
  - `fetch_monocular_depth(self, ts)`
  - `fetch_sliced_data(self, frame_number)`
  - `fetch_stereo_data(self, ts)`
  - `get_cam_data_processor(self)`
  - `get_depth_reader(self)`
  - `get_mono_depth_reader(self)`
  - `get_rgb_reader(self)`
  - `get_stereo_cam_reader(self)`
  - `is_depth_pb_recorded(self)`
- `class ConsolidatedLidarReader`
  - `add_spherical_coordinates_to_frame(self)`
  - `correct_for_ego_motion(self, frame_number)`
  - `correct_for_ego_roll_pitch(self, frame_number)`
  - `fetch_data(self, frame_number)`
  - `get_livox_frames(self, frame_number)`
  - `get_ouster_frames(self, frame_number)`
  - `list_frames(self)`
  - `merge_frames(self)`
  - `transform_frames(self)`
- `class Lidar2DReader`
  - `fetch_data(self, frame_number)`
- `class PerceptionSensorsData`
  - `fetch_cam_data(self, ts)`
  - `fetch_cam_data_sliced(self, frame_number)`
  - `fetch_lidar_2d_data(self, frame_number)`
  - `fetch_lidar_data(self, frame_number)`
  - `fetch_ultrasonic_data(self, frame_number)`
  - `get_cam_data(self, cam_str, ts)`
  - `get_cam_data_sliced(self, cam_str, frame_number)`
  - `get_cam_reader(self, cam_str)`
  - `get_lidar_type(self)`
  - `list_frames(self)`
- `class UltrasonicReader`
  - `fetch_data(self, frame_id)`

**ati/tools/reader/perception_sensors_online.py**

- `class BusReader(threading.Thread)`
  - `modify_lidar_settings(self, lidar_settings)`
  - `process_control_status(self, raw_msg)`
  - `process_livox_lidar_frame(self, raw_msg)`
  - `process_objects(self, raw_msg)`
  - `process_ouster_lidar_frame(self, raw_msg)`
  - `process_yelli_odo(self, raw_msg)`
  - `run(self)`
  - `should_process_livox_msg(self, raw_msg)`
- `class PerceptionBusReader`
  - `are_threads_alive(self)`
  - `get_cam_data(self, cam_str, depth_data)`
  - `get_cam_lidar_yelli_data(self, cam_str)`
  - `get_cam_reader(self, cam_str)`
  - `get_cam_yelli_data(self, cam_str, depth_data)`
  - `get_color_cam_data(self, cam_str, cam_data)`
  - `get_depth_cam_data(self, cam_str, cam_data)`
  - `get_depth_cam_reader(self, cam_str)`
  - `get_lidar_data(self)`
  - `get_lidar_data_fast(self)`
  - `get_lidar_type(self)`
  - `get_yelli_data(self)`
  - `start_readers(self)`

**ati/tools/visualizer/obstacle_detection.py**

- `class Datafetcher`
  - `get_drivable_grids(self, fn, recreate)`
  - `get_frenet_paths(self, vis, frame_id)`
  - `get_recorded_drivable_data(self, fn)`
  - `get_recorded_path_occupany_data(self, fn)`
  - `get_reference_path(self, vis, fn, d)`
  - `process_sensor_data(self)`
  - `set_sensor_data(self, fn)`
  - `toggle_on_ramp_behaviour(self, on_ramp)`
- `class Plotter`
  - `add_drivable_grids(self, frame_id)`
  - `add_frenet_candidate_paths(self, vis, frame_id, show_mule_rectangle, show_all_paths)`
  - `add_global_obstacle(self)`
  - `add_ground_obstacle_segmentation_plot(self)`
  - `add_mule(self)`
  - `add_mule_box(self, dr, grid, pose, mule_box, value)`
  - `add_path_mask(self)`
  - `add_payload_mask(self)`
  - `add_reference_path(self)`
  - `get_global_pose(self, dr)`
  - `get_local_obstacle(self, margin)`
  - `plot_estimated(self, fig, estimated_trajectory, row, col)`
  - `show_clustering_grids(self, frame_id)`
  - `show_details(self, frame_id)`
  - `show_safety_exceptions(self)`
  - `show_sensor_exceptions(self)`

**ati/tools/visualizer/sanity.py**

- `class Sensor`

**ati/tools/visualizer/sensor_fov.py**

- `class Sensor`

**ati/tools/visualizer/visualizer.py**

- `class Visualizer`

**ati_core/mule_services/usb_monitor.py**

- `class USBDeviceMonitor`
  - `get_device_info(self, device)`
  - `handle_device_addition(self, device)`
  - `handle_device_removal(self, device)`
  - `is_critical_device(self, device)`
  - `start_monitoring(self)`

**epo/epo_v3_utils.py**

- `class BatteryInfo`

**mule_analytics/analytics_handlers.py**

- `class AnalyticsHandler`
  - `get_req_handler(self, req)`
  - `handle(self, req)`
  - `handle_battery(self, req)`
  - `handle_cpu(self, req)`
  - `handle_encoder(self, req)`
  - `handle_events(self, req)`
  - `handle_lidar(self, req)`
  - `handle_network(self, req)`
  - `handle_runs(self, req)`
  - `handle_sw_perf_temp(self, req)`
  - `record_msg_recv(self, req)`

**mule_analytics/analytics_msg_processor.py**

- `class AnalyticsMsgProcessor`
  - `get_request_class(self, req_type)`
  - `process_message(self, message)`
  - `run(self)`

**mule_analytics/db_session.py**

- `class DBSession`
  - `add_battery(self, battery)`
  - `add_events(self, event)`
  - `add_health(self, health_report_details)`
  - `add_runs(self, run)`
  - `add_sw_history(self, sw_history)`
  - `add_to_session(self, obj)`
  - `add_trip_log(self, trip_log)`
  - `close(self, commit)`
  - `commit(self)`
  - `delete_old_sw_tags(self)`
  - `drop_tables(self)`
  - `get_odometry(self)`
  - `get_previous_run_id(self)`
  - `get_sw_history(self, sw_tag)`
  - `get_sw_tags(self)`
  - `has_alembic_version(self)`
  - `update_sw_history(self, sw_id, sw_tag, odo_dist)`

**mule_analytics/models/analytics_models.py**

- `class events(Base)`
- `class network(Base)`
- `class runs(Base)`
- `class sw_perf_temp(Base)`

**mule_analytics/models/base_models.py**

- `class odometry(Base)`
- `class ops_history(Base)`
- `class sw_history(Base)`

**mule_analytics/models/request_models.py**

- `class BatteryReq(ClientReq)`
- `class CPUReq(ClientReq)`
- `class ClientReq(BaseModel)`
- `class EncoderReq(ClientReq)`
- `class EventsReq(ClientReq)`
- `class LidarReq(ClientReq)`
- `class NetworkReq(ClientReq)`
- `class RunsReq(ClientReq)`
- `class SWPerfTempReq(ClientReq)`

**mule_analytics/models/sensor_models.py**

- `class Battery(Base)`
- `class cpu(Base)`
- `class encoder(Base)`
- `class lidar(Base)`

**mule_comms/comms_orchestrator.py**

- `class Orchestrator`
  - `kill(self)`
  - `proc_communicate(self, proc_name, proc)`
  - `start(self)`
  - `stop(self)`
  - `terminate(self)`

**mule_comms/fleet_bridge_utils.py**

- `class AppContext`
  - `empty_queue(self, q: asyncio.Queue)`
  - `get_all_request_kwargs(self, req_json, files, params, retry_after, response_type)`
  - `get_all_ws_kwargs(self)`
  - `get_fq_http_url(self, url)`
  - `get_fq_ws_url(self, url)`
  - `get_static_file_auth(self)`
  - `push_to_tx_queue(self, msg)`
  - `update_config(self)`

**mule_comms/hmi_bridge/hmi_bridge_utils.py**

- `class AppContext`
  - `send_to_hmi_frontend(self, msg)`
- `class DebounceManager`
  - `should_send(self, message_type: str) → bool`

**mule_comms/hmi_bridge/hmi_handler.py**

- `class Handler`
  - `calculate_angle(self, bot_x: float, bot_y: float, obstacle_x: float, obstacle_y: float, bot_heading: float) → float`
  - `calculate_distance(self, x1: float, y1: float, x2: float, y2: float) → float`
  - `check_recently_changed(self, timeout_seconds)`
  - `clear_obstacles(self)`
  - `find_closest_point(self, x, y)`
  - `get_closest_obstacle(self) → dict`
  - `get_obstacle_info_string(self, obstacle: dict) → str`
  - `get_obstacles_in_range(self, max_distance: float) → list`
  - `handle(self, msg)`
  - `handle_action_terminate_trip(self, msg)`
  - `handle_set_alerts(self, msg)`
  - `handle_set_bot_position(self, msg)`
  - `handle_set_mule_error(self, msg)`
  - `handle_set_network_stats(self, msg)`
  - `handle_set_obstacle_detection(self, msg)`
  - `handle_set_sherpa_status(self, msg)`
  - `handle_set_trip_description(self, msg)`
  - `handle_set_trip_status(self, msg)`
  - `process_obstacle_detection(self, obstacle_data: dict) → dict`
  - `set_recently_changed(self)`
  - `switch_to_alert(self)`
  - `switch_to_error(self)`
  - `switch_to_home(self)`
  - `switch_to_warning(self)`
  - `update_bot_position(self, x: float, y: float, heading: float)`
  - `write_obstacle_direction(self, x, y, base_address)`

**mule_comms/hmi_bridge/hmi_models.py**

- `class BatteryBar`
- `class Const`
- `class ImageTypes`
- `class ReadAddresses`
- `class Recovery`
- `class RecoveryValues`
- `class RestartSherpa`
- `class RestartSherpaValues`
- `class SwitchMode`
- `class SwitchModeValues`
- `class WriteAddresses`

**mule_comms/hmi_bridge/hmi_tcp_utils.py**

- `class ModbusTcpClient`
  - `read_coil(self, address)`
  - `read_register(self, address)`
  - `read_string_from_registers(self, address, length)`
  - `write_coil(self, address, value)`
  - `write_register(self, address, value)`
  - `write_string_to_registers(self, address, string_value, length)`

**mule_comms/hmi_bridge/tests/test_hmi_bridge.py**

- `class FailingBridge(HMIBridgeTest)`
  - `main(self)`
- `class HMIBridgeTest`
  - `empty_queue(self, q)`
  - `get_app_ctx(self)`
  - `hmi_to_mule_comms(self, ctx)`
  - `main(self)`
  - `redis_channel_reader(self, ctx)`
  - `redis_channel_writer(self, ctx)`
  - `send_error_info(self, ctx)`
  - `send_network_stats(self, ctx)`
  - `send_sherpa_status(self, ctx, msg_reader)`
  - `send_updates(self, ctx, msg_reader)`
- `class MockAppContext`
  - `send_to_hmi_frontend(self, msg)`
- `class MockDebounceManager`
  - `should_send(self, message_type)`
- `class MockHMIMsgHandler`
  - `handle(self, msg)`
- `class MockZMQBusReader`
  - `is_alive(self)`
  - `start(self)`
- `class TestSuite`
  - `test_async_operations(self)`
  - `test_component_creation(self)`
  - `test_exception_handling(self)`
  - `test_main_bridge_function(self)`

**mule_comms/hmi_bridge/tests/test_hmi_bridge_utils.py**

- `class HMIBridgeUtilsTest`
  - `empty_queue(self, q)`
  - `get_app_ctx(self)`
  - `get_mule_orc_down_msg(self, ctx)`
  - `hmi_to_mule_comms(self, ctx)`
  - `redis_channel_reader(self, ctx)`
  - `redis_channel_writer(self, ctx)`
  - `send_error_info(self, ctx)`
  - `send_network_stats(self, ctx)`
  - `send_sherpa_status(self, ctx, msg_reader)`
  - `send_updates(self, ctx, msg_reader)`
- `class MockAppContext`
  - `send_to_hmi_frontend(self, msg)`
- `class MockDebounceManager`
  - `should_send(self, message_type: str) → bool`
- `class MockHMIMsgHandler`
  - `handle(self, msg)`
- `class MockZMQBusReader`
  - `is_alive(self)`
  - `start(self)`
- `class TestSuite`
  - `test_app_context_creation(self)`
  - `test_debounce_manager(self)`
  - `test_empty_queue(self)`
  - `test_get_mule_orc_down_msg(self)`
  - `test_hmi_to_mule_comms(self)`
  - `test_queue_operations(self)`
  - `test_redis_channel_reader(self)`
  - `test_redis_channel_writer(self)`
  - `test_send_error_info(self)`
  - `test_send_network_stats(self)`
  - `test_send_sherpa_status(self)`
  - `test_send_updates(self)`

**mule_comms/hmi_bridge/tests/test_hmi_handler.py**

- `class Const`
- `class HMIHandlerTest`
  - `find_closest_point(self, x, y)`
  - `handle(self, msg)`
  - `handle_action_terminate_trip(self, msg)`
  - `handle_set_alerts(self, msg)`
  - `handle_set_mule_error(self, msg)`
  - `handle_set_network_stats(self, msg)`
  - `handle_set_sherpa_status(self, msg)`
  - `handle_set_trip_description(self, msg)`
  - `handle_set_trip_status(self, msg)`
  - `switch_to_alert(self)`
  - `switch_to_error(self)`
  - `switch_to_home(self)`
  - `switch_to_warning(self)`
  - `write_obstacle_direction(self, x, y, base_address)`
- `class ImageTypes`
- `class MockHMIModels`
- `class MockHMIUtils`
  - `shrink_message_type(message_type)`
- `class MockModbusTcpClient`
  - `read_coil(self, address)`
  - `read_register(self, address)`
  - `read_string_from_registers(self, address, length)`
  - `write_coil(self, address, value)`
  - `write_register(self, address, value)`
  - `write_string_to_registers(self, address, string_value, length)`
- `class ReadAddresses`
- `class TestSuite`
  - `test_battery_warnings(self)`
  - `test_component_creation(self)`
  - `test_error_handling(self)`
  - `test_message_handling(self)`
  - `test_missing_methods(self)`
  - `test_mode_switching(self)`
  - `test_obstacle_direction_find_closest_point(self)`
  - `test_obstacle_direction_modbus_writes(self)`
  - `test_trip_status_with_local_obstacle(self)`
  - `test_utility_functions(self)`
- `class WriteAddresses`

**mule_comms/hmi_bridge/tests/test_hmi_modbus_client.py**

- `class Const`
- `class HMIModbusClientTest`
  - `get_read_addresses(self)`
  - `main(self)`
  - `modbus_reader(self, aredis_conn)`
  - `modbus_writer(self, aredis_conn)`
- `class ImageTypes`
- `class MockHMIModels`
- `class MockHMIUtils`
  - `shrink_message_type(message_type)`
- `class MockHandler`
  - `handle(self, msg)`
- `class MockModbusTcpClient`
  - `read_coil(self, address)`
  - `read_register(self, address)`
  - `read_string_from_registers(self, address, length)`
  - `write_coil(self, address, value)`
  - `write_register(self, address, value)`
  - `write_string_to_registers(self, address, string_value, length)`
- `class MockPubSub`
  - `add_message(self, message)`
  - `get_message(self, ignore_subscribe_messages, timeout)`
  - `subscribe(self, channel)`
- `class MockRedisConnection`
  - `publish(self, channel, message)`
  - `pubsub(self)`
- `class ReadAddresses`
  - `get_addresses(cls)`
- `class TestSuite`
  - `test_address_monitoring(self)`
  - `test_component_creation(self)`
  - `test_data_model_mapping(self)`
  - `test_main_function(self)`
  - `test_message_processing(self)`
  - `test_modbus_reader(self)`
  - `test_modbus_writer(self)`
  - `test_redis_operations(self)`
- `class WriteAddresses`

**mule_comms/hmi_bridge/tests/test_hmi_models.py**

- `class BatteryBar`
- `class Const`
- `class ImageTypes`
- `class ReadAddresses`
- `class RestartSherpa`
- `class RestartSherpaValues`
- `class SwitchMode`
- `class SwitchModeValues`
- `class TestSuite`
  - `test_address_consistency(self)`
  - `test_address_values(self)`
  - `test_battery_bar_values(self)`
  - `test_const_class(self)`
  - `test_data_model_mapping(self)`
  - `test_dataclass_creation(self)`
  - `test_dataclass_serialization(self)`
  - `test_hex_to_decimal_conversion(self)`
  - `test_image_types_values(self)`
  - `test_restart_sherpa_values(self)`
  - `test_switch_mode_values(self)`
  - `test_type_annotations(self)`
- `class WriteAddresses`

**mule_comms/hmi_bridge/tests/test_hmi_tcp_utils.py**

- `class Const`
- `class MockHMIModels`
- `class MockModbusClient`
  - `read_coils(self, address, count)`
  - `read_holding_registers(self, address, count)`
  - `write_multiple_registers(self, address, values)`
  - `write_single_coil(self, address, value)`
  - `write_single_register(self, address, value)`
- `class ModbusTcpClientTest`
  - `read_coil(self, address)`
  - `read_register(self, address)`
  - `read_string_from_registers(self, address, length)`
  - `write_coil(self, address, value)`
  - `write_register(self, address, value)`
  - `write_string_to_registers(self, address, string_value, length)`
- `class TestSuite`
  - `test_client_creation(self)`
  - `test_concurrent_operations(self)`
  - `test_data_persistence(self)`
  - `test_error_handling(self)`
  - `test_large_strings(self)`
  - `test_read_coil(self)`
  - `test_read_register(self)`
  - `test_read_string_from_registers(self)`
  - `test_unicode_strings(self)`
  - `test_write_coil(self)`
  - `test_write_register(self)`
  - `test_write_string_to_registers(self)`

**mule_comms/hmi_bridge/tests/test_hmi_utils.py**

- `class TestSuite`
  - `test_error_handling(self)`
  - `test_function_signature(self)`
  - `test_shrink_message_type_basic(self)`
  - `test_shrink_message_type_complex(self)`
  - `test_shrink_message_type_consistency(self)`
  - `test_shrink_message_type_edge_cases(self)`
  - `test_shrink_message_type_performance(self)`
  - `test_shrink_message_type_real_world_examples(self)`
  - `test_shrink_message_type_special_cases(self)`
  - `test_shrink_message_type_unicode(self)`
  - `test_shrink_message_type_whitespace_handling(self)`

**mule_comms/hmi_bridge/tests/test_hmi_ws_server.py**

- `class HMIWebSocketServerTest`
  - `get_config(self)`
  - `handler(self, websocket)`
  - `start_server(self, host, port)`
  - `ws_reader(self, websocket, aredis_conn)`
  - `ws_writer(self, websocket, aredis_conn)`
- `class MockPubSub`
  - `add_message(self, message)`
  - `get_message(self, ignore_subscribe_messages, timeout)`
  - `subscribe(self, channel)`
- `class MockRedisConnection`
  - `publish(self, channel, message)`
  - `pubsub(self)`
- `class MockWebSocket`
  - `add_message(self, message)`
  - `clear_sent_messages(self)`
  - `get_sent_messages(self)`
  - `recv(self)`
  - `send(self, message)`
- `class TestSuite`
  - `custom_ws_writer(websocket, aredis_conn)`
  - `test_ast_literal_eval(self)`
  - `test_config_loading(self)`
  - `test_error_handling(self)`
  - `test_handler(self)`
  - `test_json_parsing(self)`
  - `test_message_flow(self)`
  - `test_redis_connection_creation(self)`
  - `test_redis_pubsub_operations(self)`
  - `test_server_startup(self)`
  - `test_websocket_creation(self)`
  - `test_websocket_message_handling(self)`
  - `test_ws_reader(self)`
  - `test_ws_writer(self)`

**mule_comms/message_handlers.py**

- `class FMMsgHandler`
  - `check_valid_map_files(self, data_dir, data_req)`
  - `handle(self, msg)`
  - `handle_auto_recover(self, msg: dict)`
  - `handle_current_sound_status(self, req)`
  - `handle_diagnostics(self, req)`
  - `handle_fm_message(self, req)`
  - `handle_get_data_dir(self, req)`
  - `handle_init(self, req)`
  - `handle_lifter_actuator_manual(self, req)`
  - `handle_map_creation(self, body_json)`
  - `handle_move_to(self, msg: dict)`
  - `handle_pause_resume(self, msg: dict)`
  - `handle_peripherals(self, msg: dict)`
  - `handle_powercycle(self, req)`
  - `handle_quick_diagnostics(self, req)`
  - `handle_reset_pose(self, msg: dict)`
  - `handle_reset_visas_held(self, req)`
  - `handle_restart_mule_docker(self, req)`
  - `handle_retrieve_data(self, req)`
  - `handle_revoke_visa(self, msg: dict)`
  - `handle_sound(self, msg: dict)`
  - `handle_switch_mode(self, msg: dict)`
  - `handle_terminate_trip(self, msg: dict)`
  - `handle_update_sherpa_config(self, msg: dict)`
  - `raise_exp_if_mule_orc_is_down(self)`
- `class HMIMsgHandler(FMMsgHandler)`

**mule_comms/request_models.py**

- `class auto_recover_req`
- `class conveyor_req`
- `class current_sound_status_req`
- `class diagnostics_req`
- `class dispatch_button_req`
- `class fm_message_req`
- `class get_data_dir_req`
- `class hitch_req`
- `class indicator_req`
- `class init_req`
- `class lifter_actuator`
- `class move_to_req`
- `class pause_resume_req`
- `class reset_pose_req`
- `class reset_visas_held_req`
- `class restart_mule_docker_req`
- `class retrieve_data_req`
- `class revoke_visa_req`
- `class sound_req`
- `class speaker_req`
- `class switch_mode_req`
- `class terminate_trip_req`
- `class update_sherpa_config_req`

**mule_comms/send_event_updates_to_fm.py**

- `class HandleMuleEvent`
  - `check_if_msg_is_stale(self, msg)`
  - `handle_event_alerts(self, ctx, msg)`
  - `handle_event_peripherals(self, ctx, msg)`
  - `handle_event_reached(self, ctx, msg)`
  - `handle_event_resource(self, ctx, msg)`
  - `handle_event_slam_recover(self, ctx, msg)`
  - `handle_mule_event(self, ctx, msg)`

**mule_comms/utils/zmq_utils.py**

- `class ZMQBusReader(threading.Thread)`
  - `maybe_add_to_process_buffer(self, msg, msg_type)`
  - `process_alert_msg(self, raw_msg)`
  - `process_basic_description_in_peripheral_msg(self, raw_msg)`
  - `process_battery_msg(self, raw_msg)`
  - `process_follow_me_msg(self, raw_msg)`
  - `process_mule_command_msg(self, raw_msg)`
  - `process_mule_status_msg(self, raw_msg)`
  - `process_peripherals_msg(self, raw_msg)`
  - `process_slam_pose_msg(self, raw_msg)`
  - `run(self)`

**simulators/mule_simulator/control_messages.py**

- `class Mule`
  - `get_v_and_w(self, rear_omega, steering_angle)`
  - `handle_drive_message(self, v, w)`
  - `handle_message(self, v, w)`
  - `state(self) → MuleState`
  - `update(self, world_state)`
- `class MuleState`
- `class TrackerData`
  - `creating_np_array_for_tracker(self)`
- `class WorldState`
- `class drivable_region_thread(Thread)`
  - `drivable_region_update(self)`
  - `run(self)`
  - `stop(self)`
- `class mule_actuator_driver_thread(Thread)`
  - `run(self)`
  - `stop(self)`
- `class mule_sensor_status_thread(Thread)`
  - `run(self)`
  - `sensor_status_update(self)`
  - `stop(self)`
- `class stoppages_message_thread(Thread)`
  - `run(self)`
  - `stop(self)`
  - `stoppages_message_update(self)`
- `class yelli_thread(Thread)`
  - `run(self)`
  - `stop(self)`
  - `yelli_update(self)`

**simulators/mule_simulator/fm_control_sim.py**

- `class Mule`
  - `handle_drive_message(self, v, w)`
  - `handle_message(self, v, w)`
  - `state(self) → MuleState`
  - `update(self, world_state)`
- `class MuleState`
- `class StationsData`
- `class TrackerData`
  - `creating_np_array_for_tracker(self)`
- `class TripData`
- `class WorldState`
- `class drivable_region_thread(Thread)`
  - `drivable_region_update(self)`
  - `run(self)`
  - `stop(self)`
- `class mule_sensor_status_thread(Thread)`
  - `run(self)`
  - `sensor_status_update(self)`
  - `stop(self)`
- `class stoppages_message_thread(Thread)`
  - `run(self)`
  - `stop(self)`
  - `stoppages_message_update(self)`
- `class yelli_thread(Thread)`
  - `run(self)`
  - `stop(self)`
  - `yelli_update(self)`

**tools/python_receiver/CAN_Parsing.py**

- `class CAN_Node(ABC)`
  - `CAN_Rx_IDs(self)`
  - `parseMsg(self, msg: can.Message)`
- `class ParseRule`
  - `apply(self, msg: can.Message)`

**tools/python_receiver/drivers/AMT212.py**

- `class AMT212(CAN_Node)`
  - `CAN_Rx_IDs(self)`
  - `parseMsg(self, msg: can.Message)`

**tools/python_receiver/drivers/CElectric.py**

- `class CElectric(CAN_Node)`
  - `CAN_Rx_IDs(self)`
  - `parseErrorCode(self, errorCode)`
  - `parseMSG1(self, msg: can.Message)`
  - `parseMSG2(self, msg: can.Message)`
  - `parseMSG3(self, msg: can.Message)`
  - `parseMsg(self, msg: can.Message)`

**tools/python_receiver/drivers/EndStop.py**

- `class EndStop(CAN_Node)`
  - `CAN_Rx_IDs(self)`
  - `parseMsg(self, msg: can.Message)`

**tools/python_receiver/drivers/Ewellix.py**

- `class CAHB(CAN_Node)`
  - `CAN_Rx_IDs(self)`
  - `holdCurrentPosition(self)`
  - `parseMsg(self, msg: can.Message)`
  - `setPosition(self, position)`

**tools/python_receiver/drivers/LoadCell.py**

- `class LoadCell(CAN_Node)`
  - `CAN_Rx_IDs(self)`
  - `parseMsg(self, msg: can.Message)`
  - `tare(self)`

**tools/python_receiver/drivers/Roboteq.py**

- `class Roboteq(CAN_Node)`
  - `CAN_Rx_IDs(self)`
  - `getReady(self)`
  - `parseMsg(self, msg: can.Message)`
  - `parseStatus(self, msg: can.Message)`
  - `parseTPDO1(self, msg: can.Message)`
  - `parseTPDO2(self, msg: can.Message)`
  - `parseTPDO3(self, msg: can.Message)`
  - `parseTPDO4(self, msg: can.Message)`
  - `setRpms(self, rpmL, rpmR)`

**tools/python_receiver/drivers/SidekickInternal.py**

- `class Sidekick(CAN_Node)`
  - `CAN_Rx_IDs(self)`
  - `parseMsg(self, msg: can.Message)`
  - `parseVersionNumber(self, msg: can.Message)`
  - `requestVersionNumber(self)`

**utils/comms.py**

- `class Delfino(object)`
  - `read_message(self)`
  - `read_thread(self)`
  - `send(self, left, right, angle)`
  - `send_message(self, message_id, message)`
  - `slip_putc(self, ch)`

**utils/control_utils.py**

- `class ObstacleInfo(object)`
- `class Timer`
  - `get_current_timer_value(self)`
  - `reset(self)`
  - `start(self)`
  - `stop(self)`

**utils/geometry_utils.py**

- `class GridLine`
  - `add_internal_node(self, pt: np.ndarray) → Any`
  - `grid_intersection(self, seg: Line, tol: float) → Union[...]`
  - `is_intersecting_with_line_segment(self, seg: Line) → bool`
  - `is_intersecting_with_ray(self, ray: Line) → bool`
  - `point_distance(self, pt: np.ndarray) → float`
  - `point_projection(self, pt: np.ndarray) → np.ndarray`
- `class Line`
  - `angle(self)`
  - `angle_between_lines(self, line)`
  - `get_point_at_length(self, d)`
  - `orthogonal_direction(self)`
  - `reduce_length_by(self, z, distance_to_reduce)`
- `class Point`
  - `array(self)`
  - `to_list(self)`
- `class Polygon`
  - `check_if_edges_ordered(self)`
  - `get_polygon_vertices_from_edges(self, edges)`
  - `is_inside_polygon(self, pose)`
  - `is_intersecting_with_line_seg(self, line_seg: GridLine) → bool`
  - `polygon_edges_from_vertices(self, vertices)`
- `class Pose`
  - `array(self)`
  - `to_list(self)`
- `class Rectangle(Polygon)`
  - `are_edges_perpendicular(self, edge1, edge2) → bool`
  - `calculate_diagonal(self)`
  - `check_if_rectangle(self)`
  - `inflate_rectangle(self, offset)`
  - `is_inside_rectangle(self, point)`

**utils/grid_mappingv1.py**

- `class Grid2D`
  - `apply_median_filter(self, kernel_size)`
  - `insert_points(self, pose, frame)`
  - `search(self, frame, search_space)`
  - `set_grid(self, grid, z_grid)`
  - `transform_local_to_grid(self, frame, pose)`
  - `transform_world_to_grid(self, frame)`
- `class Grid2DCuda(Grid2D)`
  - `search(self, frame, search_space)`
  - `set_grid(self, grid, z_grid)`
- `class MultiGrid`
  - `apply_median_filter(self, kernel_size)`
  - `insert_points(self, beams, pose)`
  - `load_map(folder, dtype, level, zslice, cuda)`
  - `save_map(self, folder)`
  - `search(self, beams, search_space)`
  - `set_maps(self)`
  - `split_frame(self, frame)`
- `class MultiGridCuda(MultiGrid)`
  - `set_maps(self)`

**utils/imu_tracker.py**

- `class ImuTracker`
  - `add_imu_data(self, imu_data)`
  - `get_cumulative_quaternion(self, quaternion_buffer)`
  - `get_gyro_quaternion(self, upto_time)`
  - `get_initial_gyro_bias(self, imu_data)`
  - `get_rolling_gyro_bias(self, imu_data)`
  - `get_z(self, debug)`
  - `start_tracking_z(self)`
  - `stop_tracking_z(self)`

**utils/map_creation_tools/merge_maps.py**

- `class dataManager`
  - `generate_map_files(self, map_dir, opt_poses, constraints, scores, z_slices, map_grid_res, max_dist, level_lookup_type, pruned, debug, plot)`
  - `get_data(self)`
  - `return_transformed(self, transforms)`
  - `transform(self, transforms)`

**utils/mule_utils.py**

- `class DataGather(Thread)`
  - `get_data(self)`
  - `is_msg_new(self)`
  - `run(self)`
  - `stop(self)`

**utils/posegraph_map/grid.py**

- `class Grid2D`
  - `apply_median_filter(self, kernel_size)`
  - `compute_level_mapping(self, max_levels)`
  - `insert_points(self, pose, frame)`
  - `linear_transform(self, t1)`
  - `search(self, frame, search_space, count_once)`
  - `set_grid(self, grid)`
  - `set_level_search_type(self, search_type)`
  - `transform_local_to_grid(self, frame, pose)`
  - `transform_world_to_grid(self, frame)`

**utils/posegraph_map/posegraph.py**

- `class Constraint`
- `class PoseGraphOptimization(g2o.SparseOptimizer)`
  - `add_edge(self, vertices, measurement, information, robust_kernel)`
  - `add_edge_from_state(self, vertices, information, robust_kernel)`
  - `add_vertex(self, id, pose, fixed)`
  - `get_pose(self, id)`
  - `optimize(self, max_iterations)`

**utils/posegraph_map/submap.py**

- `class Submap`
  - `compress_data(self)`
  - `decompress_data(self)`
  - `finish(self)`
  - `insert_points(self, frame, pose, frame_id, node_id)`
  - `search(self, frame, search_space, count_once)`
  - `set_level_search_type(self, search_type)`

**utils/ps4_utils.py**

- `class DbusBluzScanner(Thread)`
  - `check_old_interfaces(self)`
  - `get_devices(self)`
  - `interfaces_added(self, path, interfaces)`
  - `new_report(self, path, data)`
  - `properties_changed(self, interface, changed, invalidated, path)`
  - `run(self)`
- `class PS4(object)`
  - `run(self, topic, update)`
- `class PS4Control`
- `class SafetyPolicy`
  - `check_drive_policy(self, current_pose, velocity, omega)`

**utils/ps5_utils.py**

- `class PS4(object)`
  - `run(self, topic, update)`

**utils/undistort_images.py**

- `class CSVWriter`
  - `close(self)`
  - `write_header(self)`
  - `write_row(self, row)`

## Fleet Manager Usage of Mule APIs

### Files Importing Mule (3)

**fm_init.py**
- Imports: load_mule_config

**utils/fleet_utils.py**
- Imports: gbu, load_mule_config, mu, rpi

**utils/router_utils.py**
- Imports: RoutePlannerInterface, grl

### Function Call Chains

- fm_init.py:regenerate_mule_config() → load_mule_config(os.getenv(...))
- utils/fleet_utils.py:FleetUtils.delete_fleet() → delete_station(dbsession, station.name)
- utils/fleet_utils.py:FleetUtils.delete_invalid_stations() → delete_station(dbsession, st.name)
- utils/fleet_utils.py:FleetUtils.delete_station() → get_station(station_name)
- utils/fleet_utils.py:maybe_create_gmaj_file() → maybe_update_gmaj(gmaj_path, wpsj_path, True)
- utils/fleet_utils.py:maybe_create_graph_object() → get_checksum(gmaj_path)
- utils/fleet_utils.py:maybe_create_graph_object() → load_mule_config()
- utils/fleet_utils.py:maybe_create_graph_object() → process_dict(terminal_lines)
- utils/fleet_utils.py:maybe_create_graph_object() → process_stations_info(stations)
- utils/router_utils.py:get_dense_path() → get_dense_path(final_route)

## Detailed Interface Changes & Dependencies

### `delete_station`

**Mule Definition:**
```python
def delete_station(name, stations)
```

**Used in 2 place(s):**

- **utils/fleet_utils.py** line 411
  - Called in: `FleetUtils.delete_invalid_stations`
  - With args: `dbsession, st.name`
  - Return value used: yes

- **utils/fleet_utils.py** line 437
  - Called in: `FleetUtils.delete_fleet`
  - With args: `dbsession, station.name`
  - Return value used: yes

### `get_checksum`

**Mule Definition:**
```python
def get_checksum(fname, fn)
```

**Used in 1 place(s):**

- **utils/fleet_utils.py** line 177
  - Called in: `maybe_create_graph_object`
  - With args: `gmaj_path`
  - Return value used: yes

### `get_dense_path`

**Mule Definition:**
```python
def get_dense_path(final_route)
```

**Used in 1 place(s):**

- **utils/router_utils.py** line 14
  - Called in: `get_dense_path`
  - With args: `final_route`
  - Return value used: yes

### `get_station`

**Mule Definition:**
```python
def get_station(pose)
```

**Used in 1 place(s):**

- **utils/fleet_utils.py** line 395
  - Called in: `FleetUtils.delete_station`
  - With args: `station_name`
  - Return value used: yes

### `load_mule_config`

**Mule Definition:**
```python
def load_mule_config(config_file)
```

**Used in 2 place(s):**

- **fm_init.py** line 37
  - Called in: `regenerate_mule_config`
  - With args: `os.getenv(...)`
  - Return value used: yes

- **utils/fleet_utils.py** line 163
  - Called in: `maybe_create_graph_object`
  - With args: ``
  - Return value used: yes

### `maybe_update_gmaj`

**Mule Definition:**
```python
def maybe_update_gmaj(gmaj_path, wpsj_path, VERIFY_WPSJ_CHECKSUM)
```

**Used in 1 place(s):**

- **utils/fleet_utils.py** line 146
  - Called in: `maybe_create_gmaj_file`
  - With args: `gmaj_path, wpsj_path, True`
  - Return value used: yes

### `process_dict`

**Mule Definition:**
```python
def process_dict(terminal_lines)
```

**Used in 1 place(s):**

- **utils/fleet_utils.py** line 175
  - Called in: `maybe_create_graph_object`
  - With args: `terminal_lines`
  - Return value used: yes

### `process_stations_info`

**Mule Definition:**
```python
def process_stations_info(stations)
```

**Used in 1 place(s):**

- **utils/fleet_utils.py** line 176
  - Called in: `maybe_create_graph_object`
  - With args: `stations`
  - Return value used: yes

