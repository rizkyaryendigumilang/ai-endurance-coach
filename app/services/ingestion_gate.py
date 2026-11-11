"""
Goalie V2 - Lapisan 1: Ingestion & Pre-Processing Gate
Cleans raw telemetry sensors, filters cardiac lag, removes stopped points,
simplifies GPX courses with RDP, and validates high-speed video fps.
"""

import math
from typing import List, Dict, Any, Optional


class IngestionGate:
    """
    Ingestion & Pre-Processing Gate for raw athlete telemetry and GPX files.
    Ensures that only clean, steady-state, noise-filtered data enters SportsEngine.
    """

    @staticmethod
    def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates great-circle distance between two GPS points in meters."""
        R = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2.0) ** 2 +
             math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

    def slice_steady_state(
        self,
        stream_points: List[Dict[str, Any]],
        cardiac_lag_seconds: int = 600,
        min_running_speed_mps: float = 0.8
    ) -> Dict[str, Any]:
        """
        Extracts steady-state running segments:
        1. Drops initial cardiac lag window (default 10 mins / 600s).
        2. Drops stopped / traffic light points (speed < 0.8 m/s or HR <= 0).
        3. Computes average steady speed, pace, and heart rate.
        """
        if not stream_points:
            return {
                "status": "insufficient_data",
                "steady_points": [],
                "cardiac_lag_points_dropped": 0,
                "pause_points_dropped": 0,
                "avg_speed_mps": 0.0,
                "avg_heart_rate": 0.0,
                "avg_pace_formatted": "--:-- /km",
                "steady_duration_seconds": 0
            }

        max_elapsed = max(p.get("elapsed_seconds", 0) for p in stream_points)
        if max_elapsed < cardiac_lag_seconds:
            return {
                "status": "too_short_for_steady_state",
                "steady_points": [],
                "cardiac_lag_points_dropped": len(stream_points),
                "pause_points_dropped": 0,
                "avg_speed_mps": 0.0,
                "avg_heart_rate": 0.0,
                "avg_pace_formatted": "--:-- /km",
                "steady_duration_seconds": 0
            }

        lag_dropped = 0
        pause_dropped = 0
        steady_points = []

        for p in stream_points:
            t = p.get("elapsed_seconds", 0)
            if t < cardiac_lag_seconds:
                lag_dropped += 1
                continue

            spd = float(p.get("speed_mps", 0.0))
            hr = float(p.get("heart_rate", 0.0))

            if spd < min_running_speed_mps or hr <= 0.0:
                pause_dropped += 1
                continue

            steady_points.append(p)

        if not steady_points:
            return {
                "status": "insufficient_data",
                "steady_points": [],
                "cardiac_lag_points_dropped": lag_dropped,
                "pause_points_dropped": pause_dropped,
                "avg_speed_mps": 0.0,
                "avg_heart_rate": 0.0,
                "avg_pace_formatted": "--:-- /km",
                "steady_duration_seconds": 0
            }

        speeds = [float(p.get("speed_mps", 0.0)) for p in steady_points]
        hrs = [float(p.get("heart_rate", 0.0)) for p in steady_points]

        avg_spd = sum(speeds) / len(speeds)
        avg_hr = sum(hrs) / len(hrs)

        # Calculate formatted pace in MM:SS /km
        if avg_spd > 0.1:
            pace_sec_km = 1000.0 / avg_spd
            mins = int(pace_sec_km // 60)
            secs = int(round(pace_sec_km % 60))
            if secs >= 60:
                mins += 1
                secs = 0
            pace_formatted = f"{mins:02d}:{secs:02d} /km"
        else:
            pace_sec_km = 0
            pace_formatted = "--:-- /km"

        first_t = steady_points[0].get("elapsed_seconds", 0)
        last_t = steady_points[-1].get("elapsed_seconds", 0)
        duration_s = max(0, last_t - first_t)

        return {
            "status": "success",
            "steady_points": steady_points,
            "cardiac_lag_points_dropped": lag_dropped,
            "pause_points_dropped": pause_dropped,
            "avg_speed_mps": round(avg_spd, 3),
            "avg_heart_rate": round(avg_hr, 1),
            "avg_pace_sec_km": round(pace_sec_km, 1),
            "avg_pace_formatted": pace_formatted,
            "steady_duration_seconds": duration_s
        }

    def simplify_gpx_route(
        self,
        raw_coords: List[List[float]],
        epsilon: float = 0.0001
    ) -> Dict[str, Any]:
        """
        Applies Ramer-Douglas-Peucker (RDP) algorithm to simplify 2D/3D GPS tracks.
        Coordinates are formatted as [lat, lon, ele] or [lat, lon].
        """
        if not raw_coords or len(raw_coords) <= 2:
            return {
                "simplified_coords": raw_coords or [],
                "original_count": len(raw_coords or []),
                "simplified_count": len(raw_coords or []),
                "reduction_ratio": 0.0
            }

        def perpendicular_distance(point, start, end):
            if start[0] == end[0] and start[1] == end[1]:
                return math.sqrt((point[0] - start[0]) ** 2 + (point[1] - start[1]) ** 2)

            num = abs(
                (end[1] - start[1]) * point[0] -
                (end[0] - start[0]) * point[1] +
                end[0] * start[1] - end[1] * start[0]
            )
            den = math.sqrt((end[1] - start[1]) ** 2 + (end[0] - start[0]) ** 2)
            return num / den if den > 0 else 0.0

        def rdp(pts, eps):
            if len(pts) < 3:
                return pts

            dmax = 0.0
            index = 0
            end = len(pts) - 1

            for i in range(1, end):
                d = perpendicular_distance(pts[i], pts[0], pts[end])
                if d > dmax:
                    index = i
                    dmax = d

            if dmax > eps:
                rec_results1 = rdp(pts[:index + 1], eps)
                rec_results2 = rdp(pts[index:], eps)
                return rec_results1[:-1] + rec_results2
            else:
                return [pts[0], pts[end]]

        simplified = rdp(raw_coords, epsilon)
        orig_count = len(raw_coords)
        simp_count = len(simplified)
        ratio = round((orig_count - simp_count) / orig_count, 4) if orig_count > 0 else 0.0

        return {
            "simplified_coords": simplified,
            "original_count": orig_count,
            "simplified_count": simp_count,
            "reduction_ratio": ratio
        }

    def segment_gpx_elevation_profile(
        self,
        coords: List[List[float]],
        segment_length_m: float = 1000.0
    ) -> Dict[str, Any]:
        """
        Segments a GPX route into 1 km distance slices, calculating elevation gain/loss
        and slope gradient percentage for Minetti GAP evaluation.
        """
        if not coords or len(coords) < 2:
            return {"segments": [], "total_distance_m": 0.0, "total_elev_gain_m": 0.0}

        segments = []
        seg_idx = 1
        current_seg_dist = 0.0
        seg_elev_gain = 0.0
        seg_elev_loss = 0.0
        seg_start_elev = coords[0][2] if len(coords[0]) > 2 else 0.0
        total_dist = 0.0
        total_gain = 0.0

        prev_pt = coords[0]

        for i in range(1, len(coords)):
            curr_pt = coords[i]
            d = self.haversine_distance_m(prev_pt[0], prev_pt[1], curr_pt[0], curr_pt[1])
            if d <= 0:
                continue

            current_seg_dist += d
            total_dist += d

            ele_prev = prev_pt[2] if len(prev_pt) > 2 else 0.0
            ele_curr = curr_pt[2] if len(curr_pt) > 2 else 0.0
            dele = ele_curr - ele_prev

            if dele > 0:
                seg_elev_gain += dele
                total_gain += dele
            else:
                seg_elev_loss += abs(dele)

            # Reached segment boundary
            if current_seg_dist >= segment_length_m or i == len(coords) - 1:
                gradient = ((ele_curr - seg_start_elev) / current_seg_dist) * 100.0 if current_seg_dist > 0 else 0.0
                segments.append({
                    "km_index": seg_idx,
                    "distance_m": round(current_seg_dist, 1),
                    "start_elev": round(seg_start_elev, 1),
                    "end_elev": round(ele_curr, 1),
                    "elev_gain_m": round(seg_elev_gain, 1),
                    "elev_loss_m": round(seg_elev_loss, 1),
                    "gradient_pct": round(gradient, 2)
                })
                seg_idx += 1
                current_seg_dist = 0.0
                seg_elev_gain = 0.0
                seg_elev_loss = 0.0
                seg_start_elev = ele_curr

            prev_pt = curr_pt

        return {
            "segments": segments,
            "total_distance_m": round(total_dist, 1),
            "total_elev_gain_m": round(total_gain, 1)
        }

    def validate_video_metadata(
        self,
        fps: float,
        width: Optional[int] = None,
        height: Optional[int] = None,
        duration_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Validates runner video capture for Computer Vision Ground Contact Time (GCT).
        Ground contact time in distance running is typically 180 to 260 milliseconds.
        A 30 fps recording captures only ~6 frames per ground strike, resulting in excessive
        temporal quantization noise. Minimum 60 fps (or 120 fps) is required.
        """
        fps_val = float(fps or 0.0)

        if fps_val < 58.0:
            return {
                "is_valid_for_gct": False,
                "fps": fps_val,
                "recommended_fps": 60,
                "reason": (
                    f"Frame rate {fps_val:.1f} fps lacks temporal resolution for Ground Contact Time "
                    f"(GCT < 250ms). Minimum 60 fps required."
                ),
                "vertical_oscillation_ready": False
            }

        res_str = f"{width}x{height}" if width and height else "unknown"
        vert_ready = bool(height and height >= 720)

        return {
            "is_valid_for_gct": True,
            "fps": fps_val,
            "resolution": res_str,
            "vertical_oscillation_ready": vert_ready,
            "message": "High-speed video validated for Ground Contact Time and Vertical Oscillation."
        }
