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
        self.user_names = []
        self.user_list_labels = []

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

    def create_login_screen(self):
        bg_frame = tk.Frame(self.upper_frame, bg="#80C1FF")
        bg_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.login_widgets.append(bg_frame)

        ip_label = tk.Label(self.upper_frame, text="Server IP")
        ip_label.place(anchor="center", relx=0.40, rely=0.29)
        self.login_widgets.append(ip_label)

        ip_entry = tk.Entry(self.upper_frame, font=("modern", 12), width=16, justify="center")
        if self.server_address is not None:
            ip_entry.insert(0, self.server_address)
        ip_entry.place(anchor="center", relx=0.40, rely=0.35)
        self.login_widgets.append(ip_entry)

        port_label = tk.Label(self.upper_frame, text="Server Port")
        port_label.place(anchor="center", relx=0.70, rely=0.29)
        self.login_widgets.append(port_label)

        port_entry = tk.Entry(self.upper_frame, font=("modern", 12), width=6, justify="center")
        if self.server_port is not None:
            port_entry.insert(0, self.server_port)
        port_entry.place(anchor="center", relx=0.70, rely=0.35)
        self.login_widgets.append(port_entry)

        username_label = tk.Label(self.upper_frame, text="Username")
        username_label.place(anchor="center", relx=0.5, rely=0.44)
        self.login_widgets.append(username_label)

        username_box = tk.Entry(self.upper_frame, font=("modern", 12), justify="center")
        if self.username is not None:
            username_box.insert(0, self.username)
        username_box.place(anchor="center", relx=0.5, rely=0.5)
        username_box.focus_set()
        username_box.bind("<Return>", lambda event: self.connect_to_server())
        self.login_widgets.append(username_box)

        login_button = tk.Button(self.upper_frame, text="Login", command=self.connect_to_server)
        login_button.place(anchor="center", relx=0.5, rely=0.58)
        self.login_widgets.append(login_button)

    def create_chat_screen(self):
        chat_history_w = 30
        chat_history_h = 30
        chat_history = scrolledtext.ScrolledText(self.upper_frame, width=chat_history_w, height=chat_history_h,
                                                 font=("modern", 12), wrap=tk.WORD, state="disabled")
        chat_history.place(relx=0.02, rely=0.02, relwidth=0.96, relheight=0.95)
        chat_history.bind("<1>", lambda event: chat_history.focus_set())
        self.chat_widgets.append(chat_history)

        text_entry = tk.Entry(self.lower_frame, width=40, font=("modern", 12), state="disabled")
        text_entry.place(anchor="center", relx=0.5, rely=0.48, relwidth=0.97, relheight=0.5)
        text_entry.bind("<Return>", self.msg_send)
        self.chat_widgets.append(text_entry)

        user_list_frame = tk.Frame(self.upper_frame, bg="#00C1FF")
        user_list_frame.place(relx=0.98, rely=0.02, relwidth=0.30, relheight=0.95)
        user_list_frame.bind("<1>", self.toggle_user_list)
        user_list_bg = tk.Frame(user_list_frame, bg="#FFFFFF")
        user_list_bg.place(relx=0.1, rely=0.03, relwidth=0.8, relheight=0.94)
        self.chat_widgets.append(user_list_frame)

        close_button = tk.Button(self, text="Close App", command=self.stop_app)
        close_button.place(anchor="center", relx=0.895, rely=0.02)
        self.chat_widgets.append(close_button)

    def toggle_user_list(self, event=None):
        if event:
            x = float(event.widget.place_info()["relx"])
            if x > 0.9:
                self.refresh_user_list()
                self.chat_widgets[0].place(relwidth=0.68)
                event.widget.place(relx=0.7)
            else:
                self.chat_widgets[0].place(relwidth=0.96)
                event.widget.place(relx=0.98)

    def refresh_user_list(self):
        for u in self.user_list_labels:
            u.destroy()
        user_list_labels = []
        y_pos = 0.05
        y_inc = 0.05
        self.user_names = sorted(self.user_names)
        for user in self.user_names:
            label = tk.Label(self.chat_widgets[2], text=user, bg="#FFFFFF", anchor="w")
            if user == self.username:
                label.configure(font=("modern", 12, "bold"))
            else:
                label.configure(font=("modern", 12))
            label.place(relx=0.1, rely=y_pos, relwidth=0.8)
            user_list_labels.append(label)
            y_pos += y_inc
        self.user_list_labels = user_list_labels

    def update_status_line(self, text, anchor="e", rel_x=0.95, rel_y=0.83):
        if self.status_line is None:
            self.status_line = tk.Label(self, text=text)
        else:
            self.status_line.configure(text=text)
        self.status_line.place(anchor=anchor, relx=rel_x, rely=rel_y)
        self.update_idletasks()

    def msg_receive_thread(self):
        """
            First byte is msg type
            0 = will be server sending options or something
            1 = user joined
            2 = user left
            3 = user message
        """
        while self.is_connected:
            try:
                msg_type = self.connection_socket.recv(1)
                if len(msg_type) == 0:
                    print("disconnect waiting for msg_type")
                    self.update_status_line("Disconnected from {}".format(self.server_address))
                    self.is_connected = False
                    continue
                msg_type = int().from_bytes(msg_type, "little")
                msg_data = self.connection_socket.recv(1024)
                if len(msg_data) == 0:
                    print("disconnect waiting for msg_data")
                    self.update_status_line("Disconnected from {}".format(self.server_address))
                    self.is_connected = False
                    continue
                msg_data = msg_data.decode("utf-8", "could not decode")
                if msg_type == 0:
                    print("received special server data but i dunno what to do :)")
                    print(msg_data)
                    continue
                elif msg_type == 1:
                    self.user_names.append(msg_data)
                    self.refresh_user_list()
                    msg_string = "<"+msg_data+" has joined>"
                    self.update_chat_history(msg_string)
                elif msg_type == 2:
                    self.user_names.remove(msg_data)
                    self.refresh_user_list()
                    msg_string = "<"+msg_data+" has left>"
                    self.update_chat_history(msg_string)
                elif msg_type == 3:
                    self.update_chat_history(msg_data)
                else:
                    print("invalid msg_type received")
            except (ConnectionError, socket.timeout) as e:
                print(e, "exception while receiving")
                self.is_connected = False

    def update_chat_history(self, msg):
        self.chat_widgets[0].configure(state="normal")
        self.chat_widgets[0].insert(tk.END, msg + "\n")
        self.chat_widgets[0].configure(state="disabled")
        self.chat_widgets[0].see(tk.END)

    def msg_send(self, event=None):
        msg = event.widget.get()
        event.widget.delete(0, tk.END)
        if self.is_connected:
            try:
                if len(msg) > 0:
                    self.connection_socket.send(bytes(msg[:1024], "utf-8"))
            except ConnectionError as e:
                print("exception during msg_send", e)
                self.is_connected = False
                self.update_status_line("Disconnected from {}".format(self.server_address))
                self.chat_widgets[1].configure(state="disabled")
                self.create_login_screen()
        else:
            self.update_status_line("Disconnected from {}".format(self.server_address))
            self.chat_widgets[1].configure(state="disabled")
            self.create_login_screen()

    def connect_to_server(self):
        if self.connection_thread is not None:
            self.connection_thread.join()
            self.connection_thread = None
        self.username = self.login_widgets[6].get()
        self.server_address = self.login_widgets[2].get()
        self.server_port = int(self.login_widgets[4].get())
        self.update_status_line("connecting to {}".format(self.server_address))
        if self.is_connected is False:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                conn.connect((self.server_address, self.server_port))
                resp = conn.recv(1024)
                if len(resp) == 4:
                    conn.send(bytes(self.username, "utf-8"))
                    resp = int().from_bytes(conn.recv(1), byteorder="little")
                    if resp == 0:
                        print("username already in use")
                        raise ConnectionAbortedError("Username already in use")
                    else:
                        self.receive_user_list(resp, conn)
                    self.connection_socket = conn
                    self.update_status_line("Connected to {}".format(self.server_address))
                    self.is_connected = True
                    for wid in self.login_widgets:
                        wid.destroy()
                    self.login_widgets = []
                    self.chat_widgets[1].configure(state="normal")
                    self.chat_widgets[1].focus_set()
                    self.connection_thread = Thread(target=self.msg_receive_thread, daemon=True)
                    self.connection_thread.start()
                else:
                    raise ConnectionAbortedError("Unexpected response from server")
            except (ConnectionError, socket.timeout) as e:
                self.update_status_line(e)
                print(e, "when connecting to server")

    def receive_user_list(self, count, conn):
        user_names = []
        for _ in range(count):
            user_names.append(conn.recv(1024).decode("utf-8", "n/a"))
            conn.send(bytes([1]))
        self.user_names = sorted(user_names)

    def start_app(self):
        self.create_chat_screen()
        self.create_login_screen()
        self.mainloop()

    def stop_app(self):
        print("closing client app")
        if self.connection_socket is not None:
            self.connection_socket.close()
        sys.exit()


if __name__ == "__main__":
    first_window = AppWindow(800, 650)
    try:
        first_window.start_app()
    except KeyboardInterrupt:
        first_window.stop_app()
        print("client app closed")
