# -*- coding: utf-8 -*-
import curses
import os
import json
import locale
import unicodedata


def main(stdscr):
    # 尝试设置区域为中文（简体），UTF-8 编码
    try:
        locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
    except locale.Error:
        # 如果设置失败，使用默认区域设置
        locale.setlocale(locale.LC_ALL, '')

    stdscr.clear()
    curses.curs_set(0)  # 隐藏光标
    directory = 'texts'  # 请替换为实际的 TXT 文件目录路径
    positions_file = os.path.join(directory, '.reading_positions.json')

    # 加载阅读位置
    if os.path.exists(positions_file):
        with open(positions_file, 'r', encoding='utf-8') as f:
            positions = json.load(f)
    else:
        positions = {}

    # 获取 TXT 文件列表
    txt_files = [f for f in os.listdir(directory) if f.endswith('.txt')]
    if not txt_files:
        stdscr.addstr(0, 0, "未找到TXT文件。按任意键退出。")
        stdscr.refresh()
        stdscr.getch()
        return

    selected = 0
    top_file = 0

    while True:
        stdscr.refresh()
        height, width = stdscr.getmaxyx()
        file_win = curses.newwin(height - 1, width, 0, 0)
        status_win = curses.newwin(1, width, height - 1, 0)

        file_win.clear()
        for i in range(top_file, min(top_file + height - 1, len(txt_files))):
            file = txt_files[i]
            try:
                if i == selected:
                    file_win.addstr(i - top_file, 0, file, curses.A_REVERSE)
                else:
                    file_win.addstr(i - top_file, 0, file)
            except curses.error:
                file_win.addstr(i - top_file, 0, "[文件名无法显示]")

        file_win.refresh()
        status_win.addstr(0, 0, "使用上下箭头导航，Enter选择，q退出")
        status_win.refresh()

        #refresh..
        key = stdscr.getch()
        if key == curses.KEY_UP:
            if selected > 0:
                selected -= 1
                if selected < top_file:
                    top_file = selected
        elif key == curses.KEY_DOWN:
            if selected < len(txt_files) - 1:
                selected += 1
                if selected >= top_file + height - 1:
                    top_file = selected - height + 2
        elif key == ord('\n'):
            file_to_read = txt_files[selected]
            read_file(stdscr, os.path.join(directory, file_to_read), positions)
            stdscr.clear()  # 返回文件选择界面时清屏
            stdscr.refresh()
        elif key == ord('q'):
            break
        elif key == curses.KEY_RESIZE:
            stdscr.clear()
            stdscr.refresh()

    # 保存阅读位置
    with open(positions_file, 'w', encoding='utf-8') as f:
        json.dump(positions, f, ensure_ascii=False)


def get_display_width(text):
    """计算字符串的显示宽度，中文字符计为 2 个字符宽度"""
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in ('F', 'W', 'A'):
            width += 2  # 宽字符（中文等）占 2 个位置
        else:
            width += 1
    return width


def process_line(line, width):
    """处理单行文本，过滤不可打印字符并按显示宽度换行"""
    # 过滤控制字符和不可打印字符，替换为 '?'
    filtered_line = ''.join(c if unicodedata.category(c)[0] != 'C' and c.isprintable() else '?' for c in line.rstrip())
    # 按显示宽度换行
    wrapped_lines = []
    current_line = ""
    current_width = 0
    for char in filtered_line:
        char_width = 2 if unicodedata.east_asian_width(char) in ('F', 'W', 'A') else 1
        if current_width + char_width > width - 2:  # 留 2 个字符边距
            wrapped_lines.append(current_line)
            current_line = char
            current_width = char_width
        else:
            current_line += char
            current_width += char_width
    if current_line:
        wrapped_lines.append(current_line)
    if not wrapped_lines:
        wrapped_lines = ['']  # 处理空行
    return wrapped_lines


def read_file(stdscr, file_path, positions):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        stdscr.addstr(0, 0, f"打开文件错误：{e}。按任意键继续。")
        stdscr.refresh()
        stdscr.getch()
        return

    file_name = os.path.basename(file_path)
    height, width = stdscr.getmaxyx()

    # 获取上次阅读位置
    if file_name in positions:
        current_line = positions[file_name]
    else:
        current_line = 0

    def create_display_lines(lines, width):
        display_lines = []
        for line in lines:
            wrapped_lines = process_line(line, width)
            display_lines.extend(wrapped_lines)
        return display_lines

    # 创建初始显示行
    display_lines = create_display_lines(lines, width)
    pad = curses.newpad(max(len(display_lines), height), width)
    for i, line in enumerate(display_lines):
        try:
            pad.addstr(i, 0, line)
        except curses.error:
            pad.addstr(i, 0, "[无法显示的行]")

    status_win = curses.newwin(1, width, height - 1, 0)
    stdscr.clear()
    stdscr.refresh()

    while True:
        max_line = max(0, len(display_lines) - height + 1)
        current_line = min(current_line, max_line)
        # 计算阅读进度
        if max_line > 0:
            progress = int((current_line / max_line) * 100)
        else:
            progress = 100  # 文件短于屏幕高度时，进度为 100%
        # 更新状态栏，添加进度显示
        status_text = f"正在阅读 {file_name} | 进度: {progress}% | 使用上下箭头滚动，q返回"
        try:
            status_win.addstr(0, 0, status_text[:width - 1])  # 防止状态栏溢出
        except curses.error:
            status_win.addstr(0, 0, "状态栏显示错误")

        # 强制刷新屏幕
        stdscr.clear()
        stdscr.refresh()
        pad.refresh(current_line, 0, 0, 0, height - 2, width - 1)
        status_win.refresh()

        key = stdscr.getch()
        if key == curses.KEY_UP:
            current_line = max(0, current_line - 1)
        elif key == curses.KEY_DOWN:
            current_line = min(max_line, current_line + 1)
        elif key == ord('q'):
            positions[file_name] = current_line
            break
        elif key == curses.KEY_RESIZE:
            # 终端大小调整时重新处理文本
            height, width = stdscr.getmaxyx()
            display_lines = create_display_lines(lines, width)
            pad = curses.newpad(max(len(display_lines), height), width)
            for i, line in enumerate(display_lines):
                try:
                    pad.addstr(i, 0, line)
                except curses.error:
                    pad.addstr(i, 0, "[无法显示的行]")
            status_win.resize(1, width)
            status_win.mvwin(height - 1, 0)
            stdscr.clear()
            stdscr.refresh()


if __name__ == '__main__':
    curses.wrapper(main)
