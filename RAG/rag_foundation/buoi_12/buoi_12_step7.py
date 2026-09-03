# -*- coding: utf-8 -*-
"""
BƯỚC 7: Kiểm tra kết nối Neo4j
Module: buoi_12_step7.py

Yêu cầu:
1. Đọc cấu hình từ .env.
2. Không in password.
3. Dùng official neo4j Python driver.
4. Mở driver.
5. Verify connectivity.
6. Chạy query đọc đơn giản để xác nhận database hoạt động.
7. Đóng driver đúng cách.
8. Không import dữ liệu ở bước này.
"""

import os
import sys
import io
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def run_step_7():
    print("=" * 70)
    print("                 BƯỚC 7: KIỂM TRA KẾT NỐI NEO4J                  ")
    print("=" * 70)
    
    # 1. Đọc cấu hình từ .env
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    
    if not os.path.exists(env_path):
        # Thử tìm ở thư mục cha nếu cần
        parent_env = os.path.abspath(os.path.join(base_dir, "..", "..", "..", ".env"))
        if os.path.exists(parent_env):
            load_dotenv(parent_env)
            print(f"[1] Đã tải .env từ: {parent_env}")
        else:
            print(f"LỖI: Không tìm thấy file .env tại {env_path}")
            return False
    else:
        load_dotenv(env_path)
        print(f"[1] Đã tải .env từ: {env_path}")
        
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    
    # Kiểm tra không in password ra màn hình
    print(f"  - NEO4J_URI      : {uri}")
    print(f"  - NEO4J_USERNAME : {username}")
    print(f"  - NEO4J_PASSWORD : {'*' * len(password) if password else '[NOT SET]'}")
    print(f"  - NEO4J_DATABASE : {database}")
    
    if not password:
        print("\nLỖI: NEO4J_PASSWORD chưa được cấu hình trong .env")
        return False
        
    driver = None
    try:
        # 2. Khởi tạo official driver
        print("\n[2] Đang kết nối tới Neo4j database bằng official neo4j Python driver...")
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        # 3. Verify connectivity
        print("[3] Kiểm tra verify_connectivity()...")
        driver.verify_connectivity()
        print("  --> Kết nối mạng và xác thực tài khoản thành công!")
        
        # 4. Chạy truy vấn đọc đơn giản
        print(f"\n[4] Thực thi truy vấn đọc đơn giản trên database '{database}'...")
        with driver.session(database=database) as session:
            result = session.run("RETURN 1 AS ping_val, datetime() AS current_time")
            record = result.single()
            if record:
                ping_val = record["ping_val"]
                current_time = record["current_time"]
                print(f"  --> Query test thành công: ping_val = {ping_val}, server_time = {current_time}")
                
            # Đếm số lượng node hiện tại
            count_res = session.run("MATCH (n) RETURN count(n) AS total_nodes")
            node_cnt = count_res.single()["total_nodes"]
            print(f"  --> Số lượng node hiện tại trong database: {node_cnt}")
            
        print("\n[5] Đang đóng driver đúng cách...")
        driver.close()
        print("  --> Đã đóng driver thành công.")
        
        print("\n" + "=" * 70)
        print("                  KẾT QUẢ ĐÁNH GIÁ BƯỚC 7                 ")
        print("=" * 70)
        print("Neo4j connection : PASS")
        print(f"Database in use  : {database}")
        print("Error details    : None (Kết nối và phản hồi truy vấn hoàn hảo)")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n[LỖI] Kết nối Neo4j thất bại: {e}")
        if driver:
            try:
                driver.close()
            except Exception:
                pass
        print("\n" + "=" * 70)
        print("Neo4j connection : FAIL")
        print(f"Database in use  : {database}")
        print(f"Error details    : {e}")
        print("=" * 70)
        return False

if __name__ == "__main__":
    run_step_7()
