// 租房管理系统主JavaScript文件

// API基础URL
const API_BASE = window.location.origin;

// 全局状态管理
const AppState = {
    currentUser: null,
    token: localStorage.getItem('access_token'),
    refreshToken: localStorage.getItem('refresh_token'),
};

// HTTP请求封装
const http = {
    // 获取请求头
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        if (AppState.token) {
            headers['Authorization'] = `Bearer ${AppState.token}`;
        }
        return headers;
    },

    // 处理响应
    async handleResponse(response) {
        const data = await response.json();
        if (!response.ok) {
            if (response.status === 401) {
                // Token过期，尝试刷新
                if (AppState.refreshToken) {
                    const refreshed = await this.refreshToken();
                    if (refreshed) {
                        // 重新请求
                        return this.handleResponse(await fetch(response.url, {
                            method: response.method,
                            headers: this.getHeaders(),
                            body: response.bodyUsed ? null : await response.clone().text(),
                        }));
                    }
                }
                // 无法刷新，跳转到登录页
                this.logout();
                throw new Error('登录已过期，请重新登录');
            }
            throw new Error(data.message || '请求失败');
        }
        return data;
    },

    // 刷新Token
    async refreshToken() {
        try {
            const formData = new FormData();
            formData.append('refresh_token', AppState.refreshToken);

            const response = await fetch(`${API_BASE}/api/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${AppState.token}`,
                },
                body: formData,
            });

            if (response.ok) {
                const data = await response.json();
                if (data.data && data.data.access_token) {
                    AppState.token = data.data.access_token;
                    localStorage.setItem('access_token', data.data.access_token);
                    return true;
                }
            }
        } catch (e) {
            console.error('Token刷新失败:', e);
        }
        return false;
    },

    // GET请求
    async get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${API_BASE}${url}?${queryString}` : `${API_BASE}${url}`;

        const response = await fetch(fullUrl, {
            method: 'GET',
            headers: this.getHeaders(),
        });

        return this.handleResponse(response);
    },

    // POST请求
    async post(url, data = {}, isFormData = false) {
        const options = {
            method: 'POST',
            headers: isFormData ? {} : this.getHeaders(),
            body: isFormData ? data : JSON.stringify(data),
        };

        const response = await fetch(`${API_BASE}${url}`, options);
        return this.handleResponse(response);
    },

    // PUT请求
    async put(url, data = {}) {
        const response = await fetch(`${API_BASE}${url}`, {
            method: 'PUT',
            headers: this.getHeaders(),
            body: JSON.stringify(data),
        });

        return this.handleResponse(response);
    },

    // DELETE请求
    async delete(url) {
        const response = await fetch(`${API_BASE}${url}`, {
            method: 'DELETE',
            headers: this.getHeaders(),
        });

        return this.handleResponse(response);
    },

    // 登录
    async login(username, password) {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            body: formData,
        });

        const data = await this.handleResponse(response);

        if (data.access_token) {
            AppState.token = data.access_token;
            AppState.refreshToken = data.refresh_token;
            AppState.currentUser = data.user;
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
        }

        return data;
    },

    // 注册
    async register(userData) {
        return this.post('/api/auth/register', userData);
    },

    // 登出
    logout() {
        AppState.token = null;
        AppState.refreshToken = null;
        AppState.currentUser = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
    },

    // 获取当前用户信息
    async getCurrentUser() {
        if (!AppState.token) return null;

        try {
            const data = await this.get('/api/auth/me');
            AppState.currentUser = data;
            return data;
        } catch (e) {
            console.error('获取用户信息失败:', e);
            return null;
        }
    },
};

// Toast提示
const Toast = {
    container: null,

    init() {
        this.container = document.createElement('div');
        this.container.className = 'toast-container';
        this.container.style.cssText = `
            position: fixed;
            top: 1rem;
            right: 1rem;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        `;
        document.body.appendChild(this.container);
    },

    show(message, type = 'info', duration = 3000) {
        if (!this.container) this.init();

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            animation: slideIn 0.3s ease;
            color: white;
        `;

        const colors = {
            success: '#22c55e',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6',
        };

        toast.style.backgroundColor = colors[type] || colors.info;
        toast.textContent = message;

        this.container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    success(message) { this.show(message, 'success'); },
    error(message) { this.show(message, 'error'); },
    warning(message) { this.show(message, 'warning'); },
    info(message) { this.show(message, 'info'); },
};

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// 表单工具
const FormUtils = {
    // 获取表单数据
    getData(formElement) {
        const formData = new FormData(formElement);
        const data = {};
        for (const [key, value] of formData.entries()) {
            if (value !== '' && value !== null) {
                // 尝试解析JSON
                try {
                    data[key] = JSON.parse(value);
                } catch {
                    data[key] = value;
                }
            }
        }
        return data;
    },

    // 设置表单数据
    setData(formElement, data) {
        for (const [key, value] of Object.entries(data)) {
            const input = formElement.querySelector(`[name="${key}"]`);
            if (input) {
                if (input.type === 'checkbox') {
                    input.checked = !!value;
                } else if (input.type === 'radio') {
                    const radio = formElement.querySelector(`[name="${key}"][value="${value}"]`);
                    if (radio) radio.checked = true;
                } else {
                    input.value = value ?? '';
                }
            }
        }
    },

    // 显示表单错误
    showErrors(formElement, errors) {
        // 清除旧错误
        formElement.querySelectorAll('.form-error').forEach(el => el.remove());

        if (Array.isArray(errors)) {
            errors.forEach(error => {
                const fieldName = error.loc?.[1];
                if (fieldName) {
                    const input = formElement.querySelector(`[name="${fieldName}"]`);
                    if (input) {
                        const errorEl = document.createElement('div');
                        errorEl.className = 'form-error text-danger text-sm mt-1';
                        errorEl.textContent = error.msg || '字段验证失败';
                        input.parentNode.appendChild(errorEl);
                    }
                }
            });
        }
    },
};

