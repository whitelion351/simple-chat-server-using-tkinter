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
        self.username = ""

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

    def start_app(self):
        server_thread = Thread(target=self.server_listen_thread, daemon=True)
        server_thread.start()
        self.create_chat_screen()
        self.mainloop()

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

    def remove_connection(self, conn):
        msg = "<" + self.client_dict[conn]["username"] + " has disconnected>"
        print(msg)
        conn.close()
        self.socket_list.remove(conn)
        del self.client_dict[conn]
        self.update_chat_history(msg)
        self.update_send(msg)
        self.total_clients = len(self.client_dict)
        self.update_status_line("{} client(s) connected".format(self.total_clients))

    def accept_connection(self):
        s, addr = self.connection_socket.accept()
        s.send((bytes("what", "utf-8")))
        resp = s.recv(1024)
        msg = "<" + resp.decode() + " has connected>"
        print(msg, "from {}".format(addr[0]))
        self.socket_list.append(s)
        self.client_dict[s] = {"username": resp.decode()}
        self.total_clients = len(self.client_dict)
        self.update_status_line("{} client(s) connected".format(self.total_clients))
        self.update_chat_history(msg)
        self.update_send(msg)

    def msg_receive(self, conn):
        msg = conn.recv(1024)
        if len(msg) == 0:
            self.remove_connection(conn)
        else:
            self.update_chat_history(msg.decode())
            for c in self.socket_list:
                if c != self.connection_socket:
                    c.send(msg)

    def msg_send(self, event=None):
        msg = event.widget.get()
        event.widget.delete(0, tk.END)
        if len(msg) > 0:
            msg = "Server: " + msg
            self.update_chat_history(msg)
            for c in self.socket_list:
                if c != self.connection_socket:
                    c.send(bytes(msg, "utf-8"))

    def update_chat_history(self, msg):
        self.chat_widgets[0].configure(state="normal")
        self.chat_widgets[0].insert(tk.END, msg + "\n")
        self.chat_widgets[0].see(tk.END)
        self.chat_widgets[0].configure(state="disabled")

    def update_send(self, msg):
        for c in self.socket_list:
            if c != self.connection_socket:
                c.send(bytes(msg, "utf-8"))

    def create_chat_screen(self):
        chat_history_w = 30
        chat_history_h = 30
        chat_history = scrolledtext.ScrolledText(self.upper_frame, width=chat_history_w, height=chat_history_h,
                                                 font=("modern", 16), wrap=tk.WORD, state="disabled")
        chat_history.bind("<1>", lambda event: chat_history.focus_set())
        chat_history.place(anchor="center", relx=0.5, rely=0.5, relwidth=0.95, relheight=0.95)
        self.chat_widgets.append(chat_history)

        text_entry = tk.Entry(self.lower_frame, width=40, font=("modern", 20))
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


if __name__ == "__main__":
    first_window = AppWindow(800, 650)
    try:
        first_window.start_app()
    except KeyboardInterrupt:
        pass
    finally:
        print("server app closed")
