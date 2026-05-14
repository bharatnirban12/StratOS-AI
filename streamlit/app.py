from aiokafka.record import legacy_records
from aiokafka.record import legacy_records
from aiokafka.record import legacy_records
from aiokafka.record import legacy_records
from fastapi import responses
from fastapi import responses
import os
import time
import json
import requests
import streamlit as st
from datetime import datetime, date
from typing import Dict, Any, Optional
from streamlit.components.v1 import html
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="StratOS AI",
    page_icon="assets/logo1.png",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =====================================================
# API CONFIG
# =====================================================

API_BASE = os.getenv("API_GATEWAY_URL", "http://localhost:8000")



# =====================================================
# CAPABILITY UI MAP
# =====================================================

CAPABILITY_UI = {
    "business_blueprinting": ("📋", "Business Blueprint"),
    "market_analysis": ("📊", "Market Analysis"),
    "financial_projection": ("💰", "Financial Projection"),
    "technical_architecture": ("🧠", "Technical Architecture"),
    "operations_planning": ("⚙️", "Operations Planning"),
    "growth_strategy": ("🚀", "Growth Strategy"),
    "risk_assessment": ("⚖️", "Risk Assessment"),
    "strategic_vision": ("🧠", "Strategic Vision"),
    "supply_chain_design": ("🚚", "Supply Chain"),

    # Runtime fallback IDs
    "architect": ("📋", "Business Blueprint"),
    "market": ("📊", "Market Analysis"),
    "finance": ("💰", "Financial Projection"),
    "ml": ("🧠", "Technical Architecture"),
    "execution": ("⚙️", "Operations Planning"),
    "product": ("🚀", "Growth Strategy"),
    "evaluator": ("⚖️", "Risk Assessment"),
    "ceo": ("🧠", "Strategic Vision"),
}


# =====================================================
# EXECUTION LAYERS
# =====================================================

EXECUTION_LAYERS = [
    ["business_blueprinting"],
    [
        "market_analysis",
        "technical_architecture",
        "operations_planning",
        "supply_chain_design",
    ],
    [
        "financial_projection",
        "growth_strategy",
    ],
    ["risk_assessment"]
]


# =====================================================
# SESSION STATE
# =====================================================


