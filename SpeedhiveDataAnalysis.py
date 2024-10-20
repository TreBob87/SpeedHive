import requests
import tkinter as tk
from tkinter import messagebox, scrolledtext
import json
import re

auto_update_interval = 5000  # Auto-update interval in milliseconds (5 seconds)
auto_update_running = False  # Flag to track if auto-update is running

# Function to parse lap time and handle invalid entries or times over 2 minutes
def parse_lap_time(lap_time):

    if not re.match(r'^\d+:\d{2}\.\d{3}$|^\d+\.\d{3}$', lap_time):
        return None  # Skip invalid lap times
    if ':' in lap_time:
        minutes, seconds = lap_time.split(':')
        minutes = int(minutes)
        seconds = float(seconds)
        total_seconds = minutes * 60 + seconds
    else:
        try:
            total_seconds = float(lap_time)
        except ValueError:
            return None
    if total_seconds > 120:
        return None  # Exclude lap times over 2 minutes
    return total_seconds

# Function to calculate average lap time for best or last laps
def calculate_average_lap_time(lap_times, laps, method='best'):
    lap_times = [parse_lap_time(time) for time in lap_times if parse_lap_time(time) is not None]
    if method == 'best':
        sorted_lap_times = sorted(lap_times)
        selected_lap_times = sorted_lap_times[:laps]
    elif method == 'last':
        selected_lap_times = lap_times[-laps:]
    if len(selected_lap_times) == 0:
        return None
    return sum(selected_lap_times) / len(selected_lap_times)

# Function to format lap time
def format_lap_time(total_seconds):
    if total_seconds >= 60:
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds % 1) * 1000)
        return f"{minutes}:{str(seconds).zfill(2)}.{str(milliseconds).zfill(3)}"
    else:
        seconds = int(total_seconds)
        milliseconds = int((total_seconds % 1) * 1000)
        return f"{seconds}.{str(milliseconds).zfill(3)}"

# Function to fetch race data
def fetch_race_data(event_id, session_id):
    url = f"https://lt-api.speedhive.com/api/events/{event_id}/sessions/{session_id}/data"
    headers = {
        "Accept": "application/json",
        "Origin": "https://speedhive.mylaps.com",
        "Referer": "https://speedhive.mylaps.com/",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        race_data = data.get('l', [])
        race_id_map = {}
        for el in race_data:
            competitor_url = f"https://lt-api.speedhive.com/api/events/{event_id}/sessions/{session_id}/competitor/{el['id']}"
            try:
                competitor_response = requests.get(competitor_url, headers=headers)
                competitor_response.raise_for_status()
                competitor_data = competitor_response.json()
                lap_times = [
                    result['lsTm']
                    for result in competitor_data['results']
                    if 'lsTm' in result and parse_lap_time(result['lsTm']) is not None
                ]
                best_time = next(
                    (result['btTm'] for result in competitor_data['results'] if 'btTm' in result),
                    None
                )
                race_id_map[el['nam']] = {'lap_times': lap_times, 'best_time': best_time}
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    continue
                else:
                    # For other HTTP errors, re-raise the exception
                    raise
        return race_id_map
    except requests.RequestException as e:
        messagebox.showerror("Error", f"Error fetching race data: {str(e)}")
        return None



# Function to display race results in a Text widget
def display_race_results(race_id_map, laps, method, result_text_widget):
    results = []
    for name, data in race_id_map.items():
        lap_times = data['lap_times']
        avg_lap_time = calculate_average_lap_time(lap_times, laps, method=method)
        best_time = data['best_time']
        if avg_lap_time is not None:
            results.append((name, avg_lap_time, best_time))
    results.sort(key=lambda x: x[1])
    name_column_width = 20
    result_str = "{:<10} {:<20} {:>20} {:>20}\n".format("Position", "Name", "Average Lap Time", "Best Time")
    result_str += "-" * 80 + "\n"
    for i, (name, avg_lap_time, best_time) in enumerate(results):
        formatted_name = name[:name_column_width] if len(name) > name_column_width else name.ljust(name_column_width)
        result_str += "{:<10} {} {:>20} {:>20}\n".format(i + 1, formatted_name, format_lap_time(avg_lap_time), best_time)
    result_text_widget.config(state=tk.NORMAL)
    result_text_widget.delete(1.0, tk.END)
    result_text_widget.insert(tk.END, result_str)
    result_text_widget.config(state=tk.DISABLED)

# Function to start automatic updates
def start_auto_update():
    global auto_update_running
    auto_update_running = True
    auto_update()

# Function to stop automatic updates
def stop_auto_update():
    global auto_update_running
    auto_update_running = False

# Function to automatically update data at intervals
def auto_update():
    if auto_update_running:
        on_submit(auto_update=True)
        root.after(auto_update_interval, auto_update)

# Tkinter-based desktop app
def main():
    global event_id_entry, session_id_entry, method_var, laps_entry, result_text, root
    root = tk.Tk()
    root.title("Lap Timer App")

    # Event ID
    tk.Label(root, text="Enter the event ID:").grid(row=0, column=0, padx=10, pady=10)
    event_id_entry = tk.Entry(root)
    event_id_entry.grid(row=0, column=1, padx=10, pady=10)

    # Session ID
    tk.Label(root, text="Enter the session ID:").grid(row=1, column=0, padx=10, pady=10)
    session_id_entry = tk.Entry(root)
    session_id_entry.grid(row=1, column=1, padx=10, pady=10)

    # Method: best or last
    tk.Label(root, text="Calculate average for:").grid(row=2, column=0, padx=10, pady=10)
    method_var = tk.StringVar(value="best")
    tk.Radiobutton(root, text="Best Laps", variable=method_var, value="best").grid(row=2, column=1, sticky="w")
    tk.Radiobutton(root, text="Last Laps", variable=method_var, value="last").grid(row=2, column=2, sticky="w")

    # Number of laps
    tk.Label(root, text="How many laps to consider?").grid(row=3, column=0, padx=10, pady=10)
    laps_entry = tk.Entry(root)
    laps_entry.grid(row=3, column=1, padx=10, pady=10)

    # Result display with a scrollable text widget (monospaced font)
    result_text = scrolledtext.ScrolledText(root, height=15, width=80, font=("Courier", 10))
    result_text.grid(row=5, columnspan=3, padx=10, pady=10)
    result_text.config(state=tk.DISABLED)

    # Submit button
    submit_button = tk.Button(root, text="Submit", command=lambda: on_submit(auto_update=False))
    submit_button.grid(row=4, columnspan=1, pady=20)

    # Start Auto-Update button
    start_button = tk.Button(root, text="Start Auto-Update", command=start_auto_update)
    start_button.grid(row=4, column=1, padx=10, pady=20)

    # Stop Auto-Update button
    stop_button = tk.Button(root, text="Stop Auto-Update", command=stop_auto_update)
    stop_button.grid(row=4, column=2, padx=10, pady=20)

    root.mainloop()

# Submit data fetch and display logic, shared between manual and auto-update
def on_submit(auto_update=False):
    event_id = event_id_entry.get()
    session_id = session_id_entry.get()
    method = method_var.get()
    try:
        laps = int(laps_entry.get())
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid number of laps.")
        return
    if not event_id or not session_id or method not in ['best', 'last']:
        messagebox.showerror("Error", "All fields must be filled correctly.")
        return
    race_id_map = fetch_race_data(event_id, session_id)
    if race_id_map:
        display_race_results(race_id_map, laps, method, result_text)

if __name__ == "__main__":
    main()
