/**
 * Agribank KTNB To-Do App — Frontend Logic
 * Xử lý gọi API, Render danh sách, Lọc trạng thái, CRUD công việc & Xử lý trường hợp biên (Edge cases)
 */

let allTasks = [];
let currentFilter = 'all';

// Khởi chạy khi tài liệu tải xong
document.addEventListener('DOMContentLoaded', () => {
    fetchTasks();
    setupEventListeners();
});

// ==========================================
// 1. GỌI API & LẤY DỮ LIỆU
// ==========================================

async function fetchTasks() {
    try {
        const response = await fetch('/api/tasks');
        const result = await response.json();
        
        if (result.success) {
            allTasks = result.data || [];
            updateStats(result.total || 0, result.count_dang_lam || 0, result.count_xong || 0);
            renderTasks();
        } else {
            showToast(result.message || 'Lỗi khi tải danh sách', 'error');
        }
    } catch (error) {
        console.error('Lỗi API:', error);
        showToast('Không thể kết nối tới máy chủ', 'error');
    }
}

// Cập nhật các con số thống kê
function updateStats(total, pending, completed) {
    document.getElementById('stat-total').innerText = total;
    document.getElementById('stat-pending').innerText = pending;
    document.getElementById('stat-completed').innerText = completed;

    document.getElementById('count-all').innerText = total;
    document.getElementById('count-dang-lam').innerText = pending;
    document.getElementById('count-xong').innerText = completed;
}

// ==========================================
// 2. RENDER GIAO DIỆN & LỌC DỮ LIỆU
// ==========================================

function renderTasks() {
    const container = document.getElementById('task-list-container');
    const searchInput = document.getElementById('search-input');
    const searchQuery = (searchInput ? searchInput.value : '').trim().toLowerCase();

    // 1. Lọc theo tab trạng thái
    let filtered = allTasks;
    if (currentFilter !== 'all') {
        filtered = filtered.filter(t => t.trang_thai === currentFilter);
    }

    // 2. Lọc theo từ khóa tìm kiếm
    if (searchQuery) {
        filtered = filtered.filter(t => 
            (t.ten && t.ten.toLowerCase().includes(searchQuery)) || 
            (t.nguoi_phu_trach && t.nguoi_phu_trach.toLowerCase().includes(searchQuery))
        );
    }

    // TRƯỜNG HỢP BIÊN 1: Xử lý danh sách rỗng
    if (allTasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📭</div>
                <p><strong>Danh sách hiện đang trống.</strong></p>
                <p style="font-size: 13px; margin-top: 4px;">Hãy thêm công việc đầu tiên ở form bên trái!</p>
            </div>
        `;
        return;
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🔍</div>
                <p><strong>Không tìm thấy công việc nào phù hợp.</strong></p>
                <p style="font-size: 13px; margin-top: 4px;">Thử thay đổi bộ lọc trạng thái hoặc từ khóa tìm kiếm.</p>
            </div>
        `;
        return;
    }

    // Render danh sách công việc
    container.innerHTML = filtered.map(task => {
        const isDone = task.trang_thai === 'xong';
        const statusLabel = isDone ? 'Đã xong' : 'Đang làm';
        const statusClass = isDone ? 'xong' : 'dang_lam';

        return `
            <div class="task-item ${isDone ? 'is-done' : ''}" id="task-${task.id}">
                <div class="task-left">
                    <input 
                        type="checkbox" 
                        class="task-checkbox" 
                        ${isDone ? 'checked' : ''} 
                        onchange="toggleTask(${task.id})"
                        title="Đánh dấu hoàn thành / chưa hoàn thành"
                    >
                    <div class="task-details">
                        <span class="task-title">${escapeHtml(task.ten)}</span>
                        <div class="task-meta">
                            <span class="assignee-badge">👤 ${escapeHtml(task.nguoi_phu_trach)}</span>
                            <span class="status-badge ${statusClass}">[${statusLabel}]</span>
                        </div>
                    </div>
                </div>
                <div class="task-actions">
                    <button class="action-btn edit-btn" onclick="openEditModal(${task.id})" title="Chỉnh sửa">
                        ✏️ Sửa
                    </button>
                    <button class="action-btn delete-btn" onclick="deleteTask(${task.id})" title="Xóa">
                        🗑️ Xóa
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Chuyển đổi bộ lọc trạng thái
function filterBy(filter) {
    currentFilter = filter;
    
    // Cập nhật active tab UI
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === filter);
    });

    renderTasks();
}

// ==========================================
// 3. THÊM / SỬA / XÓA / ĐỔI TRẠNG THÁI
// ==========================================

function setupEventListeners() {
    // Form Thêm Công Việc
    const addForm = document.getElementById('add-task-form');
    if (addForm) {
        addForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // TRƯỜNG HỢP BIÊN 2: Nhập chuỗi trống hoặc toàn khoảng trắng
            const ten = document.getElementById('task-name').value.trim();
            const nguoi_phu_trach = document.getElementById('task-assignee').value.trim();

            if (!ten || !nguoi_phu_trach) {
                showToast('Tên công việc và người phụ trách không được để trống!', 'error');
                return;
            }

            try {
                const response = await fetch('/api/tasks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ten, nguoi_phu_trach })
                });
                const result = await response.json();

                if (result.success) {
                    showToast(result.message, 'success');
                    addForm.reset();
                    fetchTasks(); // Tải lại danh sách
                } else {
                    showToast(result.message || 'Không thể thêm công việc', 'error');
                }
            } catch (error) {
                showToast('Lỗi kết nối máy chủ', 'error');
            }
        });
    }

    // Form Sửa Công Việc trong Modal
    const editForm = document.getElementById('edit-task-form');
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const id = parseInt(document.getElementById('edit-task-id').value, 10);
            const ten = document.getElementById('edit-task-name').value.trim();
            const nguoi_phu_trach = document.getElementById('edit-task-assignee').value.trim();
            const trang_thai = document.getElementById('edit-task-status').value;

            if (!id || isNaN(id)) {
                showToast('Mã công việc không hợp lệ!', 'error');
                return;
            }

            if (!ten || !nguoi_phu_trach) {
                showToast('Tên công việc và người phụ trách không được để trống!', 'error');
                return;
            }

            try {
                const response = await fetch(`/api/tasks/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ten, nguoi_phu_trach, trang_thai })
                });
                const result = await response.json();

                if (result.success) {
                    showToast(result.message, 'success');
                    closeEditModal();
                    fetchTasks();
                } else {
                    showToast(result.message || 'Không thể cập nhật công việc', 'error');
                }
            } catch (error) {
                showToast('Lỗi khi cập nhật công việc', 'error');
            }
        });
    }

    // Đóng Modal khi bấm phím ESC hoặc click bên ngoài
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeEditModal();
        }
    });

    const modalOverlay = document.getElementById('edit-modal');
    if (modalOverlay) {
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                closeEditModal();
            }
        });
    }
}

