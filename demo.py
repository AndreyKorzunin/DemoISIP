import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
import hashlib
import random
import os
from PIL import Image, ImageTk

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Замените на вашего пользователя MySQL
    'password': '',  # Укажите пароль от MySQL
    'database': 'dairy_db',
    'autocommit': True
}

# Путь к фрагментам капчи
CAPTCHA_DIR = "assets"
CAPTCHA_FILES = [f"{i}.png" for i in range(1, 5)]



def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def check_user(login, pwd):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE login = %s", (login,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        return None, "not_found"

    if user['is_blocked']:
        return user, "blocked"

    pwd_hash = hash_password(pwd)
    if user['password_hash'] == pwd_hash:
        return user, "success"

    return user, "wrong_pwd"


def increment_attempts(login):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET failed_attempts = failed_attempts + 1 WHERE login = %s", (login,))
    cursor.execute("SELECT failed_attempts FROM users WHERE login = %s", (login,))
    attempts = cursor.fetchone()[0]

    if attempts >= 3:
        cursor.execute("UPDATE users SET is_blocked = 1 WHERE login = %s", (login,))
        blocked = True
    else:
        blocked = False

    cursor.close()
    conn.close()
    return blocked


def reset_attempts(login):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET failed_attempts = 0, is_blocked = 0 WHERE login = %s", (login,))
    cursor.close()
    conn.close()



class CaptchaPuzzle(tk.Toplevel):
    def __init__(self, master, on_success, on_fail):
        super().__init__(master)
        self.title("Капча-пазл")
        self.resizable(False, False)
        self.on_success = on_success
        self.on_fail = on_fail
        self.selected_tile = None
        self.current_order = [0, 1, 2, 3]
        random.shuffle(self.current_order)
        self.correct_order = [0, 1, 2, 3]
        self.tiles = []

        if not self._load_images():
            return

        self._build_grid()
        self.protocol("WM_DELETE_WINDOW", self.on_fail)

    def _load_images(self):
        self.fragments = []
        for fname in CAPTCHA_FILES:
            path = os.path.join(CAPTCHA_DIR, fname)
            if not os.path.exists(path):
                messagebox.showerror("Ошибка капчи", f"Файл не найден: {path}")
                self.on_fail()
                return False
            img = Image.open(path).resize((150, 150))
            self.fragments.append(ImageTk.PhotoImage(img))
        return True

    def _build_grid(self):

        for w in self.winfo_children():
            w.destroy()
        self.tiles = []


        for i in range(2):
            for j in range(2):
                idx = self.current_order[i * 2 + j]
                lbl = tk.Label(self, image=self.fragments[idx], borderwidth=2, relief="solid")
                lbl.image = self.fragments[idx]
                lbl.grid(row=i, column=j, padx=5, pady=5)
                lbl.bind("<Button-1>", lambda e, pos=i * 2 + j: self._on_click(pos))
                self.tiles.append(lbl)


        confirm_btn = tk.Button(
            self,
            text="Подтвердить",
            command=self._check,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            width=20,
            height=2
        )

        confirm_btn.grid(row=2, column=0, columnspan=2, pady=15)

        confirm_btn.bind("<Enter>", lambda e: confirm_btn.config(bg="#45a049"))
        confirm_btn.bind("<Leave>", lambda e: confirm_btn.config(bg="#4CAF50"))

    def _on_click(self, pos):
        if self.selected_tile is None:
            self.selected_tile = pos
            self.tiles[pos].config(relief="sunken")
        else:
            self.current_order[self.selected_tile], self.current_order[pos] = \
                self.current_order[pos], self.current_order[self.selected_tile]
            self.selected_tile = None
            for t in self.tiles:
                t.config(relief="solid")
            self._rebuild()

    def _rebuild(self):
        self._build_grid()

    def _check(self):
        if self.current_order == self.correct_order:
            self.on_success()
        else:
            messagebox.showinfo("Капча", "Пазл собран неверно. Попробуйте ещё раз.")
            self.on_fail()


