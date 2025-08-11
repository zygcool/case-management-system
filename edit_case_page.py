#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编辑卷宗页面
复制自添加卷宗页面的功能，用于编辑现有卷宗
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
from datetime import datetime
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import io
from database_config import DatabaseManager, CaseManager, DirectoryManager
from database_config_enhanced import EnhancedCaseManager, PDFFileManager, EnhancedDirectoryManager

class ToolTip:
    """创建工具提示框"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind('<Enter>', self.on_enter)
        self.widget.bind('<Leave>', self.on_leave)
        
    def on_enter(self, event=None):
        """鼠标进入时显示提示框"""
        if self.tooltip_window or not self.text:
            return
        try:
            x, y, cx, cy = self.widget.bbox("insert")
        except:
            # 对于按钮等控件，使用控件的位置
            x, y = 0, 0
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify='left',
                        background='#ffffe0', relief='solid', borderwidth=1,
                        font=('Microsoft YaHei', 9))
        label.pack(ipadx=1)
        
    def on_leave(self, event=None):
        """鼠标离开时隐藏提示框"""
        tw = self.tooltip_window
        self.tooltip_window = None
        if tw:
            tw.destroy()

class EditCasePage:
    """编辑卷宗页面类"""
    
    def __init__(self, parent, db_manager, current_user, case_data=None):
        self.parent = parent
        self.db_manager = db_manager
        self.current_user = current_user
        self.case_data = case_data
        
        # 初始化管理器
        self.case_manager = CaseManager(db_manager)
        self.directory_manager = DirectoryManager(db_manager)
        
        # PDF缓存字典
        self.pdf_cache = {}
        
        self.current_pdf_file_id = None  # 当前加载的PDF文件ID
        self.is_loading = False  # 加载状态标志
        self.pdf_cache = {}  # PDF预加载缓存
        self.pdf_images = []  # 初始化PDF图像引用列表
        
        # 创建编辑窗口
        self.create_edit_window()
        
        # 如果有卷宗数据，加载它
        if self.case_data:
            self.load_case_data()
        
    def create_edit_window(self):
        """创建编辑窗口"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("编辑卷宗" if self.case_data else "新建卷宗")
        self.window.geometry("1400x900")
        self.window.configure(bg='#f0f8ff')
        
        # 设置窗口关闭协议
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 创建主框架
        self.main_frame = tk.Frame(self.window, bg='#f0f8ff')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建标题栏
        self.create_title_bar()
        
        # 创建内容区域
        self.create_content_area()
        
    def create_title_bar(self):
        """创建标题栏"""
        title_frame = tk.Frame(self.main_frame, bg='#f0f8ff')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 标题
        title_text = "📝 编辑卷宗" if self.case_data else "📝 新建卷宗"
        title_label = tk.Label(title_frame, text=title_text, 
                              font=('Microsoft YaHei', 16, 'bold'),
                              bg='#f0f8ff', fg='#333333')
        title_label.pack(side=tk.LEFT)
        
        # 按钮区域
        btn_frame = tk.Frame(title_frame, bg='#f0f8ff')
        btn_frame.pack(side=tk.RIGHT)
        
        # 保存按钮
        save_btn = tk.Button(btn_frame, text="💾 保存", 
                            command=self.save_case,
                            bg='#28a745', fg='white',
                            font=('Microsoft YaHei', 10),
                            relief=tk.FLAT, bd=0,
                            padx=15, pady=5,
                            cursor='hand2')
        save_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 取消按钮
        cancel_btn = tk.Button(btn_frame, text="❌ 取消", 
                              command=self.on_closing,
                              bg='#dc3545', fg='white',
                              font=('Microsoft YaHei', 10),
                              relief=tk.FLAT, bd=0,
                              padx=15, pady=5,
                              cursor='hand2')
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
    def create_content_area(self):
        """创建内容区域"""
        content_frame = tk.Frame(self.main_frame, bg='#f0f8ff')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # PDF文件添加区域
        self.create_pdf_panel(content_frame)
        
        # 显示区域（上下分割）
        self.create_display_panel(content_frame)
        
        # 聊天对话框
        self.create_chat_panel(content_frame)
        
    def create_pdf_panel(self, parent):
        """创建PDF文件添加区域"""
        pdf_frame = tk.Frame(parent, bg='#ffffff', relief=tk.RAISED, bd=2)
        pdf_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        pdf_frame.config(width=280)
        pdf_frame.pack_propagate(False)
        
        # 卷宗信息输入区域 - 移到最顶部
        case_info_frame = tk.Frame(pdf_frame, bg='#f8f9fa', relief=tk.FLAT, bd=1)
        case_info_frame.pack(fill=tk.X, padx=10, pady=(5, 5))
        
        # 卷宗案号输入
        case_number_frame = tk.Frame(case_info_frame, bg='#f8f9fa')
        case_number_frame.pack(fill=tk.X, padx=10, pady=2)
        
        case_number_label = tk.Label(case_number_frame, text="卷宗案号:",
                                     font=('Microsoft YaHei', 9),
                                     bg='#f8f9fa', fg='#333333', width=8, anchor='w')
        case_number_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.case_number_entry = tk.Entry(case_number_frame,
                                          font=('Microsoft YaHei', 9),
                                          relief=tk.FLAT, bd=1, bg='#ffffff')
        self.case_number_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # 卷宗名称输入
        case_name_frame = tk.Frame(case_info_frame, bg='#f8f9fa')
        case_name_frame.pack(fill=tk.X, padx=10, pady=2)
        
        case_name_label = tk.Label(case_name_frame, text="卷宗名称:",
                                   font=('Microsoft YaHei', 9),
                                   bg='#f8f9fa', fg='#333333', width=8, anchor='w')
        case_name_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.case_name_entry = tk.Entry(case_name_frame,
                                        font=('Microsoft YaHei', 9),
                                        relief=tk.FLAT, bd=1, bg='#ffffff')
        self.case_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # 卷宗描述输入
        case_desc_frame = tk.Frame(case_info_frame, bg='#f8f9fa')
        case_desc_frame.pack(fill=tk.X, padx=10, pady=(2, 8))
        
        case_desc_label = tk.Label(case_desc_frame, text="描述:",
                                   font=('Microsoft YaHei', 9),
                                   bg='#f8f9fa', fg='#333333', width=8, anchor='nw')
        case_desc_label.pack(side=tk.LEFT, padx=(0, 5), pady=(2, 0))
        
        self.case_desc_text = tk.Text(case_desc_frame,
                                      font=('Microsoft YaHei', 9),
                                      relief=tk.FLAT, bd=1, bg='#ffffff',
                                      height=3, wrap=tk.WORD)
        self.case_desc_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # 保存按钮框架
        save_btn_frame = tk.Frame(case_info_frame, bg='#f8f9fa')
        save_btn_frame.pack(fill=tk.X, padx=10, pady=(5, 8))
        
        # 文件夹图标按钮（添加PDF文件）- 使用自定义图标
        try:
            # 加载自定义图标
            from PIL import Image, ImageTk
            img = Image.open("FileImg.png")
            # 按比例缩放，保持原始宽高比
            original_width, original_height = img.size
            max_size = 52
            if original_width > original_height:
                new_width = max_size
                new_height = int((original_height * max_size) / original_width)
            else:
                new_height = max_size
                new_width = int((original_width * max_size) / original_height)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.file_icon = ImageTk.PhotoImage(img)
            
            folder_btn = tk.Button(save_btn_frame, image=self.file_icon,
                                  command=self.upload_files,
                                  relief=tk.FLAT, bd=0,
                                  bg='#f8f9fa', fg='white',
                                  activebackground='#e9ecef',
                                  highlightthickness=0,
                                  cursor='hand2')
        except Exception as e:
            # 如果图标加载失败，使用文本按钮
            folder_btn = tk.Button(save_btn_frame, text="📁",
                                  command=self.upload_files,
                                  font=('Microsoft YaHei', 16),
                                  relief=tk.FLAT, bd=0,
                                  bg='#f8f9fa', fg='#4a90e2',
                                  activebackground='#e9ecef',
                                  cursor='hand2')
        
        folder_btn.pack(side=tk.RIGHT, padx=(10, 0), pady=0)
        
        # 为添加PDF文件按钮添加tooltip提示
        ToolTip(folder_btn, "请添加卷宗PDF文件")
        
        # 保存卷宗信息按钮
        save_case_btn = tk.Button(save_btn_frame, text="💾 保存卷宗信息",
                                  font=('Microsoft YaHei', 9),
                                  bg='#4a90e2', fg='white',
                                  relief=tk.FLAT, bd=0,
                                  padx=15, pady=5,
                                  cursor='hand2',
                                  command=self.save_case_info_to_database)
        save_case_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 上部分：文件列表区域
        upper_list_frame = tk.Frame(pdf_frame, bg='#ffffff')
        upper_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 5))
        
        # 文件列表标题行
        title_frame = tk.Frame(upper_list_frame, bg='#f8f9fa', relief=tk.FLAT, bd=1)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 标题
        list_title = tk.Label(title_frame, text="卷宗PDF文件列表", 
                             font=('Microsoft YaHei', 12, 'bold'),
                             bg='#f8f9fa', fg='#333333', anchor='center')
        list_title.pack(fill=tk.X, pady=3)
        
        # 文件列表容器
        list_container = tk.Frame(upper_list_frame, bg='#ffffff', relief=tk.FLAT, bd=1)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        # 创建滚动条
        list_scrollbar = tk.Scrollbar(list_container, orient=tk.VERTICAL)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 文件列表画布
        self.file_canvas = tk.Canvas(list_container, bg='#ffffff', 
                                    yscrollcommand=list_scrollbar.set,
                                    highlightthickness=0)
        self.file_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        list_scrollbar.config(command=self.file_canvas.yview)
        
        # 文件列表内容框架
        self.file_list_frame = tk.Frame(self.file_canvas, bg='#ffffff')
        self.file_canvas.create_window((0, 0), window=self.file_list_frame, anchor='nw')
        
        # 绑定滚动事件
        def configure_scroll_region(event):
            self.file_canvas.configure(scrollregion=self.file_canvas.bbox('all'))
        
        self.file_list_frame.bind('<Configure>', configure_scroll_region)
        
        # 绑定鼠标滚轮
        def on_mousewheel(event):
            self.file_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.file_canvas.bind('<MouseWheel>', on_mousewheel)
        
        # 下部分：证据类型分类区域
        evidence_frame = tk.Frame(pdf_frame, bg='#ffffff', relief=tk.FLAT, bd=1)
        evidence_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        # 证据类型标题
        evidence_title = tk.Label(evidence_frame, text="证据类型分类",
                                 font=('Microsoft YaHei', 11, 'bold'),
                                 bg='#ffffff', fg='#333333')
        evidence_title.pack(pady=(5, 8))
        
        # 创建证据类型图标网格
        evidence_grid = tk.Frame(evidence_frame, bg='#ffffff')
        evidence_grid.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 2))
        
        # 证据类型列表
        evidence_types = [
            "物证", "书证", "证人证言", "被害人陈述",
            "犯罪嫌疑人", "鉴定意见", "勘验辨认笔录", "视听电子数据"
        ]
        
        # 创建4x2的网格布局
        for i, evidence_type in enumerate(evidence_types):
            row = i // 4
            col = i % 4
            
            # 创建证据类型按钮框架
            evidence_btn_frame = tk.Frame(evidence_grid, bg='#f8f9fa', relief=tk.RAISED, bd=1)
            evidence_btn_frame.grid(row=row, column=col, padx=2, pady=2, sticky='nsew')
            
            # 文件夹图标
            folder_icon = tk.Label(evidence_btn_frame, text="📁",
                                  font=('Microsoft YaHei', 16),
                                  bg='#f8f9fa', fg='#4a90e2')
            folder_icon.pack(pady=(8, 2))
            
            # 证据类型名称
            evidence_name = tk.Label(evidence_btn_frame, text=evidence_type,
                                   font=('Microsoft YaHei', 9),
                                   bg='#f8f9fa', fg='#333333',
                                   wraplength=45,  # 每行最多4个字符
                                   justify='center')  # 居中对齐
            evidence_name.pack(pady=(0, 8), padx=2)
            
            # 绑定点击事件
            def on_evidence_click(event, etype=evidence_type):
                self.on_evidence_type_click(etype)
            
            evidence_btn_frame.bind('<Button-1>', on_evidence_click)
            folder_icon.bind('<Button-1>', on_evidence_click)
            evidence_name.bind('<Button-1>', on_evidence_click)
            
            # 设置鼠标悬停效果
            def on_enter(event, frame=evidence_btn_frame):
                frame.config(bg='#e3f2fd')
                for child in frame.winfo_children():
                    child.config(bg='#e3f2fd')
            
            def on_leave(event, frame=evidence_btn_frame):
                frame.config(bg='#f8f9fa')
                for child in frame.winfo_children():
                    child.config(bg='#f8f9fa')
            
            evidence_btn_frame.bind('<Enter>', on_enter)
            evidence_btn_frame.bind('<Leave>', on_leave)
            folder_icon.bind('<Enter>', on_enter)
            folder_icon.bind('<Leave>', on_leave)
            evidence_name.bind('<Enter>', on_enter)
            evidence_name.bind('<Leave>', on_leave)
        
        # 配置网格权重，使图标均匀分布
        for i in range(4):
            evidence_grid.columnconfigure(i, weight=1)
        for i in range(2):
            evidence_grid.rowconfigure(i, weight=1)
    
    def create_display_panel(self, parent):
        """创建显示区域（上下分割）"""
        display_frame = tk.Frame(parent, bg='#ffffff', relief=tk.RAISED, bd=2)
        display_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        display_frame.config(width=500)  # 设置固定宽度
        display_frame.pack_propagate(False)
        
        # 上部分区域
        upper_frame = tk.Frame(display_frame, bg='#ffffff')
        upper_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))
        
        # 当前文件名显示
        self.current_file_label = tk.Label(upper_frame, text="未选择文件",
                                          font=('Microsoft YaHei', 10),
                                          bg='#ffffff', fg='#666666')
        self.current_file_label.pack(anchor='w', pady=(0, 10))
        
        # 文档显示容器
        doc_container = tk.Frame(upper_frame, bg='#ffffff')
        doc_container.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        doc_scrollbar = tk.Scrollbar(doc_container, orient=tk.VERTICAL)
        doc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 文档显示区域
        self.doc_display = tk.Text(doc_container,
                                  font=('Microsoft YaHei', 10),
                                  bg='#fafafa', fg='#333333',
                                  relief=tk.FLAT, bd=1,
                                  wrap=tk.WORD,
                                  yscrollcommand=doc_scrollbar.set)
        self.doc_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置滚动条
        doc_scrollbar.config(command=self.doc_display.yview)
        
        # 分隔线
        separator = tk.Frame(display_frame, bg='#dee2e6', height=2)
        separator.pack(fill=tk.X, padx=10)
        
        # 下部分区域
        lower_frame = tk.Frame(display_frame, bg='#ffffff')
        lower_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        lower_frame.config(height=250)
        lower_frame.pack_propagate(False)
        
        # 下部分标题栏
        lower_title_frame = tk.Frame(lower_frame, bg='#f8f9fa')
        lower_title_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 目录提示文字
        title_label = tk.Label(lower_title_frame, text="原文目录中可能会存在手写目录而无法识别的情况，可右键下方进行编辑",
                              font=('Microsoft YaHei', 10),
                              bg='#f8f9fa', fg='#666666')
        title_label.pack(expand=True, pady=5)
        
        # 下部分内容容器
        lower_content_container = tk.Frame(lower_frame, bg='#ffffff')
        lower_content_container.pack(fill=tk.BOTH, expand=True)
        
        # 创建可编辑的四列表格
        self.toc_tree = ttk.Treeview(lower_content_container, 
                                    columns=('序号', '名称', '起始页', '结束页'), 
                                    show='headings',
                                    height=12)
        
        # 设置列标题
        self.toc_tree.heading('序号', text='目录序号')
        self.toc_tree.heading('名称', text='文书名称')
        self.toc_tree.heading('起始页', text='起始页')
        self.toc_tree.heading('结束页', text='结束页')
        
        # 设置列宽
        self.toc_tree.column('序号', width=80, anchor='center')
        self.toc_tree.column('名称', width=200, anchor='w')