def init_state():
    defaults = {
        "auth_token": None,
        "active_simulation": None,
        "simulation_data": None,
        "history": [],
        "last_poll": 0,
        "debug_mode": False,
        "latest_timestamp": 0,
        "auth_mode": "login",
        "view": "main", # "main" or "settings"
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# =====================================================
# GLOBAL STYLES
# =====================================================

st.markdown(
    """
<style>

.stApp {
    background-color: #F8FAFC;
}

.block-container {
    padding-top: 2rem;
}

.metric-card {
    background: white;
    border-radius: 12px;
    padding: 12px;
    border: 1.5px solid #E2E8F0;
    min-height: 140px;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.capability-card {
    background: white;
    border-radius: 18px;
    padding: 20px;
    border: 0.5px solid #E2E8F0;
    margin-bottom: 20px;
}

.status-running {
    background: #DBEAFE;
    color: #1D4ED8;
    padding: 6px 14px;
    border-radius: 999px;
    font-weight: 600;
}

.status-completed {
    background: #DCFCE7;
    color: #15803D;
    padding: 6px 14px;
    border-radius: 999px;
    font-weight: 600;
}

.status-failed {
    background: #FEE2E2;
    color: #B91C1C;
    padding: 6px 14px;
    border-radius: 999px;
    font-weight: 600;
}

.small-muted {
    color: #64748B;
    font-size: 0.9rem;
}

</style>
""",
    unsafe_allow_html=True,
)


# =====================================================
# API CLIENT
# =====================================================

class APIClient:

    @staticmethod
    def headers():
        token = st.session_state.get("auth_token")
        headers = {}

        if token:
            headers["Authorization"] = f"Bearer {token}"

        return headers

    @staticmethod
    def request(method: str, endpoint: str, **kwargs):
        url = f"{API_BASE}/{endpoint.lstrip('/')}"

        try:
            response = requests.request(
                method,
                url,
                headers=APIClient.headers(),
                timeout=20,
                **kwargs
            )

            if response.status_code == 401:
                st.session_state.auth_token = None
                return None

            try:
                return response.json()

            except Exception:

                st.error("The system is currently unavailable. Please try again later.")
                
                if st.session_state.get("debug_mode"):
                    st.write(f"Status: {response.status_code}")
                    st.code(response.text)

                return None

        except Exception as e:
            st.error(f"Backend connection failed: {e}")
            return None


# =====================================================
# HELPERS
# =====================================================


def normalize_response(data: Dict[str, Any]) -> Dict[str, Any]:
    if not data:
        return {}

    response = data.get("data", data)

    results = response.get("results", {})

    normalized_results = {}

    for key, value in results.items():

        if not isinstance(value, dict):
            value = {
                "structured_output": {
                    "raw_output": str(value)
                }
            }

        structured = (
            value.get("structured_output")
            or value.get("content")
            or value.get("data")
            or {}
        )

        if not isinstance(structured, dict):
            structured = {
                "raw_output": str(structured)
            }

        normalized_results[key] = {
            "agent_id": value.get("agent_id", key),
            "narrative": value.get("narrative", ""),
            "structured_output": structured,
            "capability": value.get("capability", key)
        }

    response["results"] = normalized_results

    return response



def freshest_state(new_data):
    if not new_data:
        return st.session_state.simulation_data

    current = st.session_state.simulation_data

    if not current:
        return new_data

    current_ts = current.get("last_updated", 0)
    new_ts = new_data.get("last_updated", 0)

    if new_ts >= current_ts:
        return new_data

    return current

def render_login():
    
    # Horizontal header using columns for proper image loading
    _, col_logo, col_text, _ = st.columns([1, 0.5, 1.3, 1])
    
    with col_logo:
        st.image("assets/logo1.png", use_container_width=True)
    
    with col_text:
        st.markdown("""
            <h1 style='margin: 0; font-size: 3rem; font-weight: 700; line-height: 1.1;'>
                StratOS AI<span style='color: #FF4B4B;'>.</span>
            </h1>
        """, unsafe_allow_html=True)
    
    st.markdown("""
        <div style='text-align: center; color: #64748B; font-size: 1.1rem; margin-bottom: 2rem;'>
            Distributed Multi-Agent Business Simulation Platform
        </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    
    with col:
        
        mode = st.session_state.auth_mode
        
        if mode == "login":
            st.markdown("<div class='auth-header'><h1>Login</h1></div>", unsafe_allow_html=True)
            
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("Email", placeholder="Enter your email")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                
                
                login_btn = st.form_submit_button("Login")
                
                if login_btn:
                    result = APIClient.request(
                        "POST", "auth/login",
                        data={"username": email, "password": password}
                    )
                    
                    if result and "access_token" in result:
                        st.session_state.auth_token = result["access_token"]
                        st.success("Welcome back!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
            
            st.markdown("<div class='auth-footer'>Don't have an account? <span id='to-signup'></span></div>", unsafe_allow_html=True)
            if st.button("Signup", key="toggle_signup"):
                st.session_state.auth_mode = "signup"
                st.rerun()
                
        else:
            st.markdown("<div class='auth-header'><h1>Signup</h1></div>", unsafe_allow_html=True)
            
            with st.form("register_form"):
                reg_name = st.text_input("Full Name", value="New User", placeholder="Enter your full name")
                reg_email = st.text_input("Email", placeholder="Enter your email")
                reg_pass = st.text_input("Create password", type="password", placeholder="At least 8 characters")
                reg_confirm = st.text_input("Confirm password", type="password", placeholder="Repeat password")
                
                # Hidden internal fields
                reg_dob = st.date_input("Date of Birth", value=date(2000,1,1), label_visibility="collapsed")
                reg_key = st.text_input("OpenRouter API Key", type="password", placeholder="sk-or-v1-...")

                signup_btn = st.form_submit_button("Signup")
                
                if signup_btn:
                    if reg_pass != reg_confirm:
                        st.error("Passwords do not match.")
                    elif len(reg_pass) < 8:
                        st.error("Password must be at least 8 characters.")
                    elif not reg_key:
                        st.error("OpenRouter Key is required. Get one at [openrouter.ai/keys](https://openrouter.ai/keys)")

                    else:
                        payload = {
                            "email": reg_email,
                            "password": reg_pass,
                            "full_name": reg_name,
                            "dob": str(reg_dob),
                            "personal_api_key": reg_key
                        }
                        result = APIClient.request("POST", "auth/register", json=payload)
                        
                        if result and "access_token" in result:
                            st.session_state.auth_token = result["access_token"]
                            st.success("Account created successfully!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            error_msg = "Registration failed"
                            if isinstance(result, dict):
                                detail = result.get("detail")
                                if isinstance(detail, list):
                                    error_msg = ". ".join([f"{e.get('loc', ['field'])[-1].replace('_', ' ').title()}: {e.get('msg')}" for e in detail])
                                else:
                                    error_msg = str(detail or "Error during registration.")
                            st.error(error_msg)

            st.markdown("<div class='auth-footer'>Already have an account? <span id='to-login'></span></div>", unsafe_allow_html=True)
            if st.button("Login", key="toggle_login"):
                st.session_state.auth_mode = "login"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
# =====================================================
# SIDEBAR
# =====================================================


def render_sidebar():

    with st.sidebar:

        col1, col2 = st.columns([1, 4])
        with col1:
            st.image("assets/logo1.png", use_container_width=True)
        with col2:
            st.markdown("<h2 style='margin: 0; font-size: 2rem; line-height: 0.5;'>StratOS AI<span style='color: #FF4B4B;'>.</span></h2>", unsafe_allow_html=True)
        st.caption(" Distributed Multi-Agent Business Simulation Platform")

        st.caption(API_BASE)

        health = APIClient.request("GET", "health")

        if health:
            st.success("API Connected")
        else:
            st.error("API Offline")

        st.divider()

        if st.button("➕ New Simulation", use_container_width=True):
            st.session_state.active_simulation = None
            st.session_state.simulation_data = None
            st.session_state.view = "main"
            st.rerun()

        st.divider()

        st.subheader("Past Simulations")

        history = APIClient.request("GET", "simulations")

        if history:
            for sim in history:
                sim_id = sim["id"]
                goal = sim.get("goal", "Untitled")
                status = sim.get("status", "unknown").upper()
                created_at = sim.get("created_at", "")[:10]
                display_goal = goal[:30] + "..." if len(goal) > 30 else goal
                status_icon = "🟢" if status == "COMPLETED" else "🟡" if status in ["STARTED", "RUNNING", "IN_PROGRESS"] else "🔴"
                btn_label = f"{status_icon} {display_goal}\n{created_at}"
                is_active = st.session_state.active_simulation == sim_id
                
                col_sim, col_del = st.columns([5, 1])
                with col_sim:
                    if st.button(btn_label, key=f"sim_{sim_id}", use_container_width=True, type="primary" if is_active else "secondary"):
                        st.session_state.active_simulation = sim_id
                        st.session_state.simulation_data = None
                        st.session_state.view = "main"
                        st.rerun()
                
                with col_del:
                    if st.button("🗑️", key=f"del_{sim_id}"):
                        APIClient.request("DELETE", f"simulation/{sim_id}")
                        if st.session_state.active_simulation == sim_id:
                            st.session_state.active_simulation = None
                            st.session_state.simulation_data = None
                        st.rerun()
        elif history == []:
             st.info("No past simulations found.")
        else:
             st.warning("⚠️ Sign in to view your history.")

        st.divider()

        if st.button("⚙️ Profile Settings", use_container_width=True):
            st.session_state.view = "settings"
            st.rerun()
        
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()


# =====================================================
# SETTINGS
# =====================================================


def render_settings():

    st.title("⚙️ Profile Settings")
    st.caption("Update your personal information and API credentials")

    # Fetch current user data
    user = APIClient.request("GET", "auth/me")
    
    if not user:
        st.error("Failed to load profile data.")
        if st.button("← Back to Dashboard"):
            st.session_state.view = "main"
            st.rerun()
        return

    with st.form("settings_form"):
        
        new_name = st.text_input(
            "Full Name", 
            value=user.get("full_name", "")
        )
        
        # Parse DOB if it exists
        current_dob = user.get("dob")
        default_dob = date(2000, 1, 1)
        if current_dob:
            try:
                default_dob = datetime.strptime(current_dob, "%Y-%m-%d").date()
            except:
                pass

        new_dob = st.date_input(
            "Date of Birth",
            value=default_dob,
            min_value=date(1950, 1, 1),
            max_value=date.today()
        )
        
        new_key = st.text_input(
            "OpenRouter API Key",
            value=user.get("personal_api_key", ""),
            type="password",
            help="Required to run AI simulations."
        )

        col1, col2 = st.columns([1, 4])
        
        with col1:
            submitted = st.form_submit_button("Save Changes")
        
        if submitted:
            
            if not new_name or not new_key:
                st.error("Name and OpenRouter API Key are required. Get one at [openrouter.ai/keys](https://openrouter.ai/keys)")
            else:
                payload = {
                    "full_name": new_name,
                    "dob": str(new_dob),
                    "personal_api_key": new_key
                }
                
                result = APIClient.request("PUT", "auth/profile", json=payload)
                
                if result:
                    st.success("Profile updated successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to update profile.")

    if st.button("← Back to Dashboard"):
        st.session_state.view = "main"
        st.rerun()


# =====================================================
# NEW SIMULATION
# =====================================================


def render_new_simulation():

    st.title("Create Simulation")

    with st.form("simulation_form"):

        goal = st.text_area(
            "Business Goal",
            height=200,
            placeholder="Describe the business idea..."
        )

        col1, col2 = st.columns(2)

        with col1:
            budget = st.number_input(
                "Budget ($)",
                min_value=1000,
                value=50000,
                step=1000
            )

        with col2:
            timeline = st.selectbox(
                "Timeline",
                [
                    "3 Months",
                    "6 Months",
                    "1 Year",
                    "2 Years",
                    "3 Years",
                    "4 Years",
                    "5 Years"
                ]
            )

        submitted = st.form_submit_button(
            "Launch",
            use_container_width=True
        )

        if submitted:

            payload = {
                "goal": goal,
                "constraints": {
                    "budget": budget,
                    "timeline": timeline
                }
            }

            result = APIClient.request(
                "POST",
                "simulate",
                json=payload
            )

            if result and "simulation_id" in result:
                st.session_state.active_simulation = result["simulation_id"]
                st.rerun()
            else:
                st.error("Failed to start simulation")


# =====================================================
# POLLING
# =====================================================


def hydrate_simulation():

    sim_id = st.session_state.active_simulation

    if not sim_id:
        return

    response = APIClient.request(
        "GET",
        f"simulation/{sim_id}"
    )

    if not response:
        return

    normalized = normalize_response(response)

    merged = freshest_state(normalized)

    st.session_state.simulation_data = merged


# =====================================================
# ORCHESTRATION HEADER
# =====================================================


def render_top_bar(data):

    status = str(data.get("status", "STARTED")).upper()

    badge_class = {
        "RUNNING": "status-running",
        "COMPLETED": "status-completed",
        "FAILED": "status-failed"
    }.get(status, "status-running")

    col1, col2 = st.columns([4, 1])

    with col1:
        st.divider()
        goal = data.get("goal", "")
        if len(goal) > 200:
            with st.expander(f"📋 **Mission:**", expanded=False):
                st.write(goal)
        else:
            st.caption(f"📋 **Mission:** {goal}")

    with col2:
        st.divider()
        st.markdown(
            f"<div class='{badge_class}'>{status}</div>",
            unsafe_allow_html=True
        )


# =====================================================
# PROGRESS
# =====================================================


def render_progress(data):

    active = data.get("active_tasks", [])
    completed = data.get("completed_tasks", [])

    total = max(
        len(completed) + len(active),
        len(data.get("results", {})),
        1
    )  
    
    progress = min(len(completed) / total, 1.0)

    st.progress(progress)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Completed", len(completed))

    with col2:
        st.metric("Active", len(active))

    with col3:
        st.metric("Progress", f"{int(progress * 100)}%")


# =====================================================
# DAG VIEW
# =====================================================


def render_execution_layers(data):

    results = data.get("results", {})
    completed = set(data.get("completed_tasks", []))
    active = set(data.get("active_tasks", []))

    st.subheader("⚙️ Execution DAG")

    layers = (
        data.get("execution_plan", {})
        .get("execution_layers", EXECUTION_LAYERS)
    )

    for idx, layer in enumerate(layers):
        
        st.markdown(f"### Layer {idx + 1}")

        cols = st.columns(len(layer))

        for i, capability in enumerate(layer):

            icon, label = CAPABILITY_UI.get(
                capability,
                ("🧩", capability)
            )

            state = "PENDING"

            if capability in completed:
                state = "COMPLETED"
            elif capability in active:
                state = "RUNNING"
            elif capability in results:
                state = "COMPLETED"

            with cols[i]:
                st.markdown(
                    f"""
<div class='metric-card'>
    <div>
        <div style='font-size: 1.1rem; margin-bottom: 4px;'>{icon}</div>
        <div style='font-weight: 700; font-size: 1.0rem; line-height: 1.2; color: #1E293B; height: 2.5em; overflow: hidden;'>
            {label}
        </div>
    </div>
    <div style='color: #64748B; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px;'>
        {state}
    </div>
</div>
""",
                    unsafe_allow_html=True
                )


# =====================================================
# FINANCE DASHBOARD
# =====================================================


def render_finance_dashboard(data):

    results = data.get("results", {})

    # Search for finance data using both old keys and new agent:capability keys
    finance = (
        results.get("financial_projection")
        or results.get("finance")
        or next((v for k, v in results.items() if "finance" in k or "financial_projection" in k), None)
    )

    if not finance:
        st.info("💰 Financial projection is still being generated...")
        return

    structured = finance.get("structured_output", {})

    assumptions = structured.get("assumptions", {})
    simulation = structured.get("simulation", {})
    risk = structured.get("risk_profile", {})

    st.subheader("💰 Financial Intelligence")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Price / Month",
            assumptions.get("price_per_month", "N/A")
        )

    with c2:
        st.metric(
            "Target Users",
            assumptions.get("target_users_year1", "N/A")
        )

    with c3:
        st.metric(
            "Marketing Budget",
            assumptions.get("marketing_budget", "N/A")
        )

    with c4:
        brate = risk.get("bankruptcy_rate", 0)
        success = round((1 - brate) * 100, 1)
        st.metric(
            "Simulation Success",
            f"{success}%"
        )

    if simulation:
        with st.expander(
            "📈 Financial Simulation Details"
        ):

            render_nested_data(simulation)




def render_nested_data(data, level=0, max_depth=3):

    # Prevent infinite / massive recursion
    if level > max_depth:
        st.caption("Additional nested data hidden...")
        return

    if isinstance(data, dict):

        for key, value in data.items():

            pretty_key = (
                key.replace("_", " ")
                .title()
            )

            # Skip internal orchestration metadata & duplicate summaries
            if key in [
                # Raw / internal structures
                "execution_plan", "raw_output", "data",
                "compiled_execution_plan", "execution_layers",
                # Orchestration metadata
                "required_capabilities", "governance_status",
                "orchestration_metrics", "is_parallel_safe",
                "total_agents", "estimated_agent_count",
                "total_capabilities", "parallel_safe",
                # Duplicate narrative summaries
                "product_summary", "market_summary",
                "strategic_vision", "reasoning",
                "narrative", "execution_summary",
                # Agent internals
                "agent_id", "capability", "status",
                "structured_output",
            ]:
                continue

            if level == 0:
                st.markdown(f"### {pretty_key}")
            else:
                st.markdown(f"**{pretty_key}**")

            render_nested_data(
                value,
                level + 1,
                max_depth
            )

    elif isinstance(data, list):

        # Prevent giant lists
        max_items = 20

        for idx, item in enumerate(data[:max_items]):

            if isinstance(item, (dict, list)):

                with st.container(border=True):

                    render_nested_data(
                        item,
                        level + 1,
                        max_depth
                    )

            else:
                st.markdown(f"- {item}")

        if len(data) > max_items:
            st.caption(
                f"... {len(data) - max_items} more items hidden"
            )

    else:

        if isinstance(data, float):
            # Only treat as percentage if it's very small and likely a rate/ratio
            # but NOT exactly 1.0 (which is often a score fallback)
            if 0 <= data < 1:
                st.write(f"{round(data * 100, 2)}%")
            else:
                st.write(f"{data:,.2f}")

        else:
            st.write(str(data))
# =====================================================
# CAPABILITY RENDERER
# =====================================================


# Phrases that indicate a fallback/generic response instead of real analysis
FALLBACK_MARKERS = [
    "fallback", "no reasoning provided", "internal agent data",
    "fallback ml architecture", "fallback execution strategy",
    "fallback product strategy", "fallback evaluation",
]


def _is_fallback(narrative: str, structured: dict) -> bool:
    """Detect if an agent returned canned fallback data instead of real analysis."""
    text = (narrative or "").lower()
    for marker in FALLBACK_MARKERS:
        if marker in text:
            return True
    # Check for suspiciously generic structured output
    if structured.get("system_architecture") == "Fallback ML architecture":
        return True
    if structured.get("execution_summary") == "Fallback execution strategy.":
        return True
    return False


def render_capabilities(data):

    results = data.get("results", {})
    active_tasks = data.get("active_tasks", [])

    st.subheader("🤖 Agent Activity Stream")

    # Defined logical flow order
    PREFERRED_ORDER = [
        "business_blueprinting", "architect",
        "strategic_vision", "ceo",
        "market_analysis", "market",
        "technical_architecture", "ml",
        "operations_planning", "execution",
        "growth_strategy", "product",
        "financial_projection", "finance",
        "risk_assessment", "evaluator"
    ]

    # Sort results by preferred order
    sorted_items = sorted(
        results.items(),
        key=lambda x: PREFERRED_ORDER.index(x[0].split(":")[-1]) 
        if x[0].split(":")[-1] in PREFERRED_ORDER else 999
    )

    for capability, result in sorted_items:
        # Capability key might be "agent:capability" or just "capability"
        cap_name = capability.split(":")[-1]
        
        icon, label = CAPABILITY_UI.get(
            cap_name,
            ("🧠", cap_name.replace("_", " ").title())
        )

        structured = result.get("structured_output", {})
        narrative = result.get("narrative", "")
        is_fb = _is_fallback(narrative, structured)

        with st.chat_message("assistant", avatar=icon):
            st.markdown(f"**{label}**")

            if is_fb:
                st.warning(
                    "⚠️ This agent used **fallback data** because the AI model "
                    "was unavailable. Results are generic placeholders, not "
                    "specific to your business idea."
                )

            if structured.get("status") == "error":
                st.error(structured.get("error_message"))
                continue

            if narrative and not is_fb:
                st.write(narrative)

            # Only show user-facing fields, skip orchestration internals
            # and fields that duplicate the narrative already shown above
            user_fields = {
                k: v for k, v in structured.items()
                if k not in [
                    # Orchestration internals
                    "execution_plan", "raw_output", "data",
                    "compiled_execution_plan", "execution_layers",
                    "required_capabilities", "governance_status",
                    "orchestration_metrics", "is_parallel_safe",
                    "total_agents", "estimated_agent_count",
                    "total_capabilities", "parallel_safe",
                    "agent_id", "capability", "status",
                    "structured_output",
                    # Narrative-duplicate fields (already shown as text above)
                    "narrative", "execution_summary",
                    "product_summary", "market_summary",
                    "strategic_vision", "reasoning",
                    "system_architecture", "architecture_overview",
                    "overview", "summary", "description",
                ]
            }

            if user_fields:
                with st.expander("View Details"):
                    render_nested_data(user_fields)

    # Show spinners for actively running agents
    for task in active_tasks:
        cap_name = task.split(":")[-1]
        icon, label = CAPABILITY_UI.get(
            cap_name,
            ("⏳", cap_name.replace("_", " ").title())
        )
        with st.chat_message("assistant", avatar=icon):
            with st.spinner(f"Agent is analyzing **{label}**..."):
                time.sleep(0.1)


# =====================================================
# VERDICT
# =====================================================


def render_verdict(data):

    results = data.get("results", {})
    status = str(data.get("status", "")).upper()

    # Fuzzy key lookup for agent:capability format
    verdict = (
        results.get("risk_assessment")
        or results.get("evaluator")
        or next((v for k, v in results.items() if "evaluator" in k or "risk_assessment" in k), None)
    )

    if not verdict:
        if status != "COMPLETED":
            st.info("⏳ Waiting for the evaluator agent to finish...")
        else:
            st.warning("⚠️ No verdict was generated for this simulation.")
        return

    structured = verdict.get("structured_output", {})

    st.subheader("⚖️ Executive Verdict")

    decision = structured.get("decision", "PENDING")
    decision_colors = {
        "APPROVE": "🟢", "CONDITIONAL_APPROVE": "🟡",
        "REJECT": "🔴", "INSUFFICIENT_DATA": "⚪"
    }
    decision_icon = decision_colors.get(decision, "⚪")

    c1, c2 = st.columns(2)

    with c1:
        st.metric("Decision", f"{decision_icon} {decision}")

    with c2:
        confidence = structured.get("confidence", 0)
        try:
            confidence = round(float(confidence) * 100, 1)
        except:
            confidence = 0
        st.metric("Confidence", f"{confidence}%")

    reasoning = structured.get("reasoning")
    if reasoning:
        st.info(reasoning)

    # Scores as a row of metrics
    scores = structured.get("scores", {})
    if scores:
        score_cols = st.columns(len(scores))
        for i, (name, val) in enumerate(scores.items()):
            with score_cols[i]:
                try:
                    st.metric(name.title(), f"{float(val):.1f}/10")
                except:
                    st.metric(name.title(), val)

    risks = structured.get("risk_factors", [])
    if risks:
        with st.expander(f"⚠️ Risk Factors ({len(risks)})"):
            for r in risks:
                st.markdown(f"- {r}")

    changes = structured.get("required_changes", [])
    if changes:
        with st.expander(f"🔧 Required Changes ({len(changes)})"):
            for c in changes:
                st.markdown(f"- {c}")


# =====================================================
# MAIN SIMULATION VIEW
# =====================================================


def render_simulation():

    hydrate_simulation()

    data = st.session_state.simulation_data

    if not data:
        st.info("⏳ Connecting to orchestration engine...")
        time.sleep(2)
        st.rerun()
        return

    status = str(data.get("status", "")).upper()
    is_running = status not in ["COMPLETED", "FAILED"]

    render_top_bar(data)

    # Live status indicator while running
    if is_running:
        active = data.get("active_tasks", [])
        completed = data.get("completed_tasks", [])
        if active:
            agent_names = [CAPABILITY_UI.get(t.split(':')[-1], ('', t.split(':')[-1]))[1] for t in active]
            st.status(f"🔄 Running: {', '.join(agent_names)} ({len(completed)} agents completed)", state="running")
        else:
            st.status(f"⏳ Dispatching next agents... ({len(completed)} completed)", state="running")

    st.divider()

    # Create clean tabs instead of a massive vertical scroll
    tab_overview, tab_agents, tab_finance, tab_verdict = st.tabs([
        "📊 Workflow & Progress", 
        "🤖 Live Agent Stream", 
        "💰 Financial Projections", 
        "⚖️ Executive Verdict"
    ])

    with tab_overview:
        render_progress(data)
        st.write("") # Spacer
        render_execution_layers(data)

    with tab_agents:
        render_capabilities(data)

    with tab_finance:
        render_finance_dashboard(data)

    with tab_verdict:
        render_verdict(data)

    if is_running:
        time.sleep(2)
        st.rerun()


# =====================================================
# MAIN APP
# =====================================================


def main():
    


    if not st.session_state.auth_token:
        # --- CUSTOM STYLES FOR AUTH ONLY ---
        st.markdown("""
            <style>
                /* White background as requested */
                [data-testid="stAppViewContainer"] {
                    background: #FFFFFF;
                }
                
                header, [data-testid="stSidebar"] {
                    display: none;
                }
                
                .auth-card {
                    background: white;
                    padding: 40px;
                    border-radius: 16px;
                    border: 1px solid #E5E7EB;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
                    color: #1F2937;
                }
                
                .auth-header {
                    text-align: center;
                    margin-bottom: 25px;
                }
                
                .auth-header h1 {
                    font-size: 26px;
                    font-weight: 700;
                    color: #111827;
                    margin: 0;
                    border: none;
                }
                
                .auth-footer {
                    text-align: center;
                    margin-top: 20px;
                    font-size: 14px;
                    color: #6B7280;
                }
                
                .auth-link {
                    color: #0271D8;
                    text-decoration: none;
                    font-weight: 600;
                    cursor: pointer;
                }
                
                .divider {
                    display: flex;
                    align-items: center;
                    text-align: center;
                    color: #9CA3AF;
                    margin: 20px 0;
                    font-size: 14px;
                }
                .divider::before, .divider::after {
                    content: '';
                    flex: 1;
                    border-bottom: 1px solid #F3F4F6;
                }
                .divider:not(:empty)::before { margin-right: .5em; }
                .divider:not(:empty)::after { margin-left: .5em; }
                

                
                div.stButton > button {
                    width: 100% !important;
                    background-color: #0271D8 !important;
                    color: white !important;
                    border: none !important;
                    padding: 10px !important;
                    font-weight: 600 !important;
                    border-radius: 8px !important;
                }
                
                button[key^="toggle_"] {
                    background: none !important;
                    color: #0271D8 !important;
                    border: none !important;
                    padding: 0 !important;
                    font-weight: 600 !important;
                    text-decoration: underline !important;
                    box-shadow: none !important;
                    width: auto !important;
                    display: inline !important;
                }
            </style>
        """, unsafe_allow_html=True)
        render_login()
        return

    # Normal layout for authenticated users
    render_sidebar()

    if st.session_state.view == "settings":
        render_settings()
    elif not st.session_state.active_simulation:
        render_new_simulation()
    else:
        render_simulation()


if __name__ == "__main__":
    main()
