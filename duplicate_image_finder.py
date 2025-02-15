import hashlib
import logging
import os
import subprocess
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Generator, List

# Constants
HASH_ALGORITHM = hashlib.sha256
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
LOG_LEVEL = logging.INFO

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(ch)


def file_generator(target_dir: Path) -> Generator[Path, None, None]:
    return (
        Path(root) / file
        for root, _, files in os.walk(target_dir)
        for file in files
        if (Path(root) / file).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    )


def find_duplicates(target_dir: Path) -> List[List[Path]]:
    """
    Finds duplicate image files in the specified directory.

    Args:
        target_dir: The directory to search.

    Returns:
        A list of lists, where each inner list contains paths to duplicate files.
    """
    if not target_dir.is_dir():
        raise ValueError("指定されたパスはディレクトリではありません")

    hash_dict: Dict[str, List[Path]] = {}
    duplicates: List[List[Path]] = []

    for file_path in file_generator(target_dir):
        try:
            logger.info(f"処理中: {file_path}")
            hasher = HASH_ALGORITHM()
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            file_hash = hasher.hexdigest()

            if file_hash in hash_dict:
                hash_dict[file_hash].append(file_path)
            else:
                hash_dict[file_hash] = [file_path]

        except OSError as e:
            logger.error(f"ファイル処理エラー: {file_path} - {e}")
            continue

    for file_list in hash_dict.values():
        if len(file_list) > 1:
            duplicates.append(file_list)

    return duplicates


class DuplicateFinderGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("画像重複検出ツール")

        self.target_dir_label = ttk.Label(root, text="対象ディレクトリ:")
        self.target_dir_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.target_dir_entry = ttk.Entry(root, width=50)
        self.target_dir_entry.grid(row=0, column=1, padx=5, pady=5)
        self.browse_button = ttk.Button(root, text="参照...", command=self.browse_directory)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5)
        self.run_button = ttk.Button(root, text="重複検出実行", command=self.run_duplicate_detection)
        self.run_button.grid(row=1, column=1, pady=10)
        self.status_label = ttk.Label(root, text="", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=2, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.target_dir_entry.delete(0, tk.END)
            self.target_dir_entry.insert(0, directory)

    def run_duplicate_detection(self):
        target_dir_str = self.target_dir_entry.get()
        if not target_dir_str:
            messagebox.showwarning("警告", "対象ディレクトリを指定してください。")
            return

        target_dir = Path(target_dir_str)
        if not target_dir.is_dir():
            messagebox.showerror("エラー", "指定されたパスはディレクトリではありません。")
            return

        self.status_label.config(text="処理中...", foreground="blue")
        self.root.update_idletasks()

        try:
            start_time = time.time()
            duplicates = find_duplicates(target_dir)
            end_time = time.time()
            elapsed_time = end_time - start_time

            if not duplicates:
                message = "重複ファイルはありませんでした。"
                self.status_label.config(text="完了 (重複なし)", foreground="green")
                messagebox.showinfo("完了", message)
                logger.info(message)
            else:
                message = f"処理完了。{len(duplicates)} 組の重複ファイルが見つかりました。\n処理時間: {elapsed_time:.2f}秒"
                self.status_label.config(text="完了", foreground="green")
                messagebox.showinfo("完了", message)
                send_mac_notification("画像重複検出完了", message)
                logger.info(message)
                for duplicate_group in duplicates:
                    logger.info("重複:")
                    for file_path in duplicate_group:
                        logger.info(f"  - {file_path}")

        except Exception as e:
            logger.exception(f"エラー: {e}")
            self.status_label.config(text="エラー", foreground="red")
            messagebox.showerror("エラー", str(e))


def send_mac_notification(title: str, message: str):
    script = f'display notification "{message}" with title "{title}"'
    subprocess.run(["osascript", "-e", script])


def main():
    root = tk.Tk()
    gui = DuplicateFinderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