// 分页组件
class Pagination {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        this.currentPage = options.currentPage || 1;
        this.pageSize = options.pageSize || 10;
        this.total = options.total || 0;
        this.onPageChange = options.onPageChange || (() => {});
        this.render();
    }

    get totalPages() {
        return Math.ceil(this.total / this.pageSize);
    }

    render() {
        if (this.total <= 0) {
            this.container.innerHTML = '';
            return;
        }

        let html = '<div class="pagination">';

        // 上一页
        const hasPrev = this.currentPage > 1;
        html += `<button class="pagination-btn" ${!hasPrev ? 'disabled' : ''} data-page="${this.currentPage - 1}">上一页</button>`;

        // 页码
        const maxVisible = 5;
        let startPage = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
        let endPage = Math.min(this.totalPages, startPage + maxVisible - 1);

        if (endPage - startPage + 1 < maxVisible) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }

        // 第一页
        if (startPage > 1) {
            html += `<button class="pagination-btn" data-page="1">1</button>`;
            if (startPage > 2) {
                html += '<span class="px-2">...</span>';
            }
        }

        // 可见页码
        for (let i = startPage; i <= endPage; i++) {
            const isActive = i === this.currentPage;
            html += `<button class="pagination-btn ${isActive ? 'active' : ''}" data-page="${i}">${i}</button>`;
        }

        // 最后一页
        if (endPage < this.totalPages) {
            if (endPage < this.totalPages - 1) {
                html += '<span class="px-2">...</span>';
            }
            html += `<button class="pagination-btn" data-page="${this.totalPages}">${this.totalPages}</button>`;
        }

        // 下一页
        const hasNext = this.currentPage < this.totalPages;
        html += `<button class="pagination-btn" ${!hasNext ? 'disabled' : ''} data-page="${this.currentPage + 1}">下一页</button>`;

        html += '</div>';
        this.container.innerHTML = html;

        // 绑定事件
        this.container.querySelectorAll('button[data-page]').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = parseInt(btn.dataset.page);
                if (page !== this.currentPage && !btn.disabled) {
                    this.currentPage = page;
                    this.render();
                    this.onPageChange(page);
                }
            });
        });
    }

    update(options) {
        if (options.currentPage !== undefined) this.currentPage = options.currentPage;
        if (options.pageSize !== undefined) this.pageSize = options.pageSize;
        if (options.total !== undefined) this.total = options.total;
        this.render();
    }
}

