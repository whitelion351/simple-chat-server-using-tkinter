import sys
import socket
from threading import Thread
import tkinter as tk
from tkinter import scrolledtext
import select


class AppWindow(tk.Tk):
    def __init__(self, w, h):
        super(AppWindow, self).__init__()
        self.WINDOW_WIDTH = w
        self.WINDOW_HEIGHT = h

        self.server_address = None
        self.server_port = None
        self.username = "Server"

        self.user_list_labels = []

        self.title("Server")
        self.canvas = tk.Canvas(self, height=self.WINDOW_HEIGHT, width=self.WINDOW_WIDTH)
        self.canvas.pack()

        self.upper_frame = tk.Frame(self, bg="#80C1FF")
        self.upper_frame.place(relx=0.05, rely=0.05, relwidth=0.90, relheight=0.75)

        self.lower_frame = tk.Frame(self, bg="#80C1FF")
        self.lower_frame.place(relx=0.05, rely=0.85, relwidth=0.90, relheight=0.10)

        self.chat_widgets = []

        self.status_line = None
        self.total_clients = 0
        self.socket_list = []
        self.client_dict = {}
        self.connection_socket = None
        self.connection_thread = None

    def server_listen_thread(self):
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.bind(("0.0.0.0", 1050))
        conn.listen(5)
        self.connection_socket = conn
        self.socket_list.append(conn)
        print("waiting for connections")
        while True:
            read_sockets, _, exception_sockets = select.select(self.socket_list, [], self.socket_list)
            for notified_socket in read_sockets:
                if notified_socket == self.connection_socket:
                    self.accept_connection()
                else:
                    self.msg_receive(notified_socket)
            for notified_socket in exception_sockets:
                if notified_socket == self.connection_socket:
                    continue
                else:
                    self.remove_connection(notified_socket)

    def accept_connection(self):
        s, addy = self.connection_socket.accept()
        s.send((bytes("what", "utf-8")))
        resp = s.recv(1024).decode()
        user_names = []
        for c in self.get_user_names():
            user_names.append(c)
        if resp in user_names:
            print("username already exists")
            s.send(bytes([0]))
            s.close()
            return
        else:
            s.send(bytes([len(user_names)]))
            for u in user_names:
                s.send(bytes(u, "utf-8"))
                ack = s.recv(1)
                if int.from_bytes(ack, byteorder="little") != 1:
                    print("error sending user list. aborting connection")
                    s.close()
                    return
        msg = "<" + resp + " has connected>"
        print(msg, "from {}".format(addy[0]))
        self.socket_list.append(s)
        self.client_dict[s] = {"username": resp}
        self.total_clients = len(self.client_dict)
        self.update_status_line("{} client(s) connected".format(self.total_clients))
        self.update_chat_history(msg)
        self.update_send(1, resp)
        self.refresh_user_list()

    def remove_connection(self, conn):
        msg = "<" + self.client_dict[conn]["username"] + " has disconnected>"
        print(msg)
        self.update_chat_history(msg)
        self.socket_list.remove(conn)
        self.update_send(2, self.client_dict[conn]["username"])
        del self.client_dict[conn]
        conn.close()
        self.total_clients = len(self.client_dict)
        self.update_status_line("{} client(s) connected".format(self.total_clients))
        self.refresh_user_list()

    def msg_receive(self, conn):
        msg = conn.recv(1024)
        if len(msg) == 0:
            self.remove_connection(conn)
        else:
            msg_string = self.client_dict[conn]["username"] + ": " + msg.decode("utf-8", "<could not decode>")
            self.update_chat_history(msg_string)
            for c in self.socket_list:
                if c != self.connection_socket:
                    c.send(bytes([3]))
                    c.send(bytes(msg_string, "utf-8"))

    def msg_send(self, event=None):
        msg = event.widget.get()
        event.widget.delete(0, tk.END)
        if len(msg) > 0:
            msg_string = self.username + ": " + msg
            self.update_chat_history(msg_string)
            for c in self.socket_list:
                if c != self.connection_socket:
                    c.send(bytes(msg_string, "utf-8"))

    def update_chat_history(self, msg):
        self.chat_widgets[0].configure(state="normal")
        self.chat_widgets[0].insert(tk.END, msg + "\n")
        self.chat_widgets[0].see(tk.END)
        self.chat_widgets[0].configure(state="disabled")

    def update_send(self, msg_type, msg_data):
        """
        For sending data other than client messages, such as joins and leaves
        """
        for c in self.socket_list:
            if c != self.connection_socket:
                c.send(bytes([msg_type]))
                c.send(bytes(msg_data, "utf-8"))

    def create_chat_screen(self):
        chat_history_w = 30
        chat_history_h = 30
        chat_history = scrolledtext.ScrolledText(self.upper_frame, width=chat_history_w, height=chat_history_h,
                                                 font=("modern", 12), wrap=tk.WORD, state="disabled")
        chat_history.place(relx=0.02, rely=0.02, relwidth=0.96, relheight=0.95)
        chat_history.bind("<1>", lambda event: chat_history.focus_set())
        self.chat_widgets.append(chat_history)

        text_entry = tk.Entry(self.lower_frame, width=40, font=("modern", 12))
        text_entry.place(anchor="center", relx=0.5, rely=0.48, relwidth=0.97, relheight=0.5)
        text_entry.focus_set()
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

    def get_user_names(self):
        user_names = [self.username]
        for u in self.client_dict.values():
            user_names.append(u["username"])
        return sorted(user_names)

    def refresh_user_list(self):
        for u in self.user_list_labels:
            u.destroy()
        user_list_labels = []
        y_pos = 0.05
        y_inc = 0.05
        for user in self.get_user_names():
            label = tk.Label(self.chat_widgets[2], text=user, bg="#FFFFFF", anchor="w")
            if user == self.username:
                label.configure(font=("modern", 12, "bold"))
            else:
                label.configure(font=("modern", 12))
            label.place(relx=0.1, rely=y_pos, relwidth=0.8)
            user_list_labels.append(label)
            y_pos += y_inc
        self.user_list_labels = user_list_labels

    def update_status_line(self, text, anchor="e", rel_x=0.95, rely=0.83):
        if self.status_line is None:
            self.status_line = tk.Label(self, text=text)
        else:
            self.status_line.configure(text=text)
        self.status_line.place(anchor=anchor, relx=rel_x, rely=rely)
        self.update_idletasks()

    def start_app(self):
        server_thread = Thread(target=self.server_listen_thread, daemon=True)
        server_thread.start()
        self.create_chat_screen()
        self.mainloop()

    def stop_app(self):
        print("closing server app")
        for conn in self.socket_list:
            conn.close()
        sys.exit()


if __name__ == "__main__":
    first_window = AppWindow(800, 650)
    try:
        first_window.start_app()
    except KeyboardInterrupt:
        pass
    finally:
        print("server app closed")