class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Авторизация")
        self.geometry("340x300")
        self.current_login = None
        self.captcha_verified = False

        tk.Label(self, text="Логин:", font=("Arial", 10)).pack(pady=(20, 0))
        self.login_ent = tk.Entry(self, width=25, font=("Arial", 10))
        self.login_ent.pack(pady=5)

        tk.Label(self, text="Пароль:", font=("Arial", 10)).pack()
        self.pwd_ent = tk.Entry(self, width=25, show="*", font=("Arial", 10))
        self.pwd_ent.pack(pady=5)

        self.captcha_btn = tk.Button(self, text="Пройти капчу", command=self._open_captcha, font=("Arial", 10))
        self.captcha_btn.pack(pady=10)

        tk.Button(self, text="Войти", command=self._login, bg="#4CAF50", fg="white",
                  font=("Arial", 10, "bold"), width=15).pack(pady=10)

    def _open_captcha(self):
        def on_success():
            self.captcha_verified = True
            self.captcha_btn.config(text=" Капча пройдена", state=tk.DISABLED, bg="#E8F5E9")
            cap_win.destroy()

        def on_fail():
            login = self.login_ent.get().strip()
            if login:
                increment_attempts(login)
            cap_win.destroy()

        cap_win = CaptchaPuzzle(self, on_success, on_fail)

    def _login(self):
        login = self.login_ent.get().strip()
        pwd = self.pwd_ent.get().strip()

        if not login or not pwd:
            messagebox.showwarning("Внимание", "Заполните все поля")
            return

        if not self.captcha_verified:
            messagebox.showwarning("Внимание", "Необходимо пройти капчу")
            return

        user, status = check_user(login, pwd)

        if status == "not_found" or status == "wrong_pwd":
            messagebox.showerror("Ошибка",
                                 "Вы ввели неверный логин или пароль. Пожалуйста проверьте ещё раз введенные данные")
            increment_attempts(login)
            self.captcha_verified = False
            self.captcha_btn.config(text=" Пройти капчу", state=tk.NORMAL, bg="#f0f0f0")
            self.pwd_ent.delete(0, tk.END)
        elif status == "blocked":
            messagebox.showerror("Блокировка", "Вы заблокированы. Обратитесь к администратору")
        else:
            messagebox.showinfo("Успех", "Вы успешно авторизовались")
            reset_attempts(login)
            self.destroy()

            if user['role'] == 'Администратор':
                AdminPanel().mainloop()
            else:
                UserDashboard().mainloop()



class AdminPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Панель администратора")
        self.geometry("550x420")
        self._build_ui()

    def _build_ui(self):
        cols = ("id", "login", "role", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=120, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._refresh()

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text=" Добавить", command=self._add_user, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text=" Изменить", command=self._edit_user, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text=" Снять блок", command=self._unblock, width=15).pack(side=tk.LEFT, padx=5)

    def _refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, login, role, is_blocked FROM users")
        for r in cursor.fetchall():
            status = " Заблокирован" if r[3] else " Активен"
            self.tree.insert("", tk.END, values=(r[0], r[1], r[2], status))
        cursor.close()
        conn.close()

    def _add_user(self):
        dialog = tk.Toplevel(self)
        dialog.title("Новый пользователь")
        dialog.geometry("280x220")
        dialog.grab_set()

        tk.Label(dialog, text="Логин:").pack(pady=(10, 0))
        l_ent = tk.Entry(dialog)
        l_ent.pack(pady=5)

        tk.Label(dialog, text="Пароль:").pack()
        p_ent = tk.Entry(dialog, show="*")
        p_ent.pack(pady=5)

        def save():
            l, p = l_ent.get().strip(), p_ent.get().strip()
            if not l or not p:
                return messagebox.showwarning("Ошибка", "Заполните все поля")

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE login = %s", (l,))

            if cursor.fetchone():
                messagebox.showwarning("Ошибка", "Пользователь с таким логином уже существует")
            else:

                pwd_hash = hash_password(p)
                cursor.execute("INSERT INTO users (login, password_hash) VALUES (%s, %s)", (l, pwd_hash))
                conn.commit()
                messagebox.showinfo("Успех", "Пользователь добавлен")
                self._refresh()
                dialog.destroy()

            cursor.close()
            conn.close()

        tk.Button(dialog, text="Сохранить", command=save, bg="#4CAF50", fg="white").pack(pady=10)

    def _edit_user(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showinfo("Инфо", "Выберите пользователя в таблице")

        uid = self.tree.item(sel[0])["values"][0]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT login, role FROM users WHERE user_id=%s", (uid,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        dialog = tk.Toplevel(self)
        dialog.title("Редактирование")
        dialog.geometry("280x180")
        dialog.grab_set()

        tk.Label(dialog, text=f"Логин: {row[0]}").pack(pady=(15, 5))
        tk.Label(dialog, text="Роль:").pack()
        role_cb = ttk.Combobox(dialog, values=["Администратор", "Пользователь"], state="readonly")
        role_cb.set(row[1])
        role_cb.pack(pady=5)

        def save():
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role=%s WHERE user_id=%s", (role_cb.get(), uid))
            conn.commit()
            cursor.close()
            conn.close()

            messagebox.showinfo("Успех", "Данные обновлены")
            self._refresh()
            dialog.destroy()

        tk.Button(dialog, text="Сохранить", command=save).pack(pady=10)

    def _unblock(self):
        sel = self.tree.selection()
        if not sel:
            return

        uid = self.tree.item(sel[0])["values"][0]
        login = self.tree.item(sel[0])["values"][1]
        reset_attempts(login)
        messagebox.showinfo("Успех", "Блокировка снята")
        self._refresh()



class UserDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Рабочий стол пользователя")
        self.geometry("350x150")
        tk.Label(self, text="Добро пожаловать!\nВам доступен только просмотр данных.",
                 font=("Arial", 12), justify=tk.CENTER).pack(pady=40)


if __name__ == "__main__":

    try:
        conn = get_db()
        conn.close()
    except mysql.connector.Error as e:
        messagebox.showerror("Ошибка БД", f"Не удалось подключиться к MySQL:\n{e}")
        exit()

    LoginWindow().mainloop()