// 图片上传预览
class ImageUploader {
    constructor(inputElement, previewContainer, options = {}) {
        this.input = typeof inputElement === 'string' ? document.querySelector(inputElement) : inputElement;
        this.preview = typeof previewContainer === 'string' ? document.querySelector(previewContainer) : previewContainer;
        this.maxFiles = options.maxFiles || 10;
        this.maxSize = options.maxSize || 5 * 1024 * 1024;
        this.files = [];
        this.onChange = options.onChange || (() => {});
        this.init();
    }

    init() {
        this.input.addEventListener('change', (e) => this.handleFileSelect(e));
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);

        if (this.files.length + files.length > this.maxFiles) {
            Toast.error(`最多只能上传${this.maxFiles}张图片`);
            return;
        }

        files.forEach(file => {
            // 验证文件类型
            if (!file.type.startsWith('image/')) {
                Toast.error('只能上传图片文件');
                return;
            }

            // 验证文件大小
            if (file.size > this.maxSize) {
                Toast.error(`图片大小不能超过${this.maxSize / 1024 / 1024}MB`);
                return;
            }

            // 创建预览
            const reader = new FileReader();
            reader.onload = (e) => {
                this.files.push({
                    file,
                    preview: e.target.result,
                    id: Date.now() + Math.random().toString(36).substr(2, 9),
                });
                this.render();
                this.onChange(this.files);
            };
            reader.readAsDataURL(file);
        });

        // 清空input，允许重复选择同一文件
        e.target.value = '';
    }

    render() {
        if (!this.preview) return;

        let html = '';
        this.files.forEach((item, index) => {
            html += `
                <div class="image-preview-item relative">
                    <img src="${item.preview}" 
                         class="image-preview-img" 
                         alt="preview">
                    <button type="button" 
                            class="image-preview-remove absolute"
                            data-index="${index}">
                        ×
                    </button>
                </div>
            `;
        });

        this.preview.innerHTML = html;

        this.preview.querySelectorAll('button[data-index]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const index = parseInt(btn.dataset.index);
                this.files.splice(index, 1);
                this.render();
                this.onChange(this.files);
            });
        });
    }

    getFiles() {
        return this.files.map(item => item.file);
    }

    clear() {
        this.files = [];
        this.render();
        this.onChange(this.files);
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', async () => {
    // 如果有token，尝试获取用户信息
    if (AppState.token) {
        await http.getCurrentUser();
    }

    // 登录表单
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = FormUtils.getData(loginForm);

            try {
                await http.login(data.username, data.password);
                Toast.success('登录成功');
                setTimeout(() => window.location.href = '/', 1000);
            } catch (error) {
                Toast.error(error.message || '登录失败');
            }
        });
    }

    // 注册表单
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = FormUtils.getData(registerForm);

            // 验证密码确认
            if (data.password !== data.confirm_password) {
                Toast.error('两次输入的密码不一致');
                return;
            }

            try {
                await http.register(data);
                Toast.success('注册成功，请登录');
                setTimeout(() => window.location.href = '/login', 1000);
            } catch (error) {
                Toast.error(error.message || '注册失败');
            }
        });
    }

    // 登出按钮
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            http.logout();
        });
    }

    // 显示用户信息
    if (AppState.currentUser) {
        const userInfoEl = document.getElementById('user-info');
        if (userInfoEl) {
            userInfoEl.innerHTML = `
                <span class="text-sm text-secondary">
                    ${AppState.currentUser.nickname || AppState.currentUser.username}
                </span>
                <button id="logout-btn" class="btn btn-sm btn-secondary ml-2">退出</button>
            `;

            // 重新绑定登出事件
            const newLogoutBtn = document.getElementById('logout-btn');
            if (newLogoutBtn) {
                newLogoutBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    http.logout();
                });
            }
        }
    }
});

// 导出供其他脚本使用
window.AppState = AppState;
window.http = http;
window.Toast = Toast;
window.FormUtils = FormUtils;
window.Pagination = Pagination;
window.ImageUploader = ImageUploader;
