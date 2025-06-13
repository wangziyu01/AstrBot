import os
import ssl
import shutil
import socket
import time
import aiohttp
import base64
import zipfile
import uuid
from typing import Union

from PIL import Image

def on_error(func, path, exc_info):
    '''
    a callback of the rmtree function.
    '''
    print(f"remove {path} failed.")
    import stat
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise
    
def remove_dir(file_path) -> bool:
    if not os.path.exists(file_path): return True
    try:
        shutil.rmtree(file_path, onerror=on_error)
        return True
    except BaseException:
        return False
    
def port_checker(port: int, host: str = "localhost"):
    sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sk.settimeout(1)
    try:
        sk.connect((host, port))
        sk.close()
        return True
    except Exception:
        sk.close()
        return False
    

def save_temp_img(img: Union[Image.Image, str]) -> str:
    os.makedirs("data/temp", exist_ok=True)
    # 获得文件创建时间，清除超过 12 小时的
    try:
        for f in os.listdir("data/temp"):
            path = os.path.join("data/temp", f)
            if os.path.isfile(path):
                ctime = os.path.getctime(path)
                if time.time() - ctime > 3600*12:
                    os.remove(path)
    except Exception as e:
        print(f"清除临时文件失败: {e}")

    # 获得时间戳
    timestamp = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    p = f"data/temp/{timestamp}.jpg"

    if isinstance(img, Image.Image):
        img.save(p)
    else:
        with open(p, "wb") as f:
            f.write(img)
    return p

async def download_image_by_url(url: str, post: bool = False, post_data: dict = None, path = None) -> str:
    '''
    下载图片, 返回 path
    '''
    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            if post:
                async with session.post(url, json=post_data) as resp:
                    if not path:
                        return save_temp_img(await resp.read())
                    else:
                        with open(path, "wb") as f:
                            f.write(await resp.read())
                        return path
            else:
                async with session.get(url) as resp:
                    if not path:
                        return save_temp_img(await resp.read())
                    else:
                        with open(path, "wb") as f:
                            f.write(await resp.read())
                        return path
    except aiohttp.client.ClientConnectorSSLError:
        # 关闭SSL验证
        ssl_context = ssl.create_default_context()
        ssl_context.set_ciphers('DEFAULT')
        async with aiohttp.ClientSession() as session:
            if post:
                async with session.post(url, json=post_data, ssl=ssl_context) as resp:
                    return save_temp_img(await resp.read())
            else:
                async with session.get(url, ssl=ssl_context) as resp:
                    return save_temp_img(await resp.read())
    except Exception as e:
        raise e
    
async def download_file(url: str, path: str, show_progress: bool = False):
    '''
    从指定 url 下载文件到指定路径 path
    '''
    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(url, timeout=1800) as resp:
                if resp.status != 200:
                    raise Exception(f"下载文件失败: {resp.status}")
                total_size = int(resp.headers.get('content-length', 0))
                downloaded_size = 0
                start_time = time.time()
                if show_progress:
                    print(f"文件大小: {total_size / 1024:.2f} KB | 文件地址: {url}")
                with open(path, 'wb') as f:
                    while True:
                        chunk = await resp.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if show_progress:
                            elapsed_time = time.time() - start_time
                            speed = downloaded_size / 1024 / elapsed_time  # KB/s
                            print(f"\r下载进度: {downloaded_size / total_size:.2%} 速度: {speed:.2f} KB/s", end='')
    except aiohttp.client.ClientConnectorSSLError:
        # 关闭SSL验证
        ssl_context = ssl.create_default_context()
        ssl_context.set_ciphers('DEFAULT')
        async with aiohttp.ClientSession() as session:
            async with session.get(url, ssl=ssl_context, timeout=120) as resp:
                total_size = int(resp.headers.get('content-length', 0))
                downloaded_size = 0
                start_time = time.time()
                if show_progress:
                    print(f"文件大小: {total_size / 1024:.2f} KB | 文件地址: {url}")
                with open(path, 'wb') as f:
                    while True:
                        chunk = await resp.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if show_progress:
                            elapsed_time = time.time() - start_time
                            speed = downloaded_size / 1024 / elapsed_time  # KB/s
                            print(f"\r下载进度: {downloaded_size / total_size:.2%} 速度: {speed:.2f} KB/s", end='')
    if show_progress:
        print()
    
    
def file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        data_bytes = f.read()
        base64_str = base64.b64encode(data_bytes).decode()
    return "base64://" + base64_str

def get_local_ip_addresses():
    ip = ''
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except BaseException:
        pass
    finally:
        s.close()
    return ip

async def get_dashboard_version():
    if os.path.exists("data/dist"):
        if os.path.exists("data/dist/assets/version"):
            with open("data/dist/assets/version", "r") as f:
                v = f.read().strip()
                return v
    return None

async def download_dashboard():
    '''下载管理面板文件'''
    dashboard_release_url = "https://astrbot-registry.soulter.top/download/astrbot-dashboard/latest/dist.zip"
    try:
        await download_file(dashboard_release_url, "data/dashboard.zip", show_progress=True)
    except BaseException as _:
        dashboard_release_url = "https://github.com/Soulter/AstrBot/releases/latest/download/dist.zip"
        await download_file(dashboard_release_url, "data/dashboard.zip", show_progress=True)
    print("解压管理面板文件中...")
    with zipfile.ZipFile("data/dashboard.zip", "r") as z:
        z.extractall("data")