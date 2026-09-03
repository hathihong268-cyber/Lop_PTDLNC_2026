FROM python:3.10-slim

# Thiết lập UTF-8 encoding và PYTHONUNBUFFERED=1
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Sao chép và cài đặt các thư viện phụ thuộc
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn ứng dụng vào container
COPY . .

# Expose port 8501 cho Streamlit App
EXPOSE 8501

# Lệnh mặc định chạy Streamlit Web App
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
