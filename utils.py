import os
import re
import subprocess
import glob
import shutil

# 全局路径配置
class PathConfig:
    video_dir = "bilibili_video"  # 视频下载目录
    output_dir = "outputs"        # TXT导出目录
    temp_audio_dir = "audio"      # 临时音频目录（会被清理）
    
    @classmethod
    def set_video_dir(cls, path):
        cls.video_dir = path
    
    @classmethod
    def set_output_dir(cls, path):
        cls.output_dir = path

def check_ffmpeg():
    """
    检查系统是否安装了 ffmpeg
    返回: (bool, str) - (是否安装, 提示信息)
    """
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if result.returncode == 0:
            return True, "ffmpeg 已安装"
    except FileNotFoundError:
        pass
    
    # ffmpeg 未找到，返回详细的安装指南
    install_guide = """
未检测到 ffmpeg！请按以下步骤安装：

【方法一：使用 winget 安装（推荐）】
1. 以管理员身份打开 PowerShell
2. 运行命令：winget install ffmpeg
3. 重启终端

【方法二：手动安装】
1. 下载：https://github.com/GyanD/codexffmpeg/releases
2. 解压到 C:\\ffmpeg
3. 将 C:\\ffmpeg\\bin 添加到系统 PATH 环境变量
4. 重启终端

【验证安装】
在终端运行：ffmpeg -version
"""
    return False, install_guide

def ensure_folders_exist(output_dir):
    if not os.path.exists(PathConfig.video_dir):
        os.makedirs(PathConfig.video_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.exists(PathConfig.output_dir):
        os.makedirs(PathConfig.output_dir)

def download_video(bv_number):
    """
    使用you-get下载B站视频。
    参数:
        bv_number: 字符串形式的BV号（不含"BV"前缀）或完整BV号
    返回:
        文件路径
    """
    if not bv_number.startswith("BV"):
        bv_number = "BV" + bv_number
    video_url = f"https://www.bilibili.com/video/{bv_number}"
    output_dir = os.path.join(PathConfig.video_dir, bv_number)
    ensure_folders_exist(output_dir)
    print(f"使用you-get下载视频: {video_url}")
    try:
        result = subprocess.run(["you-get", "-l", "-o", output_dir, video_url], capture_output=True, text=True)
        if result.returncode != 0:
            print("下载失败:", result.stderr)
        else:
            print(result.stdout)
            print(f"视频已成功下载到目录: {output_dir}")
            video_files = glob.glob(os.path.join(output_dir, "*.mp4"))
            if video_files:
                # 删除xml文件
                xml_files = glob.glob(os.path.join(output_dir, "*.xml"))
                for xml_file in xml_files:
                    os.remove(xml_file)
            else:
                file_path = ""
    except Exception as e:
        print("发生错误:", str(e))
        file_path = ""
    return bv_number

def cleanup_temp_files():
    """清理临时音频文件，保留视频文件"""
    temp_dir = PathConfig.temp_audio_dir
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            print(f"已清理临时文件目录: {temp_dir}")
        except Exception as e:
            print(f"清理临时文件失败: {e}")
