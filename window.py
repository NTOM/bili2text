import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import webbrowser
import re
import sys
import os
import threading
from tkinter import filedialog
from utils import download_video, check_ffmpeg, cleanup_temp_files, PathConfig
from exAudio import convert_flv_to_mp3, split_mp3, process_audio_split

speech_to_text = None  # 模型实例
ffmpeg_available = False  # ffmpeg 是否可用

def is_cuda_available(whisper):
    return whisper.torch.cuda.is_available()

def open_popup(text, title="提示"):

    popup = ttk.Toplevel()
    popup.title(title)
    popup.geometry("300x150")
    popup.update_idletasks()
    x = (popup.winfo_screenwidth() - popup.winfo_reqwidth()) // 2
    y = (popup.winfo_screenheight() - popup.winfo_reqheight()) // 2
    popup.geometry("+%d+%d" % (x, y))
    label = ttk.Label(popup, text=text)
    label.pack(pady=10)
    user_choice = ttk.StringVar()

    def on_confirm():
        user_choice.set("confirmed")
        popup.destroy()
    confirm_button = ttk.Button(popup, text="确定", style="primary.TButton", command=on_confirm)
    confirm_button.pack(side=LEFT, padx=10, pady=10)

    def on_cancel():
        user_choice.set("cancelled")
        popup.destroy()
    cancel_button = ttk.Button(popup, text="取消", style="outline-danger.TButton", command=on_cancel)
    cancel_button.pack(side=RIGHT, padx=10, pady=10)
    popup.wait_window()
    return user_choice.get()

def show_log(text, state="INFO"):

    log_text.config(state="normal")
    log_text.insert(END, f"[LOG][{state}] {text}\n")
    log_text.config(state="disabled")

def on_submit_click():
    global speech_to_text, ffmpeg_available
    if not ffmpeg_available:
        print("错误：ffmpeg 未安装，无法处理视频！")
        return
    if speech_to_text is None:
        print("Whisper未加载！请点击加载Whisper按钮。")
        return
    video_link = video_link_entry.get()
    if not video_link:
        print("视频链接不能为空！")
        return
    if open_popup("是否确定生成？可能耗费时间较长", title="提示") == "cancelled":
        return
    # 提取BV号
    pattern = r'BV[A-Za-z0-9]+'
    matches = re.findall(pattern, video_link)
    if not matches:
        print("无效的视频链接！")
        return
    bv_number = matches[0]
    print(f"视频链接: {video_link}, BV号: {bv_number}")
    thread = threading.Thread(target=process_video, args=(bv_number[2:],))
    thread.start()

def process_video(av_number):
    try:
        print("=" * 10)
        print("正在下载视频...")
        file_identifier = download_video(str(av_number))
        print("=" * 10)
        print("正在分割音频...")
        # 使用音频模块处理
        folder_name = process_audio_split(file_identifier)
        print("=" * 10)
        print("正在转换文本（可能耗时较长）...")
        output_path = speech_to_text.run_analysis(folder_name, 
            prompt="以下是普通话的句子。这是一个关于{}的视频。".format(file_identifier))
        print(f"转换完成！输出文件: {output_path}")
    finally:
        # 清理临时文件
        print("=" * 10)
        print("正在清理临时文件...")
        cleanup_temp_files()
        print("处理完成！")

def on_generate_again_click():
    print("再次生成...")
    print(open_popup("是否再次生成？"))

def on_clear_log_click():
    # 临时恢复原始 stdout/stderr，避免清空期间的输出被重定向回 log_text
    try:
        sys.stdout = _orig_stdout
        sys.stderr = _orig_stderr
    except NameError:
        # 如果还没初始化原始对象，跳过
        pass
    try:
        log_text.config(state="normal")
        log_text.delete('1.0', END)
        log_text.config(state="disabled")
    finally:
        # 重新启用重定向（如果之前启用了）
        try:
            redirect_system_io()
        except Exception:
            # 避免在清空日志时抛出异常导致界面卡住
            pass

def on_show_result_click():
    print("这里是结果...")

def on_select_model():
    selected_model = model_var.get()
    print(f"选中的模型: {selected_model}")
    print("请点击加载Whisper按钮加载模型！")

