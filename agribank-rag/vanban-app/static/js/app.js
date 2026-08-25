/**
 * Agribank KTNB Văn Bản App — Frontend Logic
 * Quản lý danh mục văn bản, tìm kiếm, lọc trạng thái, CRUD & kiểm soát trường hợp biên
 */

let allVanBan = [];
let currentFilter = 'all';
let searchDebounceTimeout = null;

// Khởi chạy khi DOM sẵn sàng
document.addEventListener('DOMContentLoaded', () => {
    fetchVanBan();
    setupEventListeners();
});

// ===================================================
// 1. GỌI API & LẤY DỮ LIỆU
// ===================================================

async function fetchVanBan() {
    try {
        const searchInput = document.getElementById('search-input');
        const searchTerm = (searchInput ? searchInput.value : '').trim();
        
        let url = `/api/vanban?status=${encodeURIComponent(currentFilter)}`;
        if (searchTerm) {
            url += `&search=${encodeURIComponent(searchTerm)}`;
        }

        const response = await fetch(url);
        const result = await response.json();

        if (result.success) {
            allVanBan = result.data || [];
            updateStats(result.total || 0, result.count_con_hieu_luc || 0, result.count_het_hieu_luc || 0);
            renderTable();
        } else {
            showToast(result.message || 'Lỗi khi tải danh mục văn bản', 'error');
        }
    } catch (error) {
        console.error('Lỗi API:', error);
        showToast('Không thể kết nối tới máy chủ', 'error');
    }
}

function updateStats(total, valid, expired) {
    document.getElementById('stat-total').innerText = total;
    document.getElementById('stat-valid').innerText = valid;
    document.getElementById('stat-expired').innerText = expired;

    document.getElementById('count-all').innerText = total;
    document.getElementById('count-valid').innerText = valid;
    document.getElementById('count-expired').innerText = expired;
}

// ===================================================
// 2. RENDER GIAO DIỆN & BẢNG VĂN BẢN
// ===================================================

function renderTable() {
    const tbody = document.getElementById('vb-list-body');
    const emptyState = document.getElementById('empty-state');
    const emptyMsg = document.getElementById('empty-message');
    const searchInput = document.getElementById('search-input');
    const hasSearch = searchInput && searchInput.value.trim().length > 0;

    if (!allVanBan || allVanBan.length === 0) {
        tbody.innerHTML = '';
        emptyState.style.display = 'block';
        if (hasSearch || currentFilter !== 'all') {
            emptyMsg.innerText = 'Không tìm thấy văn bản nào phù hợp với bộ lọc hoặc từ khóa tìm kiếm.';
        } else {
            emptyMsg.innerText = 'Chưa có văn bản nào trong danh mục. Hãy thêm văn bản mới ở biểu mẫu bên trái!';
        }
        return;
    }

    emptyState.style.display = 'none';

    tbody.innerHTML = allVanBan.map(vb => {
        const isValid = vb.con_hieu_luc === true;
        const statusLabel = isValid ? 'Còn hiệu lực' : 'Hết hiệu lực';
        const statusClass = isValid ? 'valid' : 'expired';
        const formattedDate = formatDateDisplay(vb.ngay_ban_hanh);

        return `
            <tr id="row-vb-${vb.id}">
                <td>
                    <span class="vb-so-hieu-badge">${escapeHtml(vb.so_hieu)}</span>
                </td>
                <td class="vb-title-cell">
                    ${escapeHtml(vb.tieu_de)}
                </td>
                <td class="vb-date-cell">
                    📅 ${formattedDate}
                </td>
                <td style="text-align: center;">
                    <span 
                        class="status-badge ${statusClass}" 
                        onclick="toggleStatus(${vb.id})"
                        title="Click để đổi trạng thái hiệu lực"
                    >
                        ● ${statusLabel}
                    </span>
                </td>
                <td>
                    <div class="action-buttons">
                        <button class="action-btn edit-btn" onclick="openEditModal(${vb.id})" title="Chỉnh sửa">
                            ✏️ Sửa
                        </button>
                        <button class="action-btn delete-btn" onclick="deleteVanBan(${vb.id})" title="Xóa">
                            🗑️ Xóa
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function filterBy(filter) {
    currentFilter = filter;
    
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === filter);
    });

    fetchVanBan();
}

function handleSearch() {
    clearTimeout(searchDebounceTimeout);
    searchDebounceTimeout = setTimeout(() => {
        fetchVanBan();
    }, 250);
}

// ===================================================
// 3. THÊM / SỬA / XÓA / ĐỔI TRẠNG THÁI
// ===================================================

function setupEventListeners() {
    // Form Thêm Văn Bản
    const addForm = document.getElementById('add-vb-form');
    if (addForm) {
        addForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const so_hieu = document.getElementById('vb-so-hieu').value.trim();
            const tieu_de = document.getElementById('vb-tieu-de').value.trim();
            const ngay_ban_hanh = document.getElementById('vb-ngay-ban-hanh').value;
            const con_hieu_luc = document.getElementById('vb-con-hieu-luc').checked;

            if (!so_hieu || !tieu_de || !ngay_ban_hanh) {
                showToast('Vui lòng điền đầy đủ số hiệu, tiêu đề và ngày ban hành!', 'error');
                return;
            }

            try {
                const response = await fetch('/api/vanban', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ so_hieu, tieu_de, ngay_ban_hanh, con_hieu_luc })
                });
                const result = await response.json();

                if (result.success) {
                    showToast(result.message, 'success');
                    addForm.reset();
                    document.getElementById('vb-con-hieu-luc').checked = true;
                    fetchVanBan();
                } else {
                    showToast(result.message || 'Không thể thêm văn bản', 'error');
                }
            } catch (error) {
                showToast('Lỗi gửi dữ liệu lên máy chủ', 'error');
            }
        });
    }

    // Form Sửa Văn Bản trong Modal
    const editForm = document.getElementById('edit-vb-form');
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const id = parseInt(document.getElementById('edit-vb-id').value, 10);
            const so_hieu = document.getElementById('edit-vb-so-hieu').value.trim();
            const tieu_de = document.getElementById('edit-vb-tieu-de').value.trim();
            const ngay_ban_hanh = document.getElementById('edit-vb-ngay-ban-hanh').value;
            const con_hieu_luc = document.getElementById('edit-vb-con-hieu-luc').checked;

            if (!id || isNaN(id)) {
                showToast('Mã văn bản không hợp lệ!', 'error');
                return;
            }

            if (!so_hieu || !tieu_de || !ngay_ban_hanh) {
                showToast('Vui lòng điền đầy đủ các trường bắt buộc!', 'error');
                return;
            }

            try {
                const response = await fetch(`/api/vanban/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ so_hieu, tieu_de, ngay_ban_hanh, con_hieu_luc })
                });
                const result = await response.json();

                if (result.success) {
                    showToast(result.message, 'success');
                    closeEditModal();
                    fetchVanBan();
                } else {
                    showToast(result.message || 'Không thể cập nhật văn bản', 'error');
                }
            } catch (error) {
                showToast('Lỗi khi cập nhật văn bản', 'error');
            }
        });
    }

    // Phím ESC đóng modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeEditModal();
        }
    });

    // Click ngoài đóng modal
    const modalOverlay = document.getElementById('edit-modal');
    if (modalOverlay) {
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                closeEditModal();
            }
        });
    }
}

