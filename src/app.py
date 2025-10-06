import streamlit as st
import sys
import os
import sqlite3
import uuid
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.agent.main_agent import MainAgent
from src.processing.ingest_single_file import process_and_ingest_single_pdf
from src.utils import get_current_hcm_time_iso
from src.config import *

# --- Cấu hình trang và khởi tạo Agent ---
st.set_page_config(page_title="Lumin AI Agent", page_icon="✨", layout="wide")

@st.cache_resource
def load_agent():
    agent = MainAgent()
    return agent

main_agent = load_agent()

@st.cache_data(ttl=30)
def get_user_assets_tree(user_id: str) -> dict:
    if not user_id: return {}
    assets_tree = {}
    try:
        conn = sqlite3.connect(SQL_DATABASE_PATH)
        cursor = conn.cursor()
        ws_query = "SELECT T1.id, T1.name FROM Workspace AS T1 JOIN User_Workspace_Membership AS T2 ON T1.id = T2.workspace_id WHERE T2.user_id = ?"
        cursor.execute(ws_query, (user_id,))
        workspaces = cursor.fetchall()
        if not workspaces: return {}
        for ws_id, ws_name in workspaces: assets_tree[ws_id] = {'name': ws_name, 'spaces': {}}
        ws_ids = list(assets_tree.keys())
        sp_query = f"SELECT T1.id, T1.name, T1.workspace_id FROM Space AS T1 JOIN User_Space_Membership AS T2 ON T1.id = T2.space_id WHERE T2.user_id = ? AND T1.workspace_id IN ({','.join('?' for _ in ws_ids)})"
        cursor.execute(sp_query, [user_id] + ws_ids)
        spaces = cursor.fetchall()
        if not spaces: return assets_tree
        space_map = {}
        for sp_id, sp_name, ws_id in spaces:
            if ws_id in assets_tree:
                assets_tree[ws_id]['spaces'][sp_id] = {'name': sp_name, 'documents': []}
                space_map[sp_id] = ws_id
        sp_ids = list(space_map.keys())
        if not sp_ids: return assets_tree
        doc_query = f"SELECT id, filename, space_id FROM PDF_Document WHERE space_id IN ({','.join('?' for _ in sp_ids)})"
        cursor.execute(doc_query, sp_ids)
        documents = cursor.fetchall()
        for doc_id, doc_name, sp_id in documents:
            if sp_id in space_map:
                ws_id = space_map[sp_id]
                assets_tree[ws_id]['spaces'][sp_id]['documents'].append({'id': doc_id, 'name': doc_name})
        conn.close()
        return assets_tree
    except Exception as e:
        st.error(f"Could not fetch user assets tree: {e}")
        return {}

def get_db_connection(): 
    return sqlite3.connect(SQL_DATABASE_PATH)