def on_confirm_model_click():
    selected_model = model_var.get()
    print(f"确认的模型: {selected_model}")
    print("请点击加载Whisper按钮加载模型！")

def load_whisper_model():
    global speech_to_text
    import speech2text
    speech_to_text = speech2text
    speech_to_text.load_whisper(model=model_var.get())
    msg = "CUDA加速已启用" if is_cuda_available(speech_to_text.whisper) else "使用CPU计算"
    print("加载Whisper成功！", msg)

def open_github_link(event=None):
    webbrowser.open_new("https://github.com/lanbinshijie/bili2text")

def select_video_dir():
    """选择视频下载目录"""
    path = filedialog.askdirectory(title="选择视频下载目录")
    if path:
        PathConfig.set_video_dir(path)
        video_dir_var.set(path)
        print(f"视频下载目录已设置为: {path}")

def select_output_dir():
    """选择TXT导出目录"""
    path = filedialog.askdirectory(title="选择TXT导出目录")
    if path:
        PathConfig.set_output_dir(path)
        output_dir_var.set(path)
        print(f"TXT导出目录已设置为: {path}")

def check_ffmpeg_status():
    """检查 ffmpeg 状态并显示结果"""
    global ffmpeg_available
    available, message = check_ffmpeg()
    ffmpeg_available = available
    if available:
        ffmpeg_status_label.config(text="✓ ffmpeg 已就绪", foreground="green")
    else:
        ffmpeg_status_label.config(text="✗ ffmpeg 未安装", foreground="red")
        print(message)

def redirect_system_io():
    global _orig_stdout, _orig_stderr
    # 仅在首次调用时保存原始 stdout/stderr
    if '_orig_stdout' not in globals():
        _orig_stdout = sys.stdout
        _orig_stderr = sys.stderr

    class StdoutRedirector:
        def __init__(self):
            self._buffer = ""
        def write(self, message, state="INFO"):
            if not message:
                return
            # 跳过进度信息
            if "Speed" in message:
                return
            self._buffer += message
            # 只在遇到换行时写入完整行，避免把片段拆成多行日志
            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                if line.strip():
                    try:
                        log_text.config(state="normal")
                        log_text.insert(END, f"[LOG][{state}] {line}\n")
                        log_text.config(state="disabled")
                        log_text.see(END)
                    except Exception:
                        # 如果 UI 还没准备好，回退写到原始 stdout，避免丢失日志或递归
                        try:
                            _orig_stdout.write(line + "\n")
                        except Exception:
                            pass
        def flush(self):
            if self._buffer.strip():
                try:
                    log_text.config(state="normal")
                    log_text.insert(END, f"[LOG][INFO] {self._buffer}\n")
                    log_text.config(state="disabled")
                    log_text.see(END)
                except Exception:
                    try:
                        _orig_stdout.write(self._buffer + "\n")
                    except Exception:
                        pass
            self._buffer = ""

    # 安装重定向器
    sys.stdout = StdoutRedirector()
    sys.stderr = StdoutRedirector()

