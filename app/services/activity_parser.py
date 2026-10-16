"""
Parser deterministik untuk file aktivitas mentah olahraga endurance:
Mendukung format .GPX, .TCX, dan .FIT (Garmin, Coros, Wahoo, Polar, Suunto).
Mengekstraksi deret waktu jarak, durasi, HR, elevasi, dan koordinat.
"""
import io
import math
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Menghitung jarak geosains (km) antara 2 koordinat bumi."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def parse_gpx(file_bytes: bytes) -> Dict[str, Any]:
    """Parse file .GPX (GPS Exchange Format)."""
    root = ET.fromstring(file_bytes)
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    
    # Try with and without namespace
    trkpts = root.findall('.//gpx:trkpt', ns)
    if not trkpts:
        trkpts = root.findall('.//trkpt')
    
    if not trkpts:
        raise ValueError("Tidak ada trackpoints yang valid dalam file GPX.")

    points = []
    total_dist = 0.0
    elevations = []
    hr_list = []
    prev_coord = None
    first_time = None
    last_time = None

    for pt in trkpts:
        lat = float(pt.attrib.get('lat', 0.0))
        lon = float(pt.attrib.get('lon', 0.0))
        
        ele_el = pt.find('gpx:ele', ns) if 'gpx' in ns else None
        if ele_el is None: ele_el = pt.find('ele')
        ele = float(ele_el.text) if (ele_el is not None and ele_el.text) else 0.0
        elevations.append(ele)

        time_el = pt.find('gpx:time', ns) if 'gpx' in ns else None
        if time_el is None: time_el = pt.find('time')
        if time_el is not None and time_el.text:
            try:
                # ISO parsing
                t_str = time_el.text.replace('Z', '+00:00')
                t_val = datetime.fromisoformat(t_str)
                if first_time is None: first_time = t_val
                last_time = t_val
            except Exception:
                pass

        # Parse Heart Rate extension if present
        hr = None
        for hr_tag in ['.//{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}hr', './/hr']:
            h_el = pt.find(hr_tag)
            if h_el is not None and h_el.text:
                try:
                    hr = int(h_el.text)
                    hr_list.append(hr)
                    break
                except Exception:
                    pass

        if prev_coord is not None:
            total_dist += haversine_km(prev_coord[0], prev_coord[1], lat, lon)
        prev_coord = (lat, lon)
        points.append({'lat': lat, 'lon': lon, 'ele': ele, 'hr': hr})

    duration_sec = 0
    if first_time and last_time:
        duration_sec = int((last_time - first_time).total_seconds())
    if duration_sec <= 0:
        duration_sec = len(points) # fallback approx 1s interval

    # Calculate elevation gain
    elev_gain = 0.0
    for i in range(1, len(elevations)):
        diff = elevations[i] - elevations[i-1]
        if diff > 0: elev_gain += diff

    avg_hr = int(sum(hr_list) / len(hr_list)) if hr_list else None
    max_hr = max(hr_list) if hr_list else None

    return {
        "format": "gpx",
        "distance_km": round(total_dist, 2),
        "duration_seconds": max(duration_sec, 1),
        "elevation_gain_m": round(elev_gain, 1),
        "avg_hr": avg_hr,
        "max_hr": max_hr,
        "trackpoints_count": len(points)
    }

def parse_tcx(file_bytes: bytes) -> Dict[str, Any]:
    """Parse file .TCX (Training Center XML)."""
    root = ET.fromstring(file_bytes)
    total_dist = 0.0
    duration_sec = 0
    hr_list = []
    elev_gain = 0.0
    prev_ele = None

    # Trackpoints
    for tp in root.findall('.//{*}Trackpoint'):
        dist_el = tp.find('.//{*}DistanceMeters')
        if dist_el is not None and dist_el.text:
            try: total_dist = max(total_dist, float(dist_el.text) / 1000.0)
            except Exception: pass

        hr_el = tp.find('.//{*}HeartRateBpm/{*}Value')
        if hr_el is not None and hr_el.text:
            try: hr_list.append(int(hr_el.text))
            except Exception: pass

        ele_el = tp.find('.//{*}AltitudeMeters')
        if ele_el is not None and ele_el.text:
            try:
                cur_ele = float(ele_el.text)
                if prev_ele is not None and cur_ele > prev_ele:
                    elev_gain += (cur_ele - prev_ele)
                prev_ele = cur_ele
            except Exception: pass

    # Total time from Lap
    for lap in root.findall('.//{*}Lap'):
        time_el = lap.find('.//{*}TotalTimeSeconds')
        if time_el is not None and time_el.text:
            try: duration_sec += int(float(time_el.text))
            except Exception: pass

    if duration_sec <= 0:
        duration_sec = max(len(hr_list), 60)

    avg_hr = int(sum(hr_list) / len(hr_list)) if hr_list else None
    max_hr = max(hr_list) if hr_list else None

    return {
        "format": "tcx",
        "distance_km": round(total_dist, 2),
        "duration_seconds": max(duration_sec, 1),
        "elevation_gain_m": round(elev_gain, 1),
        "avg_hr": avg_hr,
        "max_hr": max_hr
    }

def parse_fit(file_bytes: bytes) -> Dict[str, Any]:
    """Parse file biner .FIT (Flexible and Interoperable Data Transfer)."""
    try:
        from fitparse import FitFile
        fitfile = FitFile(io.BytesIO(file_bytes))
        total_dist_m = 0.0
        duration_sec = 0
        elev_gain = 0.0
        hr_list = []

        # Check session summary records first
        for record in fitfile.get_messages('session'):
            for record_data in record:
                if record_data.name == 'total_distance' and record_data.value:
                    total_dist_m = float(record_data.value)
                elif record_data.name in ('total_elapsed_time', 'total_timer_time') and record_data.value:
                    duration_sec = max(duration_sec, int(record_data.value))
                elif record_data.name == 'avg_heart_rate' and record_data.value:
                    hr_list.append(int(record_data.value))
                elif record_data.name == 'total_ascent' and record_data.value:
                    elev_gain = float(record_data.value)

        # If session message was missing, scan record points
        if total_dist_m == 0:
            for record in fitfile.get_messages('record'):
                for record_data in record:
                    if record_data.name == 'distance' and record_data.value:
                        total_dist_m = max(total_dist_m, float(record_data.value))
                    elif record_data.name == 'heart_rate' and record_data.value:
                        hr_list.append(int(record_data.value))

        dist_km = round(total_dist_m / 1000.0, 2)
        avg_hr = int(sum(hr_list) / len(hr_list)) if hr_list else None
        max_hr = max(hr_list) if hr_list else None

        return {
            "format": "fit",
            "distance_km": dist_km,
            "duration_seconds": max(duration_sec, 60),
            "elevation_gain_m": round(elev_gain, 1),
            "avg_hr": avg_hr,
            "max_hr": max_hr
        }
    except Exception as e:
        raise ValueError(f"Gagal mem-parsing file .FIT: {str(e)}")

def parse_activity_file(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    """Universal Dispatcher: mendeteksi ekstensi dan memanggil parser yang tepat."""
    ext = filename.lower().split('.')[-1]
    if ext == 'gpx':
        return parse_gpx(file_bytes)
    elif ext == 'tcx':
        return parse_tcx(file_bytes)
    elif ext == 'fit':
        return parse_fit(file_bytes)
    else:
        raise ValueError(f"Format .{ext} tidak didukung. Harap unggah file .GPX, .TCX, atau .FIT.")
