import type { AccidentFacts } from "../api/client";

export function getGuidedQuestionId(question: any): string {
    return question.question_id || question.field || question.fact_key || "unknown_question";
}

export function applyGuidedQuestionAnswer(currentFacts: AccidentFacts, question: any, value: string): AccidentFacts {
        const factKey = question.fact_key || question.knia_factor_key || String(question.question_id || "").split(".").pop();
        const nextFacts: AccidentFacts = { ...currentFacts };

        function markStealthParkedVehicleCollision() {
            nextFacts.accident_party_type = "car_vs_car";
            nextFacts.accident_type = "stealth_illegal_parked_vehicle_collision";

            (nextFacts as any).knia_major_party_type = "car_vs_car";
            (nextFacts as any).collision_partner_type = "vehicle";
            (nextFacts as any).direct_collision_partner_type = "vehicle";
            (nextFacts as any).accident_subtype = "night_unlit_illegal_parked_vehicle_collision";
            (nextFacts as any).target_vehicle_status = "abnormal_parked";
            (nextFacts as any).is_parked_vehicle_collision = true;
            (nextFacts as any).is_stealth_parked_vehicle_collision = true;
            (nextFacts as any).requires_high_opponent_fault_review = true;
            (nextFacts as any).excluded_knia_party_types = ["car_vs_bicycle", "car_vs_person"];

            delete (nextFacts as any).bicycle_involved;
            delete (nextFacts as any).possible_trigger_vehicle;
            delete (nextFacts as any).trigger_actor_type;
            delete (nextFacts as any).bicycle_location;
            delete (nextFacts as any).bicycle_movement;

            const lighting = String((nextFacts as any).parked_vehicle_lighting || "");
            const visibility = String((nextFacts as any).visibility_condition || "");
            const position = String((nextFacts as any).parked_vehicle_position || "");
            const impairment = String((nextFacts as any).opponent_impairment || "");
            const avoidability = String((nextFacts as any).avoidability || "");

            const isUnlit = lighting === "unlit_stealth" || lighting === "no_lights" || lighting === "unknown_but_dark";
            const isDark = visibility === "night_dark" || visibility === "under_bridge_dark" || visibility === "low_visibility";
            const isAbnormalPosition =
                position === "traffic_space" ||
                position === "flowerbed_or_median" ||
                position === "under_bridge" ||
                position === "roadside" ||
                position === "under_bridge_flowerbed";
            const isDrunk = impairment === "drunk_driving_confirmed" || impairment === "suspected_drunk";
            const isHardToAvoid = avoidability === "nearly_impossible" || avoidability === "limited";

            (nextFacts as any).night_no_lights_or_low_visibility = isUnlit || isDark;
            (nextFacts as any).abnormal_parking = isAbnormalPosition;
            (nextFacts as any).opponent_drunk_or_abnormal_operation = isDrunk;
            (nextFacts as any).low_avoidability = isHardToAvoid;

            if (isUnlit && isDark && isAbnormalPosition && isDrunk && isHardToAvoid) {
                (nextFacts as any).fault_ratio_claim_target = "opponent_100_ego_0_possible";
                (nextFacts as any).fault_ratio_realistic_target = "opponent_90_ego_10";
                (nextFacts as any).fault_ratio_minimum_target = "opponent_80_ego_20";
            } else if ((isUnlit && isDark && isAbnormalPosition) || (isDrunk && isAbnormalPosition)) {
                (nextFacts as any).fault_ratio_claim_target = "opponent_90_ego_10";
                (nextFacts as any).fault_ratio_realistic_target = "opponent_80_ego_20";
                (nextFacts as any).fault_ratio_minimum_target = "opponent_70_ego_30";
            }
        }

        if (factKey === "stopped") {
            nextFacts.stopped = value === "yes" ? true : value === "no" ? false : undefined;
        } else if (factKey === "sudden_brake_without_reason" || factKey === "sudden_brake") {
            nextFacts.sudden_brake = value === "yes";
        } else if (factKey === "lawful_stop_reason" || factKey === "stop_reason") {
            nextFacts.stop_reason = value;
        } else if (factKey === "brake_light_failure" || factKey === "brake_light") {
            nextFacts.brake_light = value;
        } else if (factKey === "abnormal_stop_position") {
            nextFacts.abnormal_stop = value === "abnormal_stop";
        } else if (factKey === "collision_object_type") {
            (nextFacts as any).collision_object_type = value;

            if (value === "parked_vehicle") {
                markStealthParkedVehicleCollision();
            } else if (value === "fixed_object" || value === "fallen_or_movable_object") {
                nextFacts.accident_party_type = "car_vs_object";
                nextFacts.accident_type = "object_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            }
        } else if (factKey === "stealth_collision_target") {
            (nextFacts as any).stealth_collision_target = value;
            (nextFacts as any).collision_target = value === "parked_truck" ? "truck" : value === "parked_vehicle" ? "parked_vehicle" : value;
            if (value === "parked_truck" || value === "parked_vehicle") {
                markStealthParkedVehicleCollision();
            } else if (value === "fixed_object") {
                nextFacts.accident_party_type = "car_vs_object";
                nextFacts.accident_type = "object_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            }
        } else if (factKey === "stealth_parked_position") {
            (nextFacts as any).stealth_parked_position = value;
            (nextFacts as any).parked_vehicle_position = value === "under_bridge_flowerbed" ? "flowerbed_or_median" : value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "stealth_lighting") {
            (nextFacts as any).stealth_lighting = value;
            (nextFacts as any).parked_vehicle_lighting =
                value === "unlit_stealth" ? "unlit_stealth" : value === "lights_on" ? "all_lights_on" : value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "stealth_visibility") {
            (nextFacts as any).stealth_visibility = value;
            (nextFacts as any).visibility_condition = value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "opponent_drunk_driving") {
            (nextFacts as any).opponent_drunk_driving = value;
            (nextFacts as any).opponent_impairment =
                value === "drunk_confirmed" ? "drunk_driving_confirmed" : value === "drunk_suspected" ? "suspected_drunk" : value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "stealth_avoidability") {
            (nextFacts as any).stealth_avoidability = value;
            (nextFacts as any).avoidability = value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "collision_target") {
            (nextFacts as any).collision_target = value;

            if (value === "parked_vehicle" || value === "truck") {
                markStealthParkedVehicleCollision();
            } else if (value === "facility" || value === "fixed_object") {
                nextFacts.accident_party_type = "car_vs_object";
                nextFacts.accident_type = "object_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            }
        } else if (factKey === "parked_vehicle_position") {
            (nextFacts as any).parked_vehicle_position = value;

            if (value === "traffic_space" || value === "flowerbed_or_median" || value === "under_bridge" || value === "roadside") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "parked_vehicle_lighting") {
            (nextFacts as any).parked_vehicle_lighting = value;

            if (value === "unlit_stealth" || value === "no_lights" || value === "unknown_but_dark") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "visibility_condition") {
            (nextFacts as any).visibility_condition = value;

            if (value === "night_dark" || value === "under_bridge_dark" || value === "low_visibility") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "opponent_impairment") {
            (nextFacts as any).opponent_impairment = value;

            if (value === "drunk_driving_confirmed" || value === "suspected_drunk") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "avoidability") {
            (nextFacts as any).avoidability = value;

            if (value === "limited" || value === "nearly_impossible") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "abnormal_parking") {
            (nextFacts as any).abnormal_parking = value === "yes" ? true : value === "no" ? false : undefined;

            if (value === "yes") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "visibility_issue") {
            (nextFacts as any).visibility_issue = value;
            (nextFacts as any).night_no_lights_or_low_visibility = value === "stealth_no_lights" || value === "hard_to_see";

            if (value === "stealth_no_lights" || value === "hard_to_see") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "road_environment") {
            (nextFacts as any).road_environment = value;

            if (value === "under_bridge" || value === "flowerbed_or_median" || value === "dark_road") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "avoidance_time") {
            (nextFacts as any).avoidance_time = value;

            if (value === "limited" || value === "nearly_impossible") {
                (nextFacts as any).avoidability = value;
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "crosswalk_context") {
            (nextFacts as any).crosswalk_context = value;
            if (value === "crosswalk" || value === "near_crosswalk") {
                (nextFacts as any).crosswalk_nearby = true;
            } else if (value === "not_crosswalk") {
                (nextFacts as any).crosswalk_nearby = false;
            }
        } else if (factKey === "pedestrian_signal") {
            (nextFacts as any).pedestrian_signal = value;
        } else if (factKey === "pedestrian_visibility") {
            (nextFacts as any).pedestrian_visibility = value;
        } else if (factKey === "turn_signal") {
            (nextFacts as any).turn_signal = value;
        } else if (factKey === "impact_position") {
            (nextFacts as any).impact_position = value;
        } else if (factKey === "lane_change_manner") {
            (nextFacts as any).lane_change_manner = value;
            nextFacts.accident_type = "lane_change_collision";
            nextFacts.accident_party_type = "car_vs_car";
            (nextFacts as any).knia_major_party_type = "car_vs_car";
        } else if (factKey === "signal_context") {
            (nextFacts as any).signal_context = value;
        } else if (factKey === "intersection_movement") {
            (nextFacts as any).intersection_movement = value;
            nextFacts.accident_type = "intersection_collision";
            nextFacts.accident_party_type = "car_vs_car";
            (nextFacts as any).knia_major_party_type = "car_vs_car";
        } else if (factKey === "intersection_entry_order") {
            (nextFacts as any).intersection_entry_order = value;
        } else if (factKey === "bicycle_location") {
            (nextFacts as any).bicycle_location = value;
            nextFacts.accident_party_type = "car_vs_bicycle";
            nextFacts.accident_type = "bicycle_collision";
            (nextFacts as any).knia_major_party_type = "car_vs_bicycle";
        } else if (factKey === "bicycle_movement") {
            (nextFacts as any).bicycle_movement = value;
        } else if (factKey === "single_vehicle_cause") {
            (nextFacts as any).single_vehicle_cause = value;
            nextFacts.accident_party_type = "single_vehicle";
            nextFacts.accident_type = "single_vehicle_accident";
            (nextFacts as any).knia_major_party_type = "single_vehicle";
        } else if (factKey === "external_cause_evidence") {
            (nextFacts as any).external_cause_evidence = value;
        } else if (factKey === "accident_counterpart") {
            (nextFacts as any).accident_counterpart = value;

            if (value === "person") {
                nextFacts.accident_party_type = "car_vs_person";
                nextFacts.accident_type = "pedestrian_crosswalk_accident";
                (nextFacts as any).knia_major_party_type = "car_vs_person";
            } else if (value === "bicycle") {
                nextFacts.accident_party_type = "car_vs_bicycle";
                nextFacts.accident_type = "bicycle_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_bicycle";
            } else if (value === "parked_vehicle") {
                markStealthParkedVehicleCollision();
            } else if (value === "object") {
                nextFacts.accident_party_type = "car_vs_object";
                nextFacts.accident_type = "object_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            } else if (value === "car") {
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            }
        } else if (factKey === "car_vs_car_scenario_type") {
            nextFacts.accident_party_type = "car_vs_car";
            (nextFacts as any).knia_major_party_type = "car_vs_car";
            (nextFacts as any).collision_partner_type = "vehicle";
            (nextFacts as any).direct_collision_partner_type = "vehicle";
            if (value === "ego_hit_front") {
                nextFacts.accident_type = "rear_end_collision";
                (nextFacts as any).rear_end_role = "ego_hit_front";
                (nextFacts as any).collision_role = "ego_hit_front";
            } else if (value !== "unknown") {
                nextFacts.accident_type = value;
            }
        } else if (factKey === "accident_location_context") {
            (nextFacts as any).accident_location_context = value;

            if (value === "intersection") {
                nextFacts.accident_type = "intersection_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            } else if (value === "lane") {
                nextFacts.accident_type = "lane_change_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            } else if (value === "crosswalk") {
                (nextFacts as any).crosswalk_nearby = true;
                (nextFacts as any).road_context = "crosswalk_nearby";
            } else if (value === "parking_or_roadside") {
                nextFacts.accident_type = "object_collision";
            } else if (value === "under_bridge" || value === "flowerbed_or_median") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "visibility_or_weather") {
            (nextFacts as any).visibility_or_weather = value;
            (nextFacts as any).night_no_lights_or_low_visibility = value === "night_or_dark";

            if (value === "night_or_dark") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "rear_end_role") {
            (nextFacts as any).rear_end_role = value;

            if (value === "ego_hit_front") {
                nextFacts.accident_type = "rear_end_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
                (nextFacts as any).collision_role = "ego_hit_front";
            } else if (value === "hit_by_rear") {
                nextFacts.accident_type = "rear_end_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
                (nextFacts as any).collision_role = "hit_by_rear";
            }
        } else if (factKey === "accident_direction") {
            (nextFacts as any).accident_direction = value;

            if (value === "ego_hit_front") {
                nextFacts.accident_type = "rear_end_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
                (nextFacts as any).rear_end_role = "ego_hit_front";
                (nextFacts as any).collision_role = "ego_hit_front";
            } else if (value === "hit_by_rear") {
                nextFacts.accident_type = "rear_end_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
                (nextFacts as any).rear_end_role = "hit_by_rear";
                (nextFacts as any).collision_role = "hit_by_rear";
            } else if (value === "object_collision") {
                nextFacts.accident_type = "object_collision";
                nextFacts.accident_party_type = "car_vs_object";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            } else if (value === "intersection") {
                nextFacts.accident_type = "intersection_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            } else if (value === "lane_change") {
                nextFacts.accident_type = "lane_change_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            } else if (value === "pedestrian") {
                nextFacts.accident_type = "pedestrian_crosswalk_accident";
                nextFacts.accident_party_type = "car_vs_person";
                (nextFacts as any).knia_major_party_type = "car_vs_person";
            } else if (value === "parked_vehicle" || value === "stealth_parked_vehicle") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "front_vehicle_status") {
            (nextFacts as any).front_vehicle_status = value;
            (nextFacts as any).rear_end_role = "ego_hit_front";
            (nextFacts as any).collision_role = "ego_hit_front";

            if (value === "sudden_stop") {
                nextFacts.sudden_brake = true;
            }
        } else if (factKey === "front_stop_reason") {
            (nextFacts as any).front_stop_reason = value;
            nextFacts.stop_reason = value;
        } else if (factKey === "front_brake_light") {
            (nextFacts as any).front_brake_light = value;
            nextFacts.brake_light = value;
        } else if (factKey === "following_distance") {
            (nextFacts as any).following_distance = value;
        } else if (factKey === "rear_end_avoidance_time") {
            (nextFacts as any).rear_end_avoidance_time = value;
        } else {
            (nextFacts as any)[factKey] = value;
        }

        return nextFacts;
}
