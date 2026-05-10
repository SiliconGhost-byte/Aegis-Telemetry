import customtkinter as ctk
import requests
import threading
import concurrent.futures
from PIL import Image
import io
import pandas as pd
import os
import json
import webbrowser
import tkinter as tk

# Initialize the core forge
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "Aegis_Config.json"

if not os.path.exists("Aegis_Cache"):
    os.makedirs("Aegis_Cache")

class AegisTelemetryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AEGIS TELEMETRY: Executive Command")
        self.geometry("1100x750")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        self.current_games = [] 
        
        self.active_api = ""
        self.active_id = ""
        self._pending_render = []
        self._render_job = None
        self._active_search_query = ""

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#121212")
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.logo_label = ctk.CTkLabel(self.sidebar, text="AEGIS TELEMETRY", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="#FFFFFF")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 10))

        self.status_label = ctk.CTkLabel(self.sidebar, text="Status: Awaiting Coordinates", text_color="gray", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.status_label.grid(row=1, column=0, padx=20, pady=10)

        # Load saved coordinates
        self.saved_config = self.load_config()

        self.build_login_screen()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f: return json.load(f)
            except: pass
        return {"api_key": "", "steam_id": ""}

    def save_config(self, api, sid):
        try:
            with open(CONFIG_FILE, 'w') as f: json.dump({"api_key": api, "steam_id": sid}, f)
        except: pass

    # --- CLIPBOARD MASTERY ---
    def paste_to_entry(self, entry_widget):
        try:
            entry_widget.insert("end", self.clipboard_get())
        except: pass

    def make_context_menu(self, widget):
        menu = tk.Menu(widget, tearoff=0, bg="#242424", fg="#FFFFFF", activebackground="#007FFF")
        menu.add_command(label="Paste", command=lambda: self.paste_to_entry(widget))
        menu.add_command(label="Clear", command=lambda: widget.delete(0, "end"))
        widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    def build_login_screen(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1A1A1A")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.welcome_label = ctk.CTkLabel(self.main_frame, text="INITIALIZE BREACH", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color="#FFFFFF")
        self.welcome_label.pack(pady=(120, 20))

        # --- API KEY ZONE ---
        api_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        api_frame.pack(pady=(10, 0))
        
        self.api_entry = ctk.CTkEntry(api_frame, placeholder_text="Enter Steam Web API Key", width=400, height=45, font=ctk.CTkFont(family="Segoe UI", size=14), border_color="#333333")
        self.api_entry.pack(side="left", padx=(0, 10))
        self.api_entry.insert(0, self.saved_config.get("api_key", ""))
        self.make_context_menu(self.api_entry)

        api_paste_btn = ctk.CTkButton(api_frame, text="📋 Paste", width=60, height=45, fg_color="#333333", hover_color="#555555", command=lambda: self.paste_to_entry(self.api_entry))
        api_paste_btn.pack(side="left")

        api_link = ctk.CTkLabel(self.main_frame, text="Where do I get an API Key?", font=ctk.CTkFont(size=12, underline=True), text_color="#007FFF", cursor="hand2")
        api_link.pack(pady=(5, 15))
        api_link.bind("<Button-1>", lambda e: webbrowser.open("https://steamcommunity.com/dev/apikey"))

        # --- STEAM ID ZONE ---
        id_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        id_frame.pack(pady=(10, 0))

        self.id_entry = ctk.CTkEntry(id_frame, placeholder_text="Enter SteamID64", width=400, height=45, font=ctk.CTkFont(family="Segoe UI", size=14), border_color="#333333")
        self.id_entry.pack(side="left", padx=(0, 10))
        self.id_entry.insert(0, self.saved_config.get("steam_id", ""))
        self.make_context_menu(self.id_entry)

        id_paste_btn = ctk.CTkButton(id_frame, text="📋 Paste", width=60, height=45, fg_color="#333333", hover_color="#555555", command=lambda: self.paste_to_entry(self.id_entry))
        id_paste_btn.pack(side="left")

        id_link = ctk.CTkLabel(self.main_frame, text="How do I find my SteamID64?", font=ctk.CTkFont(size=12, underline=True), text_color="#007FFF", cursor="hand2")
        id_link.pack(pady=(5, 30))
        id_link.bind("<Button-1>", lambda e: webbrowser.open("https://steamid.io/"))

        # --- AUTH BUTTON ---
        self.launch_btn = ctk.CTkButton(self.main_frame, text="AUTHENTICATE", height=45, width=200, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), fg_color="#00FF41", hover_color="#00C432", text_color="#000000", command=self.start_breach)
        self.launch_btn.pack(pady=10)

    def start_breach(self):
        api_key = self.api_entry.get().strip()
        steam_id = self.id_entry.get().strip()

        if not api_key or not steam_id:
            self.status_label.configure(text="Error: Coordinates Missing", text_color="#FF4C4C")
            return

        # Secure Coordinates
        self.active_api = api_key
        self.active_id = steam_id
        self.save_config(api_key, steam_id)

        self.status_label.configure(text="Status: Breaching Network...", text_color="#00FF41")
        self.launch_btn.configure(state="disabled")

        threading.Thread(target=self.execute_harvest, args=(self.active_api, self.active_id), daemon=True).start()

    def force_sync(self):
        self.status_label.configure(text="Status: Synchronizing Cloud...", text_color="#007FFF")
        threading.Thread(target=self.execute_harvest, args=(self.active_api, self.active_id), daemon=True).start()

    def execute_harvest(self, api_key, steam_id):
        try:
            url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={steam_id}&format=json&include_appinfo=1"
            response = requests.get(url)
            data = response.json()

            if "response" not in data or "games" not in data["response"]:
                self.after(0, self.update_status, "Error: Invalid Keys", "#FF4C4C")
                return

            games = data["response"]["games"]
            for g in games:
                if 'unlocked_ach' not in g: g['unlocked_ach'] = None
                if 'total_ach' not in g: g['total_ach'] = None
                if 'ctk_image' not in g: g['ctk_image'] = None # New RAM cache slot

            self.current_games = games
            total_games = len(games)
            total_hours = sum(game.get("playtime_forever", 0) for game in games) / 60

            self.after(0, self.show_telemetry_dashboard, total_games, total_hours)

        except Exception as e:
            self.after(0, self.update_status, "Error: Network Failure", "#FF4C4C")

    def update_status(self, msg, color):
        self.status_label.configure(text=msg, text_color=color)
        if hasattr(self, 'launch_btn') and self.launch_btn.winfo_exists():
            self.launch_btn.configure(state="normal")

    def show_telemetry_dashboard(self, total_games, total_hours):
        if hasattr(self, 'main_frame') and self.main_frame.winfo_exists(): self.main_frame.destroy()
        if hasattr(self, 'dash_frame') and self.dash_frame.winfo_exists(): self.dash_frame.destroy()

        self.status_label.configure(text="Status: Uplink Active", text_color="#00FF41")

        self.dash_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1A1A1A")
        self.dash_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.dash_frame.grid_rowconfigure(2, weight=1) 
        self.dash_frame.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(self.dash_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 5))
        
        title_lbl = ctk.CTkLabel(header_frame, text="ASSET INVENTORY", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color="#FFFFFF")
        title_lbl.pack(side="left")

        export_btn = ctk.CTkButton(header_frame, text="EXPORT DOSSIER", width=140, height=35, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), fg_color="#00FF41", hover_color="#00C432", text_color="#000000", command=self.export_dossier)
        export_btn.pack(side="right", padx=(10, 0))

        sync_btn = ctk.CTkButton(header_frame, text="SYNC CLOUD", width=120, height=35, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), fg_color="#007FFF", hover_color="#005CBE", text_color="#FFFFFF", command=self.force_sync)
        sync_btn.pack(side="right", padx=(20, 0))

        stats_lbl = ctk.CTkLabel(header_frame, text=f"Total Assets: {total_games}  |  Hours: {total_hours:,.1f}", font=ctk.CTkFont(family="Segoe UI", size=14), text_color="#007FFF")
        stats_lbl.pack(side="right", pady=5)

        filter_frame = ctk.CTkFrame(self.dash_frame, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 10))

        self.search_entry = ctk.CTkEntry(filter_frame, placeholder_text="Search Armory...", width=300, height=35, font=ctk.CTkFont(family="Segoe UI", size=14), border_color="#333333")
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", self.trigger_refresh)

        sort_lbl = ctk.CTkLabel(filter_frame, text="Sort Protocol:", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="gray")
        sort_lbl.pack(side="left", padx=(20, 10))

        self.sort_combo = ctk.CTkOptionMenu(filter_frame, values=["Playtime (High-Low)", "Alphabetical (A-Z)"], width=180, fg_color="#242424", button_color="#333333", button_hover_color="#007FFF", command=self.trigger_refresh)
        self.sort_combo.pack(side="left")

        self.scroll_matrix = ctk.CTkScrollableFrame(self.dash_frame, fg_color="transparent", corner_radius=0)
        self.scroll_matrix.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)

        self.trigger_refresh()

    def trigger_refresh(self, event=None):
        if self._render_job:
            self.after_cancel(self._render_job)
            self._render_job = None
            
        for widget in self.scroll_matrix.winfo_children():
            widget.destroy()

        self._active_search_query = self.search_entry.get().lower()
        sort_protocol = self.sort_combo.get()

        valid_games = []
        for g in self.current_games:
            playtime = g.get('playtime_forever', 0) / 60
            if playtime < 0.1 and not self._active_search_query: continue
            if self._active_search_query in g.get('name', 'Unknown').lower():
                valid_games.append(g)

        if sort_protocol == "Playtime (High-Low)":
            self._pending_render = sorted(valid_games, key=lambda k: k.get('playtime_forever', 0), reverse=True)
        else: 
            self._pending_render = sorted(valid_games, key=lambda k: k.get('name', ''))

        self.render_batch()

    def render_batch(self):
        if not self._pending_render:
            self._render_job = None
            return

        batch = self._pending_render[:15]
        self._pending_render = self._pending_render[15:]

        for game in batch:
            playtime_hrs = game.get('playtime_forever', 0) / 60

            row = ctk.CTkFrame(self.scroll_matrix, corner_radius=6, fg_color="#242424", border_width=1, border_color="#333333")
            row.pack(fill="x", pady=6, ipady=6)

            img_lbl = ctk.CTkLabel(row, text="[FETCHING...]", width=120, height=45, fg_color="#121212", font=ctk.CTkFont(size=10))
            img_lbl.pack(side="left", padx=(10, 15), pady=5)

            name_lbl = ctk.CTkLabel(row, text=game.get('name', 'Unknown Asset'), font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#FFFFFF", anchor="w")
            name_lbl.pack(side="left", fill="x", expand=True)

            right_container = ctk.CTkFrame(row, fg_color="transparent")
            right_container.pack(side="right", padx=20)

            prog = ctk.CTkProgressBar(right_container, width=160, height=8, progress_color="#555555", fg_color="#121212")
            prog.pack(pady=(0, 4))

            mastery_lbl = ctk.CTkLabel(right_container, text="SCANNING...", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color="#777777")
            mastery_lbl.pack(anchor="e")

            hrs_lbl = ctk.CTkLabel(right_container, text=f"TIME: {playtime_hrs:.1f} HRS", font=ctk.CTkFont(family="Consolas", size=10), text_color="#AAAAAA")
            hrs_lbl.pack(anchor="e")

            # --- THE RAM INJECTION ARCHITECTURE (Zero I/O on main thread) ---
            if game.get('ctk_image'):
                img_lbl.configure(image=game['ctk_image'], text="")
            
            if game.get('total_ach') is not None:
                unlocked = game.get('unlocked_ach', 0)
                total = game.get('total_ach', 0)
                ratio = unlocked / total if total > 0 else 0
                
                prog.set(ratio)
                if total == 0:
                    mastery_lbl.configure(text="NO ACHIEVEMENTS", text_color="#555555")
                else:
                    color = "#00FF41" if ratio == 1.0 else "#007FFF"
                    prog.configure(progress_color=color)
                    mastery_lbl.configure(text=f"{unlocked}/{total} UNLOCKED", text_color=color)
            else:
                prog.set(0)
                self.executor.submit(self.deep_scan_worker, self.active_api, self.active_id, game, img_lbl, prog, mastery_lbl)

        self._render_job = self.after(10, self.render_batch)

    def deep_scan_worker(self, api_key, steam_id, game, img_lbl, prog_bar, mastery_lbl):
        app_id = game.get('appid')
        cache_path = f"Aegis_Cache/{app_id}.jpg"
        
        # 1. RAM CACHE PROTOCOL
        if not game.get('ctk_image'):
            try:
                if os.path.exists(cache_path):
                    image = Image.open(cache_path)
                    ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(120, 45))
                    game['ctk_image'] = ctk_image # Store in RAM
                    if img_lbl.winfo_exists(): img_lbl.after(0, lambda: img_lbl.configure(image=ctk_image, text=""))
                else:
                    url = f"https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/capsule_184x69.jpg"
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        image = Image.open(io.BytesIO(resp.content))
                        image.convert('RGB').save(cache_path, "JPEG")
                        ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(120, 45))
                        game['ctk_image'] = ctk_image # Store in RAM
                        if img_lbl.winfo_exists(): img_lbl.after(0, lambda: img_lbl.configure(image=ctk_image, text=""))
            except Exception: pass

        # 2. Achievement Fetch & Memory Lock
        try:
            ach_url = f"http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/?appid={app_id}&key={api_key}&steamid={steam_id}"
            ach_resp = requests.get(ach_url, timeout=5)
            
            if ach_resp.status_code == 200:
                ach_data = ach_resp.json()
                if "playerstats" in ach_data and "achievements" in ach_data["playerstats"]:
                    achievements = ach_data["playerstats"]["achievements"]
                    total_ach = len(achievements)
                    unlocked_ach = sum(1 for a in achievements if a.get("achieved", 0) == 1)

                    game['unlocked_ach'] = unlocked_ach
                    game['total_ach'] = total_ach

                    ratio = unlocked_ach / total_ach if total_ach > 0 else 0
                    text_str = f"{unlocked_ach}/{total_ach} UNLOCKED"
                    color = "#00FF41" if ratio == 1.0 else "#007FFF" 

                    if prog_bar.winfo_exists():
                        prog_bar.after(0, lambda: prog_bar.set(ratio))
                        prog_bar.after(0, lambda: prog_bar.configure(progress_color=color))
                    if mastery_lbl.winfo_exists():
                        mastery_lbl.after(0, lambda: mastery_lbl.configure(text=text_str, text_color=color))
                    return

            game['unlocked_ach'] = 0
            game['total_ach'] = 0
            if prog_bar.winfo_exists(): prog_bar.after(0, lambda: prog_bar.set(0))
            if mastery_lbl.winfo_exists(): mastery_lbl.after(0, lambda: mastery_lbl.configure(text="NO ACHIEVEMENTS", text_color="#555555"))

        except Exception:
            if prog_bar.winfo_exists(): prog_bar.after(0, lambda: prog_bar.set(0))
            if mastery_lbl.winfo_exists(): mastery_lbl.after(0, lambda: mastery_lbl.configure(text="SCAN FAILED", text_color="#FF4C4C"))

    def export_dossier(self):
        self.status_label.configure(text="Status: Forging Dossier...", text_color="#007FFF")
        
        data = []
        for g in self.current_games:
            playtime = g.get('playtime_forever', 0) / 60
            if playtime < 0.1: continue

            unlocked = g.get('unlocked_ach', 0)
            total = g.get('total_ach', 0)
            
            status = "In Progress"
            comp_pct = 0
            if total > 0:
                comp_pct = (unlocked / total) * 100
                if unlocked == total: status = "Flawless Mastery (100%)"
            elif total == 0 and unlocked == 0:
                status = "No Achievements"

            data.append({
                'Asset Name': g.get('name', 'Unknown'),
                'Playtime (Hours)': round(playtime, 2),
                'Unlocked Achievements': unlocked,
                'Total Achievements': total,
                'Completion %': round(comp_pct, 2),
                'Tactical Status': status
            })

        try:
            df = pd.DataFrame(data)
            writer = pd.ExcelWriter('Aegis_Executive_Dossier.xlsx', engine='xlsxwriter')
            df.to_excel(writer, sheet_name='Telemetry', index=False)

            workbook = writer.book
            worksheet = writer.sheets['Telemetry']
            header_fmt = workbook.add_format({'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#1A1A1A', 'font_name': 'Segoe UI'})
            
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_fmt)
            
            worksheet.set_column('A:A', 40)
            worksheet.set_column('B:F', 22)
            
            writer.close()
            self.status_label.configure(text="Status: Dossier Exported Successfully", text_color="#00FF41")
        except Exception as e:
            self.status_label.configure(text="Error: Close Excel before exporting", text_color="#FF4C4C")

if __name__ == "__main__":
    app = AegisTelemetryApp()
    app.mainloop()