import tkinter as tk
from tkinter import ttk
import psutil
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
import winreg  # Windows kayıt defterini kullanmak için eklenmiştir.

class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistem Performans Monitörü")
        self.root.geometry("1000x600")

        # Sidebar
        self.sidebar = tk.Frame(self.root, width=200, bg="gray")
        self.sidebar.pack(side="left", fill="y")

        # Collapsed state flag
        self.sidebar_collapsed = False

        # Icon images with resized icons
        self.icons = {
            "İşlemler": self.load_icon("images/islem_icon.png"),
            "Performans": self.load_icon("images/performans_icon.png"),
            "Uygulama Geçmişi": self.load_icon("images/uygulama_gecmisi_icon.png"),
            "Başlangıç Uygulamaları": self.load_icon("images/baslangic_icon.png"),
            "Kullanıcılar": self.load_icon("images/kullanici_icon.png"),
            "Ayrıntılar": self.load_icon("images/ayrintilar_icon.png"),
            "Hizmetler": self.load_icon("images/hizmetler_icon.png")
        }

        # Toggle button (hamburger icon)
        self.toggle_button = tk.Button(self.sidebar, text="≡", font=("Arial", 12, "bold"), command=self.toggle_sidebar)
        self.toggle_button.pack(pady=5, anchor="w", fill="x")

        # Menu buttons frame
        self.menu_buttons_frame = tk.Frame(self.sidebar, bg="gray")
        self.menu_buttons_frame.pack(fill="y", anchor="w")

        # Content frame
        self.content = tk.Frame(self.root, bg="white")
        self.content.pack(side="right", fill="both", expand=True)

        # Sidebar buttons
        self.button_texts = [
            "İşlemler", "Performans", "Uygulama Geçmişi",
            "Başlangıç Uygulamaları", "Kullanıcılar", "Ayrıntılar", "Hizmetler"
        ]
        self.button_commands = [
            self.show_processes, self.show_performance, self.show_app_history,
            self.show_startup_apps, self.show_users, self.show_details, self.show_services
        ]

        self.buttons = []
        self.create_sidebar_buttons()

        # Start with the Processes view
        self.show_processes()

        # Performance data lists
        self.cpu_usage = []
        self.memory_usage = []

        # Thread control
        self.running = True
        self.thread = threading.Thread(target=self.update_performance_data)
        self.thread.daemon = True  # Daemon thread
        self.thread.start()

    def load_icon(self, path, size=(24, 24)):
        """İkon dosyasını açar, yeniden boyutlandırır ve döndürür."""
        image = Image.open(path)
        image = image.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(image)

    def toggle_sidebar(self):
        if self.sidebar_collapsed:
            self.expand_sidebar()
        else:
            self.collapse_sidebar()

    def collapse_sidebar(self):
        self.sidebar.config(width=50)
        for button in self.buttons:
            button.config(text="", width=50, compound="top")
        self.sidebar_collapsed = True

    def expand_sidebar(self):
        self.sidebar.config(width=200)
        for button, text in zip(self.buttons, self.button_texts):
            button.config(text=text, width=200, compound="left")
        self.sidebar_collapsed = False

    def create_sidebar_buttons(self):
        for name, command in zip(self.button_texts, self.button_commands):
            button = tk.Button(self.menu_buttons_frame, text=name, command=command, width=200, anchor="w", compound="left")
            button.config(image=self.icons[name])
            button.pack(fill="x", pady=2)
            self.buttons.append(button)

    def show_processes(self):
        self.clear_content_frame()
        self.processes_frame = tk.Frame(self.content)
        self.processes_frame.pack(fill="both", expand=True)

        columns = ("PID", "Ad", "CPU", "Bellek")
        tree = ttk.Treeview(self.processes_frame, columns=columns, show="headings")
        tree.heading("PID", text="PID")
        tree.heading("Ad", text="Ad")
        tree.heading("CPU", text="CPU (%)")
        tree.heading("Bellek", text="Bellek (MB)")
        tree.pack(fill="both", expand=True)

        self.update_processes(tree)

    def update_processes(self, tree):
        # Önceki bellek değerlerini saklamak için bir sözlük
        self.prev_memory_usage = getattr(self, 'prev_memory_usage', {})

        for row in tree.get_children():
            tree.delete(row)

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']
                cpu = proc.info['cpu_percent']
                memory = proc.info['memory_info'].rss / (1024 * 1024)  # MB olarak belleği al

                # Bellek kullanımında değişiklik var mı kontrol et
                if pid in self.prev_memory_usage and self.prev_memory_usage[pid] != memory:
                    # Yeni veri ekle ve geçici olarak yeşil renge ayarla
                    item = tree.insert("", "end", values=(pid, name, cpu, memory))
                    tree.item(item, tags=("changed",))
                    self.root.after(1000, lambda i=item: tree.item(i, tags=("")))  # 1 saniye sonra eski duruma dön
                else:
                    # Bellek kullanımında değişiklik yoksa normal ekle
                    tree.insert("", "end", values=(pid, name, cpu, memory))

                # Bellek kullanımını güncelle
                self.prev_memory_usage[pid] = memory

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # Değişiklik için tag ayarları
        tree.tag_configure("changed", background="light green")

        self.root.after(2000, self.update_processes, tree)

    def clear_content_frame(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def show_performance(self):
        self.clear_content_frame()
        self.create_performance_graph()

    def create_performance_graph(self):
        # Grafik için bir figür oluştur
        self.fig, self.ax = plt.subplots(figsize=(8, 4))

        self.ax.set_title('CPU ve Bellek Kullanımı')
        self.ax.set_xlabel('Zaman (s)')
        self.ax.set_ylabel('Kullanım (%)')
        self.ax.set_ylim(0, 100)

        # Y ekseninde 10’ar 10’ar aralıklarla değerleri göster
        self.ax.set_yticks([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])

        # Çizgileri başlat
        self.cpu_line, = self.ax.plot([], [], label='CPU Kullanımı (%)', color='blue')
        self.memory_line, = self.ax.plot([], [], label='Bellek Kullanımı (%)', color='orange')

        # Legend ekle
        self.ax.legend()

        # Matplotlib figürünü Tkinter penceresine yerleştirme
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.content)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.update_performance_graph()

    def update_performance_graph(self):
        # Update the plot
        self.cpu_line.set_xdata(range(len(self.cpu_usage)))
        self.cpu_line.set_ydata(self.cpu_usage)

        self.memory_line.set_xdata(range(len(self.memory_usage)))
        self.memory_line.set_ydata(self.memory_usage)

        # Auto scale the axes
        self.ax.relim()
        self.ax.autoscale_view()

        # Redraw the canvas
        self.canvas.draw()

        # Schedule next update
        self.root.after(1000, self.update_performance_graph)  # Update every second

    def update_performance_data(self):
        while self.running:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent

            # Append current usage to lists
            self.cpu_usage.append(cpu_percent)
            self.memory_usage.append(memory_percent)

            time.sleep(1)  # Sleep for 1 second

    def show_app_history(self):
        self.clear_content_frame()
        # Uygulama geçmişi bilgilerini gösterecek kodlar buraya eklenebilir

    def show_startup_apps(self):
        self.clear_content_frame()
        self.startup_frame = tk.Frame(self.content)
        self.startup_frame.pack(fill="both", expand=True)

        columns = ("Ad", "Yol")
        tree = ttk.Treeview(self.startup_frame, columns=columns, show="headings")
        tree.heading("Ad", text="Ad")
        tree.heading("Yol", text="Yol")
        tree.pack(fill="both", expand=True)

        self.update_startup_apps(tree)

    def update_startup_apps(self, tree):
        startup_apps = self.get_startup_apps()
        for row in tree.get_children():
            tree.delete(row)
        for name, path in startup_apps:
            tree.insert("", "end", values=(name, path))

    def get_startup_apps(self):
        """Başlangıç uygulamalarını almak için kayıt defterinden bilgi alır."""
        startup_apps = []

        # Kayıt defteri anahtarı
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            for i in range(winreg.QueryInfoKey(key)[1]):
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    startup_apps.append((name, value))
                except OSError:
                    break

        return startup_apps

    def show_users(self):
        self.clear_content_frame()
        # Kullanıcı bilgilerini gösterecek kodlar buraya eklenebilir

    def show_details(self):
        self.clear_content_frame()
        # Ayrıntılı bilgileri gösterecek kodlar buraya eklenebilir

    def show_services(self):
        self.clear_content_frame()
        # Hizmet bilgilerini gösterecek kodlar buraya eklenebilir

if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.mainloop()