async function toggleStatus(id) {
    try {
        const response = await fetch(`/api/vanban/${id}/toggle-status`, { method: 'PATCH' });
        const result = await response.json();

        if (result.success) {
            showToast(result.message, 'success');
            fetchVanBan();
        } else {
            showToast(result.message || 'Lỗi cập nhật trạng thái', 'error');
        }
    } catch (error) {
        showToast('Không thể thay đổi trạng thái văn bản', 'error');
    }
}

async function deleteVanBan(id) {
    const vb = allVanBan.find(item => item.id === id);
    const vbLabel = vb ? `"${vb.so_hieu}"` : `mã #${id}`;

    if (!confirm(`Bạn có chắc chắn muốn xóa văn bản ${vbLabel} khỏi danh mục?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/vanban/${id}`, { method: 'DELETE' });
        const result = await response.json();

        if (result.success) {
            showToast(result.message, 'success');
            fetchVanBan();
        } else {
            showToast(result.message || 'Lỗi khi xóa văn bản', 'error');
        }
    } catch (error) {
        showToast('Lỗi kết nối khi xóa văn bản', 'error');
    }
}

// ===================================================
// 4. MODAL & TIỆN ÍCH
// ===================================================

function openEditModal(id) {
    const vb = allVanBan.find(item => item.id === id);
    if (!vb) {
        showToast('Không tìm thấy dữ liệu văn bản cần sửa!', 'error');
        return;
    }

    document.getElementById('edit-vb-id').value = vb.id;
    document.getElementById('edit-vb-so-hieu').value = vb.so_hieu || '';
    document.getElementById('edit-vb-tieu-de').value = vb.tieu_de || '';
    document.getElementById('edit-vb-ngay-ban-hanh').value = vb.ngay_ban_hanh || '';
    document.getElementById('edit-vb-con-hieu-luc').checked = vb.con_hieu_luc === true;

    document.getElementById('edit-modal').classList.add('active');
}

function closeEditModal() {
    const modal = document.getElementById('edit-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function formatDateDisplay(dateStr) {
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    return dateStr;
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.innerText = message;
    toast.className = `toast show ${type}`;

    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

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
