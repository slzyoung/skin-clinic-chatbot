import streamlit as st
import requests
import time

st.set_page_config(
    page_title="ERHA Assistant",
    page_icon="🩺",
    layout="wide"
)

st.title("🩺 ERHA Assistant")
st.caption("Aplikasi sederhana untuk menguji performa dan ketepatan respon endpoint POST `/api/ai/chat`.")

# Sidebar Configuration
st.sidebar.header("⚙️ Config Endpoint")
api_url = st.sidebar.text_input("API URL", value="http://localhost:8000/api/ai/chat")

if st.sidebar.button("🔌 Test Health Backend"):
    try:
        health_url = api_url.rsplit('/api', 1)[0] + "/health"
        res = requests.get(health_url, timeout=5)
        if res.status_code == 200:
            st.sidebar.success(f"Connected: {res.json()}")
        else:
            st.sidebar.error(f"HTTP {res.status_code}")
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

st.sidebar.markdown("---")
doc_type = st.sidebar.selectbox("Filter Document Type", ["All", "Product", "Treatment", "Promotional"])
top_k = st.sidebar.slider("Top K Passages", min_value=1, max_value=15, value=5)
rerank = st.sidebar.checkbox("Gunakan Reranker (Cross-Encoder)", value=False)

if st.sidebar.button("🗑️ Reset Chat"):
    st.session_state.messages = []
    st.session_state.contexts = {}
    st.rerun()

# State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "contexts" not in st.session_state:
    st.session_state.contexts = {}

# Display Messages
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="🩺" if msg["role"] == "assistant" else None):
        st.markdown(msg["content"])
        
        # Display Retrieved Context Citations if available
        if msg["role"] == "assistant" and idx in st.session_state.contexts:
            ctx_data = st.session_state.contexts[idx]
            results = ctx_data.get("results", [])
            with st.expander(f"📚 Rujukan Dokumen RAG ({len(results)} passage)"):
                for c_idx, res in enumerate(results, 1):
                    meta = res.get("metadata", {})
                    src = meta.get("source_file", meta.get("product_name", "Dokumen"))
                    score = res.get("rerank_score", res.get("score", 0.0))
                    sec = meta.get("section", "General")
                    page = meta.get("page", 1)
                    
                    st.markdown(f"**[{c_idx}] {src}** (Page {page} | Section: `{sec}`) — *Score: {score:.4f}*")
                    st.markdown(f"> {res.get('text', '').strip()}")
                    st.markdown("---")

# Quick Example Query Buttons
if not st.session_state.messages:
    st.markdown("##### 💡 Contoh Pertanyaan Pengujian:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📌 Rekomendasi Produk Jerawat"):
            st.session_state.messages.append({"role": "user", "content": "Rekomendasikan produk topikal ERHA untuk pasien jerawat."})
            st.rerun()
    with col2:
        if st.button("💆 Rekomendasi Treatment Pencerah"):
            st.session_state.messages.append({"role": "user", "content": "Apa saja tindakan klinis (treatment) ERHA untuk kulit kusam?"})
            st.rerun()

# Chat Input
user_input = st.chat_input("Tulis pertanyaan untuk chatbot RAG...")

# Process user input if just submitted or preset selected
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.rerun()

# Execute API Request if last message is from user
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_query = st.session_state.messages[-1]["content"]
    
    # Prepare history payload
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
    
    payload = {
        "query": last_query,
        "categories": [],
        "document_type": None if doc_type == "All" else doc_type,
        "top_k": top_k,
        "rerank": rerank,
        "history": history
    }
    
    with st.chat_message("assistant", avatar="🩺"):
        with st.spinner("Menghubungi API RAG Backend..."):
            t_start = time.time()
            try:
                res = requests.post(api_url, json=payload, timeout=180)
                t_elapsed = time.time() - t_start
                
                if res.status_code == 200:
                    data = res.json()
                    ans = data.get("answer", "")
                    ctx = data.get("context", "")
                    results = data.get("results", [])
                    
                    st.markdown(ans)
                    st.caption(f"⏱️ Response Time: {t_elapsed:.2f}s | Passages: {len(results)}")
                    
                    st.session_state.messages.append({"role": "assistant", "content": ans})
                    asst_idx = len(st.session_state.messages) - 1
                    st.session_state.contexts[asst_idx] = {"context": ctx, "results": results}
                    st.rerun()
                else:
                    err_msg = f"HTTP {res.status_code}: {res.text}"
                    st.error(err_msg)
                    st.session_state.messages.append({"role": "assistant", "content": f"⚠️ Error: {err_msg}"})
            except Exception as e:
                err_msg = f"Koneksi Gagal ({api_url}): {e}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": f"⚠️ Connection Error: {err_msg}"})