def create_workspace(ws_name: str, user_id: str) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    new_ws_id = f"ws_{uuid.uuid4().hex[:10]}"
    current_time = get_current_hcm_time_iso()
    cursor.execute("INSERT INTO Workspace (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                   (new_ws_id, ws_name, current_time, current_time))
    cursor.execute("INSERT INTO User_Workspace_Membership (user_id, workspace_id) VALUES (?, ?)",
                   (user_id, new_ws_id))
    conn.commit()
    conn.close()
    return new_ws_id

def create_space(sp_name: str, workspace_id: str, user_id: str) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    new_sp_id = f"sp_{uuid.uuid4().hex[:10]}"
    current_time = get_current_hcm_time_iso()
    cursor.execute("INSERT INTO Space (id, name, workspace_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                   (new_sp_id, sp_name, workspace_id, current_time, current_time))
    cursor.execute("INSERT INTO User_Space_Membership (user_id, space_id) VALUES (?, ?)",
                   (user_id, new_sp_id))
    conn.commit()
    conn.close()
    return new_sp_id

# --- Quản lý Session State ---
if "messages" not in st.session_state: 
    st.session_state.messages = []
if "current_user" not in st.session_state: 
    st.session_state.current_user = None
if "upload_step" not in st.session_state: 
    st.session_state.upload_step = 1
if "ws_choice" not in st.session_state: 
    st.session_state.ws_choice = "Sử dụng Workspace có sẵn"
if "sp_choice" not in st.session_state: 
    st.session_state.sp_choice = "Sử dụng Space có sẵn"

def reset_upload_flow():
    """Reset toàn bộ upload workflow"""
    st.session_state.upload_step = 1
    st.session_state.ws_choice = "Sử dụng Workspace có sẵn"
    st.session_state.sp_choice = "Sử dụng Space có sẵn"
    
    # Xóa các key của widget và các key "CHOSEN"
    keys_to_delete = [
        "new_ws_name", "selected_ws_id", "new_sp_name", "final_space_id", "uploaded_file",
        "CHOSEN_ws_choice", "CHOSEN_ws_id", "CHOSEN_new_ws_name",
        "CHOSEN_sp_choice", "CHOSEN_space_id", "CHOSEN_new_sp_name"
    ]
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]

# --- Giao diện (UI) ---
st.title("✨ Lumin AI - Agent Demo")

with st.sidebar:
    st.header("👥 User Selection")
    
    def on_user_change():
        """Callback khi user thay đổi - reset upload flow và clear cache"""
        reset_upload_flow()
        st.cache_data.clear()
        # Force clear cache của get_user_assets_tree
        get_user_assets_tree.clear()

    users = {"Alice": "alice_01", "Bob": "bob_02"}
    user_names = list(users.keys())
    current_user_name = next((name for name, uid in users.items() 
                             if uid == st.session_state.current_user), None)
    current_index = user_names.index(current_user_name) if current_user_name else None
    
    selected_user_name = st.selectbox(
        "Chọn người dùng:", 
        options=user_names, 
        index=current_index, 
        placeholder="Select a user...", 
        on_change=on_user_change, 
        key="user_selector"
    )
    st.session_state.current_user = users[selected_user_name] if selected_user_name else None

    if st.session_state.current_user:
        st.success(f"Logged in as **{selected_user_name}**.")
    st.divider()
    
    # File Explorer
    if st.session_state.current_user:
        with st.expander("🗂️ File Explorer", expanded=True):
            # Force refresh assets tree mỗi lần render
            get_user_assets_tree.clear()
            assets_tree = get_user_assets_tree(st.session_state.current_user)
            if assets_tree:
                for ws_id, ws_data in assets_tree.items():
                    with st.expander(f"🗂️ **{ws_data['name']}** `({ws_id})`"):
                        if ws_data['spaces']:
                            for sp_id, sp_data in ws_data['spaces'].items():
                                with st.expander(f"📁 {sp_data['name']} `({sp_id})`"):
                                    if sp_data['documents']:
                                        for doc in sp_data['documents']:
                                            st.markdown(f"📄 {doc['name']}")
                                    else: 
                                        st.caption("*No documents in this space*")
                        else: 
                            st.caption("*No spaces in this workspace*")
            else: 
                st.info("You don't have any assets yet.")
    st.divider()

    # --- UPLOAD WIZARD ---
    if st.session_state.current_user:
        with st.expander("📤 Upload PDF", expanded=False):
            assets_tree = get_user_assets_tree(st.session_state.current_user)

            # BƯỚC 1: Chọn Workspace
            if st.session_state.upload_step == 1:
                st.markdown("##### Bước 1: Chọn Workspace")
                st.radio("Hành động:", 
                        ["Sử dụng Workspace có sẵn", "Tạo Workspace mới"], 
                        key="ws_choice")
                
                if st.session_state.ws_choice == "Sử dụng Workspace có sẵn":
                    ws_options = {ws_id: data['name'] for ws_id, data in assets_tree.items()} if assets_tree else {}
                    if ws_options:
                        st.selectbox("Chọn Workspace:", 
                                   options=list(ws_options.keys()), 
                                   format_func=lambda ws_id: ws_options.get(ws_id, "N/A"), 
                                   key="selected_ws_id")
                    else: 
                        st.info("Bạn chưa có Workspace nào.")
                else:
                    st.text_input("Tên Workspace mới:", key="new_ws_name")
                
                if st.button("Tiếp tục →"):
                    # Lưu lựa chọn của Bước 1
                    st.session_state.CHOSEN_ws_choice = st.session_state.ws_choice
                    if st.session_state.ws_choice == "Sử dụng Workspace có sẵn":
                        st.session_state.CHOSEN_ws_id = st.session_state.get('selected_ws_id')
                    else:
                        st.session_state.CHOSEN_new_ws_name = st.session_state.get('new_ws_name')
                    
                    st.session_state.upload_step = 2
                    st.rerun()

            # BƯỚC 2: Chọn Space
            elif st.session_state.upload_step == 2:
                st.markdown("##### Bước 2: Chọn Space")
                
                # Hiển thị workspace đã chọn
                if st.session_state.CHOSEN_ws_choice == "Tạo Workspace mới":
                    st.info(f"Workspace mới: **{st.session_state.CHOSEN_new_ws_name}**")
                elif st.session_state.get('CHOSEN_ws_id'):
                    ws_name = assets_tree.get(st.session_state.CHOSEN_ws_id, {}).get('name', 'N/A')
                    st.info(f"Đã chọn: **{ws_name}**")
                
                st.radio("Hành động:", 
                        ["Sử dụng Space có sẵn", "Tạo Space mới"], 
                        key="sp_choice")
                
                if st.session_state.sp_choice == "Sử dụng Space có sẵn":
                    if st.session_state.CHOSEN_ws_choice == "Tạo Workspace mới":
                        st.warning("Phải tạo Space mới cho Workspace mới.")
                    else:
                        space_options = assets_tree.get(st.session_state.CHOSEN_ws_id, {}).get('spaces', {})
                        if space_options:
                            st.selectbox("Chọn Space:", 
                                       options=list(space_options.keys()), 
                                       format_func=lambda sp_id: space_options[sp_id]['name'], 
                                       key="final_space_id")
                        else: 
                            st.warning("Workspace này chưa có Space nào.")
                else: 
                    st.text_input("Tên Space mới:", key="new_sp_name")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("← Quay lại"):
                        st.session_state.upload_step = 1
                        st.rerun()
                with col2:
                    if st.button("Tiếp tục → "):
                        # Lưu lựa chọn của Bước 2
                        st.session_state.CHOSEN_sp_choice = st.session_state.sp_choice
                        if st.session_state.sp_choice == "Sử dụng Space có sẵn":
                            st.session_state.CHOSEN_space_id = st.session_state.get('final_space_id')
                        else:
                            st.session_state.CHOSEN_new_sp_name = st.session_state.get('new_sp_name')
                        
                        st.session_state.upload_step = 3
                        st.rerun()
            
            # BƯỚC 3: Upload file
            elif st.session_state.upload_step == 3:
                st.markdown("##### Bước 3: Tải file lên")
                st.file_uploader("Chọn một file PDF", type="pdf", key="uploaded_file")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("← Quay lại "):
                        st.session_state.upload_step = 2
                        st.rerun()
                with col2:
                    if st.button("⚡ Process & Upload"):
                        with st.spinner("Đang xử lý..."):
                            try:
                                uploaded_file = st.session_state.uploaded_file
                                user_id = st.session_state.current_user
                                resolved_ws_id = None
                                resolved_final_space_id = None

                                # Xử lý Workspace
                                if st.session_state.CHOSEN_ws_choice == "Sử dụng Workspace có sẵn":
                                    resolved_ws_id = st.session_state.CHOSEN_ws_id
                                elif st.session_state.CHOSEN_ws_choice == "Tạo Workspace mới":
                                    resolved_ws_id = create_workspace(
                                        st.session_state.CHOSEN_new_ws_name, user_id
                                    )
                                
                                # Xử lý Space
                                if st.session_state.CHOSEN_sp_choice == "Sử dụng Space có sẵn":
                                    resolved_final_space_id = st.session_state.CHOSEN_space_id
                                elif st.session_state.CHOSEN_sp_choice == "Tạo Space mới":
                                    if not resolved_ws_id: 
                                        raise ValueError("Không thể tạo Space mới vì không có Workspace.")
                                    resolved_final_space_id = create_space(
                                        st.session_state.CHOSEN_new_sp_name, 
                                        resolved_ws_id, 
                                        user_id
                                    )

                                if not uploaded_file: 
                                    raise ValueError("Vui lòng chọn file.")
                                if not resolved_final_space_id: 
                                    raise ValueError("Không xác định được Space.")

                                # Lưu và xử lý file
                                save_path = os.path.join(RAW_DATA_PATH, uploaded_file.name)
                                with open(save_path, "wb") as f: 
                                    f.write(uploaded_file.getbuffer())
                                
                                success, message = process_and_ingest_single_pdf(
                                    file_path=save_path, 
                                    space_id=resolved_final_space_id, 
                                    owner_id=user_id
                                )
                                
                                if success:
                                    st.success("Upload thành công!")
                                    # Clear cache để refresh file explorer
                                    st.cache_data.clear()
                                    get_user_assets_tree.clear()
                                    time.sleep(1)
                                    reset_upload_flow()
                                    st.rerun()
                                else: 
                                    st.error(message)
                            except Exception as e:
                                st.error(f"Lỗi: {e}")
            
            # Nút hủy (hiện ở mọi bước trừ bước 1)
            if st.session_state.upload_step > 1:
                if st.button("Hủy và bắt đầu lại"):
                    reset_upload_flow()
                    st.rerun()

# --- Chat UI ---
if not st.session_state.current_user:
    st.warning("Vui lòng chọn một người dùng ở thanh bên để bắt đầu.")
else:
    # Hiển thị lịch sử chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]): 
            st.markdown(message["content"])
    
    # Input chat
    if prompt := st.chat_input("Hỏi AI Agent điều gì?"):
        # Thêm và hiển thị tin nhắn user
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): 
            st.markdown(prompt)
        
        # Xử lý và hiển thị response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            with st.spinner("AI Agent đang suy nghĩ..."):
                try:
                    response = main_agent.run(
                        user_question=prompt, 
                        user_id=st.session_state.current_user
                    )
                except Exception as e: 
                    response = f"Đã xảy ra lỗi: {e}"
            
            response_placeholder.markdown(response)
        
        # Lưu response vào session state
        st.session_state.messages.append({"role": "assistant", "content": response})
        # st.rerun()
st.markdown(
    """
    <div style="
        text-align: center;
        color: gray;
        font-size: 0.9rem;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #e0e0e0;
    ">
        ✨ Developed by <b>Truong Thanh Minh</b> ✨
    </div>
    """,
    unsafe_allow_html=True
)