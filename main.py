import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
from edit_case_page import EditCasePage
from database_config import DatabaseManager, UserManager, CaseManager

class ToolTip:
    """工具提示类"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
    
    def on_enter(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, background="#ffffe0",
                        relief="solid", borderwidth=1, font=("Arial", 9))
        label.pack()
    
    def on_leave(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class GradientButton(tk.Canvas):
    """渐变按钮类"""
    def __init__(self, parent, text, command=None, width=120, height=35, 
                 start_color="#4a90e2", end_color="#357abd", text_color="white", **kwargs):
        super().__init__(parent, width=width, height=height, highlightthickness=0, **kwargs)
        
        self.text = text
        self.command = command
        self.width = width
        self.height = height
        self.start_color = start_color
        self.end_color = end_color
        self.text_color = text_color
        
        self.draw_gradient()
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
    
    def hex_to_rgb(self, hex_color):
        """将十六进制颜色转换为RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def rgb_to_hex(self, rgb):
        """将RGB颜色转换为十六进制"""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    def interpolate_color(self, start_rgb, end_rgb, factor):
        """颜色插值"""
        return tuple(int(start_rgb[i] + (end_rgb[i] - start_rgb[i]) * factor) for i in range(3))
    
    def draw_gradient(self, hover=False):
        """绘制渐变背景"""
        self.delete("all")
        
        start_rgb = self.hex_to_rgb(self.start_color)
        end_rgb = self.hex_to_rgb(self.end_color)
        
        if hover:
            # 悬停时稍微调亮
            start_rgb = tuple(min(255, c + 20) for c in start_rgb)
            end_rgb = tuple(min(255, c + 20) for c in end_rgb)
        
        # 绘制渐变
        for i in range(self.height):
            factor = i / self.height
            color_rgb = self.interpolate_color(start_rgb, end_rgb, factor)
            color_hex = self.rgb_to_hex(color_rgb)
            self.create_line(0, i, self.width, i, fill=color_hex)
        
        # 绘制圆角效果（简化版）
        self.create_rectangle(0, 0, self.width, self.height, outline="#2c5aa0", width=1)
        
        # 绘制文本
        self.create_text(self.width//2, self.height//2, text=self.text, 
                        fill=self.text_color, font=("Arial", 10, "bold"))
    
    def on_click(self, event):
        if self.command:
            self.command()
    
    def on_enter(self, event):
        self.draw_gradient(hover=True)
        self.config(cursor="hand2")
    
    def on_leave(self, event):
        self.draw_gradient(hover=False)
        self.config(cursor="")

class LawyerAssistantApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("律师助手 - 卷宗管理系统")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # 设置应用图标（如果有的话）
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # 初始化数据库
        self.db_manager = DatabaseManager()
        if not self.db_manager.connect():
            messagebox.showerror("错误", "无法连接到数据库！请检查数据库配置。")
            self.root.destroy()
            return
        
        self.user_manager = UserManager(self.db_manager)
        self.case_manager = CaseManager(self.db_manager)
        
        # 当前用户信息
        self.current_user = None
        self.current_session_token = None
        
        # 设置样式
        self.setup_styles()
        
        # 显示登录界面
        self.show_login()
    
    def setup_styles(self):
        """设置应用样式"""
        style = ttk.Style()
        
        # 设置主题
        style.theme_use('clam')
        
        # 自定义样式
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='#2c5aa0')
        style.configure('Heading.TLabel', font=('Arial', 12, 'bold'), foreground='#333333')
        style.configure('Info.TLabel', font=('Arial', 10), foreground='#666666')
        
        # 按钮样式
        style.configure('Action.TButton', font=('Arial', 10, 'bold'))
        
        # 树形控件样式
        style.configure('Treeview', font=('Arial', 9))
        style.configure('Treeview.Heading', font=('Arial', 10, 'bold'))
    
    def show_login(self):
        """显示登录界面"""
        # 清空主窗口
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 创建登录框架
        login_frame = tk.Frame(self.root, bg='#f0f0f0')
        login_frame.pack(fill='both', expand=True)
        
        # 居中容器
        center_frame = tk.Frame(login_frame, bg='white', relief='raised', bd=2)
        center_frame.place(relx=0.5, rely=0.5, anchor='center', width=400, height=300)
        
        # 标题
        title_label = tk.Label(center_frame, text="律师助手登录", 
                              font=('Arial', 18, 'bold'), fg='#2c5aa0', bg='white')
        title_label.pack(pady=30)
        
        # 用户名
        tk.Label(center_frame, text="用户名:", font=('Arial', 12), bg='white').pack(pady=5)
        self.username_entry = tk.Entry(center_frame, font=('Arial', 12), width=25)
        self.username_entry.pack(pady=5)
        
        # 密码
        tk.Label(center_frame, text="密码:", font=('Arial', 12), bg='white').pack(pady=5)
        self.password_entry = tk.Entry(center_frame, font=('Arial', 12), width=25, show='*')
        self.password_entry.pack(pady=5)
        
        # 登录按钮
        login_btn = GradientButton(center_frame, "登录", command=self.login, width=150, height=40)
        login_btn.pack(pady=20)
        
        # 绑定回车键
        self.root.bind('<Return>', lambda e: self.login())
        
        # 设置焦点
        self.username_entry.focus()
        
        # 测试用户名密码（开发阶段）
        self.username_entry.insert(0, "admin")
        self.password_entry.insert(0, "admin123")
    
    def login(self):
        """用户登录"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("错误", "请输入用户名和密码！")
            return
        
        # 验证用户
        user = self.user_manager.authenticate_user(username, password)
        if user:
            self.current_user = user
            # 创建会话
            self.current_session_token = self.user_manager.create_session(user['id'])
            print(f"用户登录成功: {user['username']} ({user['full_name']})")
            self.show_main_interface()
        else:
            messagebox.showerror("错误", "用户名或密码错误！")
    
    def show_main_interface(self):
        """显示主界面"""
        # 清空窗口
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 解绑回车键
        self.root.unbind('<Return>')
        
        # 创建主布局
        self.create_main_layout()
        
        # 加载用户数据
        self.load_user_cases()
    
    def create_main_layout(self):
        """创建主界面布局"""
        # 顶部工具栏
        toolbar = tk.Frame(self.root, bg='#2c5aa0', height=50)
        toolbar.pack(fill='x')
        toolbar.pack_propagate(False)
        
        # 标题
        title_label = tk.Label(toolbar, text="律师助手 - 卷宗管理系统", 
                              font=('Arial', 14, 'bold'), fg='white', bg='#2c5aa0')
        title_label.pack(side='left', padx=20, pady=10)
        
        # 用户信息
        user_info = f"欢迎，{self.current_user['full_name']} ({self.current_user['role']})"
        user_label = tk.Label(toolbar, text=user_info, 
                             font=('Arial', 10), fg='white', bg='#2c5aa0')
        user_label.pack(side='right', padx=20, pady=15)
        
        # 登出按钮
        logout_btn = tk.Button(toolbar, text="登出", command=self.logout,
                              font=('Arial', 9), bg='#d9534f', fg='white', 
                              relief='flat', padx=15)
        logout_btn.pack(side='right', padx=10, pady=10)
        
        # 主内容区域
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 左侧导航面板
        self.create_navigation_panel(main_frame)
        
        # 右侧内容面板
        self.create_content_panel(main_frame)
    
    def create_navigation_panel(self, parent):
        """创建左侧导航面板"""
        nav_frame = tk.Frame(parent, bg='#f8f9fa', relief='raised', bd=1)
        nav_frame.pack(side='left', fill='y', padx=(0, 10))
        nav_frame.config(width=250)
        nav_frame.pack_propagate(False)
        
        # 导航标题
        nav_title = tk.Label(nav_frame, text="卷宗管理", 
                            font=('Arial', 14, 'bold'), fg='#2c5aa0', bg='#f8f9fa')
        nav_title.pack(pady=15)
        
        # 新建卷宗按钮
        new_case_btn = GradientButton(nav_frame, "新建卷宗", 
                                     command=self.new_case, width=200, height=40)
        new_case_btn.pack(pady=10)
        
        # 卷宗列表标题
        list_title = tk.Label(nav_frame, text="我的卷宗", 
                             font=('Arial', 12, 'bold'), fg='#333', bg='#f8f9fa')
        list_title.pack(pady=(20, 10))
        
        # 卷宗列表框架
        list_frame = tk.Frame(nav_frame, bg='#f8f9fa')
        list_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        # 卷宗列表
        self.case_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                      font=('Arial', 10), selectmode='single')
        self.case_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.case_listbox.yview)
        
        # 绑定双击事件
        self.case_listbox.bind('<Double-Button-1>', self.open_case)
        
        # 右键菜单
        self.create_context_menu()
    
    def create_content_panel(self, parent):
        """创建右侧内容面板"""
        self.content_frame = tk.Frame(parent, bg='white', relief='raised', bd=1)
        self.content_frame.pack(side='right', fill='both', expand=True)
        
        # 默认显示欢迎信息
        self.show_welcome_content()
    
    def show_welcome_content(self):
        """显示欢迎内容"""
        # 清空内容面板
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        welcome_frame = tk.Frame(self.content_frame, bg='white')
        welcome_frame.pack(fill='both', expand=True)
        
        # 欢迎标题
        welcome_title = tk.Label(welcome_frame, text="欢迎使用律师助手", 
                                font=('Arial', 24, 'bold'), fg='#2c5aa0', bg='white')
        welcome_title.pack(pady=50)
        
        # 功能介绍
        features = [
            "📁 卷宗管理 - 创建、编辑和管理法律卷宗",
            "📄 PDF查看 - 在线预览PDF文档",
            "📋 目录提取 - 自动识别PDF目录结构",
            "🔍 智能搜索 - 快速定位相关内容",
            "💬 AI对话 - 智能法律咨询助手"
        ]
        
        for feature in features:
            feature_label = tk.Label(welcome_frame, text=feature, 
                                   font=('Arial', 12), fg='#666', bg='white')
            feature_label.pack(pady=8)
        
        # 操作提示
        tip_label = tk.Label(welcome_frame, 
                           text="请从左侧选择一个卷宗开始工作，或点击'新建卷宗'创建新的卷宗。", 
                           font=('Arial', 11), fg='#999', bg='white')
        tip_label.pack(pady=30)
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="打开卷宗", command=self.open_case)
        self.context_menu.add_command(label="编辑卷宗", command=self.edit_case)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="删除卷宗", command=self.delete_case)
        
        # 绑定右键事件
        self.case_listbox.bind('<Button-3>', self.show_context_menu)
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 选中右键点击的项目
        index = self.case_listbox.nearest(event.y)
        self.case_listbox.selection_clear(0, tk.END)
        self.case_listbox.selection_set(index)
        
        # 显示菜单
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def load_user_cases(self):
        """加载用户卷宗列表"""
        cases = self.case_manager.get_user_cases(self.current_user['id'])
        
        # 清空列表
        self.case_listbox.delete(0, tk.END)
        
        # 存储卷宗数据
        self.cases_data = {}
        
        print(f"查询到 {len(cases)} 个卷宗")
        
        for case in cases:
            # 显示格式：卷宗名称 (案件编号)
            display_text = f"{case['case_name']} ({case['case_number']})"
            self.case_listbox.insert(tk.END, display_text)
            
            # 存储完整数据
            self.cases_data[display_text] = case
            print(f"创建卷宗行: {display_text}")
    
    def new_case(self):
        """新建卷宗"""
        # 打开编辑卷宗页面（新建模式）
        edit_page = EditCasePage(self.root, self.db_manager, self.current_user)
        
        # 等待窗口关闭
        self.root.wait_window(edit_page.window)
        
        # 刷新卷宗列表
        self.load_user_cases()
    
    def open_case(self, event=None):
        """打开卷宗"""
        selection = self.case_listbox.curselection()
        if not selection:
            return
        
        case_text = self.case_listbox.get(selection[0])
        case_data = self.cases_data.get(case_text)
        
        if case_data:
            # 打开编辑卷宗页面（查看/编辑模式）
            edit_page = EditCasePage(self.root, self.db_manager, self.current_user, case_data)
            
            # 等待窗口关闭
            self.root.wait_window(edit_page.window)
            
            # 刷新卷宗列表
            self.load_user_cases()
    
    def edit_case(self):
        """编辑卷宗"""
        self.open_case()  # 编辑和打开使用同一个界面
    
    def delete_case(self):
        """删除卷宗"""
        selection = self.case_listbox.curselection()
        if not selection:
            return
        
        case_text = self.case_listbox.get(selection[0])
        case_data = self.cases_data.get(case_text)
        
        if case_data:
            # 确认删除
            result = messagebox.askyesno("确认删除", 
                                       f"确定要删除卷宗 '{case_data['case_name']}' 吗？\n\n此操作不可恢复！")
            if result:
                # 执行删除
                if self.case_manager.delete_case(case_data['id'], self.current_user['id']):
                    messagebox.showinfo("成功", "卷宗已删除！")
                    self.load_user_cases()  # 刷新列表
                else:
                    messagebox.showerror("错误", "删除卷宗失败！")
    
    def logout(self):
        """用户登出"""
        # 清除会话
        if self.current_session_token:
            self.user_manager.logout_user(self.current_session_token)
        
        self.current_user = None
        self.current_session_token = None
        
        # 返回登录界面
        self.show_login()
    
    def run(self):
        """运行应用"""
        try:
            self.root.mainloop()
        finally:
            # 清理资源
            if hasattr(self, 'db_manager'):
                self.db_manager.disconnect()

def main():
    """主函数"""
    app = LawyerAssistantApp()
    app.run()

if __name__ == "__main__":
    main()