// Đổi trạng thái Hoàn thành / Chưa hoàn thành
async function toggleTask(id) {
    try {
        const response = await fetch(`/api/tasks/${id}/toggle`, { method: 'PATCH' });
        const result = await response.json();
        
        if (result.success) {
            showToast(result.message, 'success');
            fetchTasks();
        } else {
            showToast(result.message || 'Không tìm thấy công việc', 'error');
            fetchTasks();
        }
    } catch (error) {
        showToast('Không thể thay đổi trạng thái', 'error');
    }
}

// TRƯỜNG HỢP BIÊN 3: Xóa công việc không tồn tại hoặc có xác nhận an toàn
async function deleteTask(id) {
    const task = allTasks.find(t => t.id === id);
    if (!task) {
        showToast('Không tìm thấy công việc cần xóa!', 'error');
        fetchTasks();
        return;
    }

    const taskName = task.ten ? `"${task.ten}"` : `mã #${id}`;

    if (!confirm(`Bạn có chắc chắn muốn xóa công việc ${taskName}?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
        const result = await response.json();

        if (result.success) {
            showToast(result.message, 'success');
            fetchTasks();
        } else {
            showToast(result.message || 'Lỗi khi xóa công việc', 'error');
            fetchTasks();
        }
    } catch (error) {
        showToast('Lỗi kết nối khi xóa công việc', 'error');
    }
}

// ==========================================
// 4. MODAL & TIỆN ÍCH
// ==========================================

// TRƯỜNG HỢP BIÊN 4: Mở modal cho công việc không tồn tại
function openEditModal(id) {
    const task = allTasks.find(t => t.id === id);
    if (!task) {
        showToast('Không tìm thấy dữ liệu công việc để chỉnh sửa!', 'error');
        fetchTasks();
        return;
    }

    document.getElementById('edit-task-id').value = task.id;
    document.getElementById('edit-task-name').value = task.ten || '';
    document.getElementById('edit-task-assignee').value = task.nguoi_phu_trach || '';
    document.getElementById('edit-task-status').value = task.trang_thai || 'dang_lam';

    document.getElementById('edit-modal').classList.add('active');
}

function closeEditModal() {
    const modal = document.getElementById('edit-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// Hiển thị thông báo Toast
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.innerText = message;
    toast.className = `toast show ${type}`;

    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

// Escape HTML để bảo vệ chống XSS
function escapeHtml(text) {
    if (typeof text !== 'string') return text;
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}
