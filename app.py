# -*- coding: utf-8 -*-
"""
电商订单抓取助手 v1
粘贴电商网址 -> 内置浏览器打开 -> 登录/确认 -> 识别平台 -> 选数量+勾选字段 -> 一键抓取导出 Excel
"""
import os, sys, shutil, subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# 支持 PyInstaller 打包后的资源路径
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)
from browser_worker import BrowserWorker
from adapters import FIELD_LABELS

PROFILE_DIR = os.path.join(BASE_DIR, "profiles", "default")
SOURCE_PROFILE = os.path.join(os.path.dirname(BASE_DIR), "edge_profile")
OUT_DIR = os.path.join(BASE_DIR, "抓取结果")

# 柔和配色
BG = "#F5F6FA"
FG = "#333333"
ACCENT = "#5B8DB8"      # 柔和蓝
ACCENT_DARK = "#2F5B7C" # 深蓝灰
BTN_BG = "#E8EEF5"
BTN_FG = "#2F5B7C"
FIELD_BG = "#FFFFFF"
BORDER = "#D8DEE6"
OK_GREEN = "#3E7C59"


class OrderGrabberApp:
    def __init__(self, root):
        self.root = root
        self.worker = None
        self.adapter_fields = []
        self.field_vars = {}
        self.busy = False
        self._pending_logs = []

        root.title("电商订单抓取助手")
        root.geometry("760x640")
        root.configure(bg=BG)
        root.minsize(680, 560)

        self._first_run_init()
        self._build_ui()
        self._start_browser()

    # ---------- 首次运行：继承已有拼多多登录态 ----------
    def _first_run_init(self):
        if not os.path.isdir(PROFILE_DIR) and os.path.isdir(SOURCE_PROFILE):
            try:
                shutil.copytree(SOURCE_PROFILE, PROFILE_DIR,
                                ignore=shutil.ignore_patterns(
                                    "Cache", "Code Cache", "GPUCache", "GrShaderCache",
                                    "ShaderCache", "DawnCache", "DawnGraphiteCache",
                                    "component_crx_cache", "Crashpad", "BrowserMetrics"))
                self._log("已继承已有登录态（无需重新登录）")
            except Exception as e:
                self._log(f"继承登录态失败（可手动登录）: {e}")
        os.makedirs(OUT_DIR, exist_ok=True)

    # ---------- UI ----------
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("Microsoft YaHei", 10))
        style.configure("TLabelframe", background=BG, bordercolor=BORDER)
        style.configure("TLabelframe.Label", background=BG, foreground=ACCENT_DARK,
                        font=("Microsoft YaHei", 10, "bold"))
        style.configure("TButton", background=BTN_BG, foreground=BTN_FG,
                        font=("Microsoft YaHei", 10), padding=(12, 5))
        style.map("TButton",
                  background=[("active", "#DCE7F2"), ("disabled", "#EFEFEF")],
                  foreground=[("disabled", "#AAAAAA")])
        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                        font=("Microsoft YaHei", 11, "bold"), padding=(16, 7))
        style.map("Accent.TButton", background=[("active", ACCENT_DARK),
                                                ("disabled", "#9FB6CA")])

        # ===== 顶部：网址栏 =====
        top = ttk.Frame(self.root, padding=(12, 10, 12, 4))
        top.pack(fill="x")
        ttk.Label(top, text="电商网址:").pack(side="left")
        self.url_var = tk.StringVar(value="https://mobile.pinduoduo.com/orders.html?type=0")
        self.url_entry = ttk.Entry(top, textvariable=self.url_var, font=("Microsoft YaHei", 10))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(6, 8), ipady=3)
        self.open_btn = ttk.Button(top, text="打开页面", command=self._on_open)
        self.open_btn.pack(side="left")

        # ===== 状态条 =====
        bar = ttk.Frame(self.root, padding=(12, 2, 12, 0))
        bar.pack(fill="x")
        self.status_var = tk.StringVar(value="状态：启动中…")
        self.status_lbl = ttk.Label(bar, textvariable=self.status_var,
                                    foreground=ACCENT_DARK)
        self.status_lbl.pack(side="left")
        self.identify_btn = ttk.Button(bar, text="识别当前页面",
                                       command=self._on_identify)
        self.identify_btn.pack(side="right")

        # ===== 中部：抓取设置 =====
        mid = ttk.Frame(self.root, padding=(12, 8, 12, 4))
        mid.pack(fill="both", expand=True)

        # 左：字段勾选
        left = ttk.Labelframe(mid, text="勾选抓取内容", padding=(10, 6))
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.fields_frame = ttk.Frame(left)
        self.fields_frame.pack(fill="both", expand=True)
        self._build_field_checks(["shop", "name", "spec", "price", "qty", "paid", "status", "img"])

        # 右：数量与操作
        right = ttk.Labelframe(mid, text="抓取设置", padding=(10, 6))
        right.pack(side="left", fill="y", padx=(6, 0))
        ttk.Label(right, text="记录数量:").pack(anchor="w")
        self.count_var = tk.StringVar(value="0")
        self.count_entry = ttk.Entry(right, textvariable=self.count_var, width=12)
        self.count_entry.pack(anchor="w", pady=(2, 2))
        ttk.Label(right, text="0 = 全部记录", foreground="#888888",
                  font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(0, 10))

        self.scrape_btn = ttk.Button(right, text="一键抓取导出",
                                     style="Accent.TButton", command=self._on_scrape)
        self.scrape_btn.pack(anchor="w", pady=(4, 4), fill="x")
        self.open_dir_btn = ttk.Button(right, text="打开结果文件夹",
                                       command=self._on_open_dir)
        self.open_dir_btn.pack(anchor="w", pady=(2, 4), fill="x")

        # ===== 底部：日志 + 进度 =====
        bottom = ttk.Labelframe(self.root, text="运行日志", padding=(10, 4))
        bottom.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.log_text = tk.Text(bottom, height=12, bg=FIELD_BG, fg=FG,
                                font=("Consolas", 9), relief="flat",
                                state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)
        self.progress = ttk.Progressbar(bottom, mode="indeterminate")
        self.progress.pack(fill="x", pady=(6, 2))

        # 刷新启动早期缓存的日志
        for msg in self._pending_logs:
            self._log(msg)
        self._pending_logs = []

    def _build_field_checks(self, fields):
        for w in self.fields_frame.winfo_children():
            w.destroy()
        self.field_vars = {}
        all_fields = ["shop", "name", "spec", "price", "qty", "paid", "status", "img"]
        for i, f in enumerate(all_fields):
            var = tk.BooleanVar(value=(f in fields))
            self.field_vars[f] = var
            cb = tk.Checkbutton(self.fields_frame, text=FIELD_LABELS.get(f, f),
                                variable=var, bg=BG, fg=FG, activebackground=BG,
                                font=("Microsoft YaHei", 10),
                                command=lambda: self._check_selection())
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=6, pady=3)

    def _check_selection(self):
        if not any(v.get() for v in self.field_vars.values()):
            messagebox.showwarning("提示", "请至少勾选一个字段")

    def _on_open_dir(self):
        os.makedirs(OUT_DIR, exist_ok=True)
        if os.name == "nt":
            subprocess.Popen(["explorer.exe", OUT_DIR])

    # ---------- 浏览器控制 ----------
    def _start_browser(self):
        self.worker = BrowserWorker(PROFILE_DIR, log_cb=self._log)
        self.worker.start()
        self.root.after(200, self._poll_results)

    def _poll_results(self):
        if not self.worker:
            return
        try:
            while True:
                res = self.worker.result_q.get_nowait()
                self._handle_result(res)
        except Exception:
            pass
        self.root.after(200, self._poll_results)

    def _handle_result(self, res):
        t = res.get("type")
        if t == "ready":
            self.status_var.set("状态：浏览器已就绪")
        elif t == "page_loaded":
            self.status_var.set(f"状态：已打开 {res.get('title', '')[:40]}")
            self._log(f"页面标题: {res.get('title')}")
        elif t == "identified":
            self.adapter_fields = res.get("fields", [])
            self._build_field_checks(self.adapter_fields)
            self.status_var.set(
                f"状态：{res.get('adapter')} | 探测到约 {res.get('count', 0)} 条记录")
            self._log(f"识别成功: {res.get('adapter')}，约 {res.get('count', 0)} 条记录")
        elif t == "scrape_done":
            self.progress.stop()
            self.busy = False
            self._set_busy(False)
            if res.get("error"):
                self.status_var.set("状态：抓取失败")
                messagebox.showerror("抓取失败", res["error"])
            else:
                n = len(res.get("rows") or [])
                path = res.get("path")
                self.status_var.set(f"状态：抓取完成 {n} 条")
                self._log(f"抓取完成，共 {n} 条记录")
                if path:
                    self._log(f"已导出: {path}")
                    if messagebox.askyesno("完成", f"成功导出 {n} 条记录！\n\n{path}\n\n是否打开文件？"):
                        self._open_file(path)
        elif t == "error":
            self.progress.stop()
            self.busy = False
            self._set_busy(False)
            self.status_var.set("状态：出错")
            messagebox.showerror("错误", res.get("msg", "未知错误"))

    def _open_file(self, path):
        if os.name == "nt":
            subprocess.Popen(["explorer.exe", path])

    def _on_open(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入网址")
            return
        self.status_var.set("状态：正在打开页面…")
        self.worker.open_url(url)

    def _on_identify(self):
        if self.busy:
            return
        self.status_var.set("状态：正在识别…")
        self.worker.identify()

    def _on_scrape(self):
        if self.busy or not self.worker:
            return
        try:
            n = int(self.count_var.get() or 0)
            if n < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "记录数量请输入非负整数（0=全部）")
            return
        fields = [f for f, v in self.field_vars.items() if v.get()]
        if not fields:
            messagebox.showwarning("提示", "请至少勾选一个字段")
            return
        if not self.adapter_fields:
            # 未识别过，先按当前 URL 识别（后台自动）
            self.worker.identify()
        self.busy = True
        self._set_busy(True)
        self.progress.start(12)
        self.status_var.set(f"状态：抓取中（目标 {n if n else '全部'} 条）…")
        self._log(f"开始抓取: 数量={'全部' if n == 0 else n}，字段={fields}")
        self.worker.scrape(max_records=n, fields=fields, out_dir=OUT_DIR)

    def _set_busy(self, busy):
        state = "disabled" if busy else "normal"
        self.scrape_btn.config(state=state)
        self.open_btn.config(state=state)
        self.identify_btn.config(state=state)

    # ---------- 日志 ----------
    def _log(self, msg):
        if not hasattr(self, "log_text") or not self.log_text.winfo_exists():
            self._pending_logs.append(msg)
            print(f"[LOG] {msg}")
            return
        ts = time_str()
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{ts}] {msg}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")


def time_str():
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")


def main():
    root = tk.Tk()
    app = OrderGrabberApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.worker.close_browser() if app.worker else None,
                                               root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
