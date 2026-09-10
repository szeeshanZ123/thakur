"""
Streamlit Frontend for AI Hackathon Starter.
Connects with FastAPI backend or works standalone with embedded fallback.
"""

import os
import json
import requests
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="AI Hackathon Starter",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI aesthetics
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #3B82F6, #8B5CF6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #6B7280;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    .status-card {
        padding: 0.8rem 1.2rem;
        border-radius: 8px;
        background: #F3F4F6;
        border-left: 4px solid #3B82F6;
        margin-bottom: 1rem;
    }
    .metric-box {
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.title("⚡ AI Hackathon Hub")
backend_url = st.sidebar.text_input("Backend URL", value=os.getenv("BACKEND_URL", "http://localhost:8000"))

# Backend Health Check Helper
def check_backend_health(url: str):
    try:
        resp = requests.get(f"{url}/health", timeout=3)
        if resp.status_code == 200:
            return True, resp.json()
        return False, {"error": f"Status {resp.status_code}"}
    except Exception as e:
        return False, {"error": str(e)}

is_healthy, health_data = check_backend_health(backend_url)

if is_healthy:
    st.sidebar.success("● Backend Connected")
    st.sidebar.caption(f"Provider: **{health_data.get('llm_provider', 'N/A')}** | Model Loaded: **{health_data.get('model_loaded', False)}**")
else:
    st.sidebar.warning("○ Backend Offline / Unreachable")
    st.sidebar.caption("Run `uvicorn backend.main:app --reload` to start the backend.")

st.sidebar.divider()
st.sidebar.markdown("""
### 🛠 Hackathon Workflow
1. **Receive Problem Statement**
2. **Define Schema & Prompt** (`ai/`)
3. **Clean & Train Baseline** (`ml/`)
4. **Expose Endpoints** (`backend/`)
5. **Interactive Demo** (`frontend/`)
""")

# Main Header
st.markdown('<div class="main-title">AI Hackathon Starter Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Rapid prototyping workbench for AI reasoning, ML pipelines, and API integrations.</div>', unsafe_allow_html=True)

# Tabs Navigation
tab_ai, tab_ml_predict, tab_ml_train, tab_docs = st.tabs([
    "🤖 AI Assistant",
    "🎯 ML Inference",
    "📊 Data & Model Training",
    "📖 Quick Reference"
])

# --- TAB 1: AI Assistant ---
with tab_ai:
    st.subheader("AI Problem Solver & Prompt Playground")
    st.write("Test prompts, system instructions, and LLM structured responses.")

    col_input, col_settings = st.columns([3, 1])

    with col_settings:
        st.markdown("**Generation Settings**")
        temp = st.slider("Temperature", 0.0, 1.5, 0.7, step=0.1)
        max_tokens = st.number_input("Max Tokens", min_value=100, max_value=4000, value=800, step=100)
        output_mode = st.selectbox("Expected Output", ["Structured Text / Markdown", "JSON Object"])

    with col_input:
        sys_prompt = st.text_area(
            "System Prompt (Optional)",
            value="You are an intelligent hackathon assistant. Provide structured, accurate answers.",
            height=80
        )
        user_prompt = st.text_area(
            "User Prompt / Problem Input",
            placeholder="Describe your input data or task here...",
            height=140
        )
        btn_generate = st.button("⚡ Generate AI Response", type="primary", use_container_width=True)

    if btn_generate:
        if not user_prompt.strip():
            st.error("Please enter a user prompt before generating.")
        else:
            with st.spinner("Processing request..."):
                try:
                    payload = {
                        "prompt": user_prompt,
                        "system_prompt": sys_prompt,
                        "temperature": temp,
                        "max_tokens": max_tokens
                    }
                    resp = requests.post(f"{backend_url}/api/ai/generate", json=payload, timeout=30)
                    if resp.status_code == 200:
                        result = resp.json()
                        st.success(f"Generated via **{result.get('provider')}** ({result.get('model')})")
                        st.markdown("### AI Output")
                        st.markdown(result.get("content", ""))

                        # If JSON output requested, display parsed format
                        if output_mode == "JSON Object":
                            from ai.utils import extract_json_from_response
                            parsed = extract_json_from_response(result.get("content", ""))
                            if parsed:
                                st.markdown("### Extracted JSON")
                                st.json(parsed)
                    else:
                        st.error(f"Backend Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {str(e)}")

# --- TAB 2: ML Inference ---
with tab_ml_predict:
    st.subheader("Model Inference & Testing")
    st.write("Run real-time predictions against the currently loaded Scikit-Learn model.")

    inference_mode = st.radio("Inference Input Mode", ["Single Record Form", "Batch CSV Upload"], horizontal=True)

    if inference_mode == "Single Record Form":
        st.markdown("**Input Features (JSON Format)**")
        default_json = '{\n  "feature_1": 5.1,\n  "feature_2": 3.5,\n  "category_a": "type_x"\n}'
        raw_feature_text = st.text_area("Record Features", value=default_json, height=120)

        if st.button("🎯 Run Prediction", type="primary"):
            try:
                feature_dict = json.loads(raw_feature_text)
                with st.spinner("Predicting..."):
                    resp = requests.post(f"{backend_url}/api/ml/predict", json={"data": feature_dict}, timeout=10)
                    if resp.status_code == 200:
                        res = resp.json()
                        st.success("Prediction Successful!")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Predicted Output", str(res.get("predictions", ["N/A"])[0]))
                        with col2:
                            if res.get("probabilities"):
                                st.write("**Confidence / Probabilities:**")
                                st.json(res.get("probabilities")[0])
                    else:
                        st.error(f"Prediction Error: {resp.json().get('detail', resp.text)}")
            except json.JSONDecodeError:
                st.error("Invalid JSON format. Please format features as a valid JSON object.")
            except Exception as e:
                st.error(f"Request failed: {str(e)}")

    else:
        uploaded_csv = st.file_uploader("Upload CSV for Batch Prediction", type=["csv"])
        if uploaded_csv is not None:
            df_batch = pd.read_csv(uploaded_csv)
            st.write("Preview of Uploaded Data:", df_batch.head(5))

            if st.button("🎯 Predict Entire Batch", type="primary"):
                with st.spinner("Processing batch predictions..."):
                    try:
                        records = df_batch.to_dict(orient="records")
                        resp = requests.post(f"{backend_url}/api/ml/predict", json={"data": records}, timeout=30)
                        if resp.status_code == 200:
                            res = resp.json()
                            df_batch["Prediction"] = res.get("predictions", [])
                            st.success(f"Generated predictions for {len(df_batch)} rows!")
                            st.dataframe(df_batch)

                            csv_data = df_batch.to_csv(index=False).encode('utf-8')
                            st.download_button("📥 Download Predictions CSV", data=csv_data, file_name="predictions_output.csv", mime="text/csv")
                        else:
                            st.error(f"Batch prediction error: {resp.text}")
                    except Exception as e:
                        st.error(f"Error connecting to backend: {str(e)}")

# --- TAB 3: Data & Training Playground ---
with tab_ml_train:
    st.subheader("Data Explorer & Rapid Baseline Training")
    st.write("Upload a dataset or load demo data to train a Scikit-Learn baseline model on the fly.")

    col_data_source, col_train_config = st.columns([2, 1])

    with col_data_source:
        data_source = st.radio("Dataset Source", ["Generate Synthetic Demo Dataset", "Upload Custom CSV"], horizontal=True)

        if data_source == "Generate Synthetic Demo Dataset":
            import numpy as np
            np.random.seed(42)
            n_samples = 200
            f1 = np.random.normal(10, 2, n_samples)
            f2 = np.random.normal(50, 10, n_samples)
            cat = np.random.choice(["Segment A", "Segment B", "Segment C"], n_samples)
            # Binary target based on features
            target = (f1 * 2 + (f2 > 50) * 5 + np.random.normal(0, 1, n_samples) > 25).astype(int)
            train_df = pd.DataFrame({"feature_x": f1, "feature_y": f2, "category": cat, "target": target})
            st.info("Loaded 200 sample synthetic records.")
        else:
            uploaded_train = st.file_uploader("Upload Training Dataset (CSV)", type=["csv"], key="train_uploader")
            if uploaded_train is not None:
                train_df = pd.read_csv(uploaded_train)
            else:
                train_df = pd.DataFrame()

        if not train_df.empty:
            st.write("Dataset Preview:", train_df.head(5))
            st.caption(f"Shape: {train_df.shape[0]} rows × {train_df.shape[1]} columns")

    with col_train_config:
        st.markdown("**Training Configuration**")
        if not train_df.empty:
            target_col = st.selectbox("Select Target Column", options=list(train_df.columns), index=len(train_df.columns)-1)
            task_type = st.selectbox("Task Type", ["classification", "regression"])
            n_estimators = st.slider("Trees (n_estimators)", min_value=10, max_value=300, value=100, step=10)

            if st.button("🚀 Train Baseline Model", type="primary", use_container_width=True):
                with st.spinner("Training baseline model pipeline..."):
                    try:
                        train_payload = {
                            "records": train_df.to_dict(orient="records"),
                            "target_column": target_col,
                            "task_type": task_type,
                            "n_estimators": n_estimators
                        }
                        resp = requests.post(f"{backend_url}/api/ml/train", json=train_payload, timeout=60)
                        if resp.status_code == 200:
                            train_res = resp.json()
                            st.success("Model trained and saved successfully!")
                            st.write("**Evaluation Metrics:**")
                            st.json(train_res.get("metrics", {}))
                            st.info(f"Model saved to: `{train_res.get('model_path')}`")
                        else:
                            st.error(f"Training failed: {resp.text}")
                    except Exception as e:
                        st.error(f"Error during training request: {str(e)}")
        else:
            st.warning("Please upload or generate a dataset first.")

# --- TAB 4: Quick Reference ---
with tab_docs:
    st.subheader("Hackathon Quick Reference & Cheat Sheet")
    st.markdown("""
    ### 🚀 Rapid Commands
    ```bash
    # 1. Start Backend Server
    uvicorn backend.main:app --reload --port 8000

    # 2. Start Frontend App
    streamlit run frontend/app.py

    # 3. Run Tests
    pytest tests/test_basic.py -v
    ```

    ### 📁 Key Project Files
    - `ai/llm.py` - Connect API keys (OpenAI / Gemini / Anthropic) or customize reasoning logic.
    - `ai/prompts.py` - Problem-specific prompt templates and formatters.
    - `ml/preprocessing.py` - Feature transformations, encoders, and cleanups.
    - `ml/model.py` - Estimator builders and training routines.
    - `ml/prediction.py` - Inference pipeline logic.
    - `backend/main.py` - FastAPI routes and schemas.
    - `frontend/app.py` - Streamlit dashboard.
    """)