def main():
    global video_link_entry, log_text, model_var, video_dir_var, output_dir_var, ffmpeg_status_label
    app = ttk.Window("Bili2Text - By Lanbin | www.lanbin.top", themename="litera")
    app.geometry("820x620")
    app.iconbitmap("favicon.ico")
    ttk.Label(app, text="Bilibili To Text", font=("Helvetica", 16)).pack(pady=10)
    
    # 路径配置区域
    path_frame = ttk.LabelFrame(app, text="路径配置", padding=10)
    path_frame.pack(fill=X, padx=20, pady=5)
    
    # 视频下载目录
    video_dir_row = ttk.Frame(path_frame)
    video_dir_row.pack(fill=X, pady=2)
    ttk.Label(video_dir_row, text="视频下载目录:", width=12).pack(side=LEFT)
    video_dir_var = ttk.StringVar(value=PathConfig.video_dir)
    video_dir_entry = ttk.Entry(video_dir_row, textvariable=video_dir_var, state="readonly")
    video_dir_entry.pack(side=LEFT, expand=YES, fill=X, padx=5)
    ttk.Button(video_dir_row, text="浏览", command=select_video_dir, bootstyle="outline").pack(side=RIGHT)
    
    # TXT导出目录
    output_dir_row = ttk.Frame(path_frame)
    output_dir_row.pack(fill=X, pady=2)
    ttk.Label(output_dir_row, text="TXT导出目录:", width=12).pack(side=LEFT)
    output_dir_var = ttk.StringVar(value=PathConfig.output_dir)
    output_dir_entry = ttk.Entry(output_dir_row, textvariable=output_dir_var, state="readonly")
    output_dir_entry.pack(side=LEFT, expand=YES, fill=X, padx=5)
    ttk.Button(output_dir_row, text="浏览", command=select_output_dir, bootstyle="outline").pack(side=RIGHT)
    
    # ffmpeg 状态
    ffmpeg_row = ttk.Frame(path_frame)
    ffmpeg_row.pack(fill=X, pady=2)
    ttk.Label(ffmpeg_row, text="ffmpeg状态:", width=12).pack(side=LEFT)
    ffmpeg_status_label = ttk.Label(ffmpeg_row, text="检测中...", foreground="gray")
    ffmpeg_status_label.pack(side=LEFT, padx=5)
    ttk.Button(ffmpeg_row, text="重新检测", command=check_ffmpeg_status, bootstyle="outline").pack(side=RIGHT)
    
    video_link_frame = ttk.Frame(app)
    video_link_entry = ttk.Entry(video_link_frame)
    video_link_entry.pack(side=LEFT, expand=YES, fill=X)
    load_whisper_button = ttk.Button(video_link_frame, text="加载Whisper", command=load_whisper_model, bootstyle="success-outline")
    load_whisper_button.pack(side=RIGHT, padx=5)
    submit_button = ttk.Button(video_link_frame, text="下载视频", command=on_submit_click)
    submit_button.pack(side=RIGHT, padx=5)
    video_link_frame.pack(fill=X, padx=20, pady=5)
    
    log_text = ttk.ScrolledText(app, height=10, state="disabled")
    log_text.pack(padx=20, pady=10, fill=BOTH, expand=YES)
    
    controls_frame = ttk.Frame(app)
    controls_frame.pack(fill=X, padx=20)
    generate_button = ttk.Button(controls_frame, text="再次生成", command=on_generate_again_click)
    generate_button.pack(side=LEFT, padx=10, pady=10)
    show_result_button = ttk.Button(controls_frame, text="展示结果", command=on_show_result_click, bootstyle="success-outline")
    show_result_button.pack(side=LEFT, padx=10, pady=10)
    
    model_var = ttk.StringVar(value="medium")
    model_combobox = ttk.Combobox(controls_frame, textvariable=model_var, values=["tiny", "small", "medium", "large"])
    model_combobox.pack(side=LEFT, padx=10, pady=10)
    model_combobox.set("small")
    
    confirm_model_button = ttk.Button(controls_frame, text="确认模型", command=on_confirm_model_click, bootstyle="primary-outline")
    confirm_model_button.pack(side=LEFT, padx=10, pady=10)
    
    clear_log_button = ttk.Button(controls_frame, text="清空日志", command=on_clear_log_click, bootstyle=DANGER)
    clear_log_button.pack(side=LEFT, padx=10, pady=10)
    
    footer_frame = ttk.Frame(app)
    footer_frame.pack(side=BOTTOM, fill=X)
    author_label = ttk.Label(footer_frame, text="作者：Lanbin")
    author_label.pack(side=LEFT, padx=10, pady=10)
    version_var = ttk.StringVar(value="2.0.0")
    version_label = ttk.Label(footer_frame, text="版本 " + version_var.get(), foreground="gray")
    version_label.pack(side=LEFT, padx=10, pady=10)
    github_link = ttk.Label(footer_frame, text="开源仓库", cursor="hand2", bootstyle=PRIMARY)
    github_link.pack(side=LEFT, padx=10, pady=10)
    github_link.bind("<Button-1>", open_github_link)
    
    redirect_system_io()
    
    # 启动时检测 ffmpeg
    app.after(100, check_ffmpeg_status)
    
    app.mainloop()

if __name__ == "__main__":
    main()
