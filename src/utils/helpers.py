import re

def wait_time_to_days(wait_time_str):
    """Convert wait time string to number of days."""
    if not wait_time_str:
        return 0
    match = re.match(r'(\d+)\s*days?', wait_time_str.lower())
    if match:
        return int(match.group(1))
    return 0

def wait_time_to_minutes(wait_time_str):
    """Convert wait time string to number of minutes."""
    if not wait_time_str:
        return 0
    match = re.match(r'(\d+)\s*minutes?', wait_time_str.lower())
    if match:
        return int(match.group(1))
    return 0 