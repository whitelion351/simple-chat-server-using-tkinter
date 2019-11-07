import sys
import socket
from threading import Thread
import tkinter as tk
from tkinter import scrolledtext


class AppWindow(tk.Tk):
    def __init__(self, w, h):
        super(AppWindow, self).__init__()
        self.WINDOW_WIDTH = w
        self.WINDOW_HEIGHT = h

        self.server_address = "127.0.0.1"
        self.server_port = 1050
        self.username = "Test User"

        self.title("Client")
        self.canvas = tk.Canvas(self, height=self.WINDOW_HEIGHT, width=self.WINDOW_WIDTH)
        self.canvas.pack()

        self.upper_frame = tk.Frame(self, bg="#80C1FF")
        self.upper_frame.place(relx=0.05, rely=0.05, relwidth=0.90, relheight=0.75)

        self.lower_frame = tk.Frame(self, bg="#80C1FF")
        self.lower_frame.place(relx=0.05, rely=0.85, relwidth=0.90, relheight=0.10)

        self.login_widgets = []
        self.chat_widgets = []

        self.status_line = None
        self.connection_socket = None
        self.is_connected = False
        self.connection_thread = None

    def start_app(self):
        self.create_login_screen()
        self.mainloop()

    def create_login_screen(self):
        ip_label = tk.Label(self.upper_frame, text="Server IP")
        ip_label.place(anchor="center", relx=0.40, rely=0.29)
        self.login_widgets.append(ip_label)

        ip_entry = tk.Entry(self.upper_frame, font=("modern", 20), width=16, justify="center")
        if self.server_address is not None:
            ip_entry.insert(0, self.server_address)
        ip_entry.place(anchor="center", relx=0.40, rely=0.35)
        self.login_widgets.append(ip_entry)

        port_label = tk.Label(self.upper_frame, text="Server Port")
        port_label.place(anchor="center", relx=0.70, rely=0.29)
        self.login_widgets.append(port_label)

        port_entry = tk.Entry(self.upper_frame, font=("modern", 20), width=6, justify="center")
        if self.server_port is not None:
            port_entry.insert(0, self.server_port)
        port_entry.place(anchor="center", relx=0.70, rely=0.35)
        self.login_widgets.append(port_entry)

        username_label = tk.Label(self.upper_frame, text="Username")
        username_label.place(anchor="center", relx=0.5, rely=0.44)
        self.login_widgets.append(username_label)

        username_box = tk.Entry(self.upper_frame, font=("modern", 20), justify="center")
        if self.username is not None:
            username_box.insert(0, self.username)
        username_box.place(anchor="center", relx=0.5, rely=0.5)
        username_box.bind("<Return>", self.connect_to_server)
        self.login_widgets.append(username_box)

        login_button = tk.Button(self.upper_frame, text="Login", command=self.connect_to_server)
        login_button.place(anchor="center", relx=0.5, rely=0.58)
        self.login_widgets.append(login_button)

        close_button = tk.Button(self.upper_frame, text="Close App", command=self.stop_app)
        close_button.place(anchor="center", relx=0.93, rely=0.05)
        self.login_widgets.append(close_button)

    def create_chat_screen(self):
        chat_history_w = 30
        chat_history_h = 30
        chat_history = scrolledtext.ScrolledText(self.upper_frame, width=chat_history_w, height=chat_history_h,
                                                 font=("modern", 14), wrap=tk.WORD, state="disabled")
        chat_history.bind("<1>", lambda event: chat_history.focus_set())
        chat_history.place(anchor="center", relx=0.5, rely=0.5, relwidth=0.95, relheight=0.95)
        self.chat_widgets.append(chat_history)

        text_entry = tk.Entry(self.lower_frame, width=40, font=("modern", 14))
        text_entry.place(anchor="center", relx=0.5, rely=0.48, relwidth=0.97, relheight=0.5)
        text_entry.bind("<Return>", self.msg_send)
        self.chat_widgets.append(text_entry)

        close_button = tk.Button(self.upper_frame, text="Close App", command=self.stop_app)
        close_button.place(anchor="center", relx=0.93, rely=0.05)
        self.chat_widgets.append(close_button)

    @staticmethod
    def stop_app():
        sys.exit()

    def update_status_line(self, text, anchor="e", relx=0.95, rely=0.83):
        if self.status_line is None:
            self.status_line = tk.Label(self, text=text)
        else:
            self.status_line.configure(text=text)
        self.status_line.place(anchor=anchor, relx=relx, rely=rely)
        self.update_idletasks()

    def msg_receive_thread(self):
        while self.is_connected:
            try:
                msg = self.connection_socket.recv(1024)
            except (ConnectionError, socket.timeout) as e:
                print(type(e), "exception while receiving")
                self.is_connected = False
            else:
                if len(msg) == 0:
                    print("no data received by receive thread")
                    self.update_status_line("Disconnected from {}".format(self.server_address))
                    self.is_connected = False
                    continue
                self.chat_widgets[0].configure(state="normal")
                self.chat_widgets[0].insert(tk.END, msg.decode()+"\n")
                self.chat_widgets[0].see(tk.END)
                self.chat_widgets[0].configure(state="disabled")

    def msg_send(self, event=None):
        msg = event.widget.get()
        event.widget.delete(0, tk.END)
        if self.is_connected:
            try:
                if len(msg) > 0:
                    self.connection_socket.send(bytes(self.username+": "+msg, "utf-8"))
            except ConnectionError as e:
                print("exception during msg_send", e)
                self.is_connected = False
                self.update_status_line("Disconnected from {}".format(self.server_address))
                for wid in self.chat_widgets:
                    wid.destroy()
                self.chat_widgets = []
                self.create_login_screen()
        else:
            self.update_status_line("Disconnected from {}".format(self.server_address))
            for wid in self.chat_widgets:
                wid.destroy()
            self.chat_widgets = []
            self.create_login_screen()

    def connect_to_server(self, event=None):
        if self.connection_thread is not None:
            self.connection_thread.join()
            self.connection_thread = None
        self.username = self.login_widgets[5].get()
        self.server_address = self.login_widgets[1].get()
        self.server_port = int(self.login_widgets[3].get())
        self.update_status_line("connecting to {}".format(self.server_address))
        if self.is_connected is False:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                conn.connect((self.server_address, self.server_port))
                resp = conn.recv(4)
                if len(resp) == 4:
                    conn.send(bytes(self.username, "utf-8"))
                    self.connection_socket = conn
                    self.update_status_line("Connected to {}".format(self.server_address))
                    self.is_connected = True
                    for wid in self.login_widgets:
                        wid.destroy()
                    self.login_widgets = []
                    self.create_chat_screen()
                    self.connection_thread = Thread(target=self.msg_receive_thread, daemon=True)
                    self.connection_thread.start()
                else:
                    raise ConnectionAbortedError
            except (ConnectionError, socket.timeout) as e:
                self.update_status_line("Connection failed")
                print(type(e), "when connecting to server")


if __name__ == "__main__":
    first_window = AppWindow(800, 650)
    try:
        first_window.start_app()
    except KeyboardInterrupt:
        pass
    finally:
        print("client app closed")
