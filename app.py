
import uuid
import streamlit as st
from langgraph.types import Command

from graph import build_blog_graph


# Page configuration
st.set_page_config(
    page_title="AI Blog Studio",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Styling
st.markdown("""
<style>
    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        padding: 1.8rem;
        border-radius: 16px;
        background: linear-gradient(120deg, #172554, #4338ca);
        color: white;
        margin-bottom: 1.5rem;
    }

    .hero h1 {
        color: white;
        margin-bottom: 0.4rem;
    }

    .hero p {
        color: #e0e7ff;
        margin-bottom: 0;
    }

    div.stButton > button {
        border-radius: 8px;
        min-height: 2.7rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# Keep one graph instance # across Streamlit reruns
@st.cache_resource
def get_graph():
    return build_blog_graph()


graph = get_graph()


# Session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "stage" not in st.session_state:
    st.session_state.stage = "input"

if "topic" not in st.session_state:
    st.session_state.topic = ""

if "audience" not in st.session_state:
    st.session_state.audience = ""

if "error" not in st.session_state:
    st.session_state.error = None


def get_config():
    return {
        "configurable": {
            "thread_id": st.session_state.thread_id
        }
    }


def update_stage(result):
    """Detect the next human-review checkpoint."""
    interrupts = result.get("__interrupt__", [])

    if interrupts:
        payload = interrupts[0].value
        checkpoint = payload.get("state", "")

        if checkpoint == "researcher_Review":
            st.session_state.stage = "research_review"
        elif checkpoint == "draft_Review":
            st.session_state.stage = "draft_review"
        return

    snapshot = graph.get_state(get_config())
    values = snapshot.values

    if values.get("final_blog"):
        st.session_state.stage = "done"


def resume_graph(action, feedback=""):
    """Resume the paused graph with human feedback."""
    try:
        result = graph.invoke(
            Command(resume={
                "action": action,
                "feedback": feedback,
            }),
            config=get_config(),
        )

        update_stage(result)
        st.session_state.error = None

    except Exception as exc:
        st.session_state.error = str(exc)


def current_values():
    return graph.get_state(get_config()).values


# Header
st.markdown("""
<div class="hero">
    <h1>✍️ AI Blog Studio</h1>
    <p>
        Research, write, review and polish blogs using
        your LangGraph multi-agent workflow.
    </p>
</div>
""", unsafe_allow_html=True)


# Sidebar
with st.sidebar:
    st.title("Workflow")

    steps = [
        ("1", "Blog details"),
        ("2", "Research review"),
        ("3", "Draft review"),
        ("4", "Final blog"),
    ]

    for number, label in steps:
        st.write(f"**{number}.** {label}")

    st.divider()

    st.caption("Powered by LangGraph, LangChain and Groq")

    if st.button("Start a new blog", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.stage = "input"
        st.session_state.topic = ""
        st.session_state.audience = ""
        st.session_state.error = None
        st.rerun()


if st.session_state.error:
    st.error(st.session_state.error)


# STEP 1: Blog details
if st.session_state.stage == "input":

    st.subheader("Create a new blog")
    st.write("Tell your agents what you want to write about.")

    with st.form("blog_form"):
        topic = st.text_input(
            "Blog topic",
            placeholder="e.g. How Generative AI is changing software development",
        )

        audience = st.selectbox(
            "Target audience",
            [
                "Beginners",
                "Students",
                "Software developers",
                "Business professionals",
                "General audience",
            ],
        )

        submitted = st.form_submit_button(
            "Start generating →",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not topic.strip():
            st.warning("Please enter a blog topic.")
        else:
            st.session_state.topic = topic.strip()
            st.session_state.audience = audience

            with st.spinner("Researcher agent is preparing your outline..."):
                try:
                    result = graph.invoke(
                        {
                            "topic": st.session_state.topic,
                            "audience": st.session_state.audience,
                        },
                        config=get_config(),
                    )
                    update_stage(result)
                    st.rerun()

                except Exception as exc:
                    st.session_state.error = str(exc)
                    st.rerun()


# STEP 2: Research review
elif st.session_state.stage == "research_review":

    values = current_values()

    st.subheader("Step 2 — Review research")
    st.caption(f"Topic: {st.session_state.topic}")

    st.markdown("### Research outline")

    st.markdown(values.get("research", "No research available yet."))

    st.divider()

    st.write("Does this research outline look good?")

    with st.form("research_review_form"):
        research_feedback = st.text_area(
            "Feedback for the researcher",
            placeholder=(
                "Optional: Ask for more statistics, examples, "
                "simpler explanations, or missing points."
            ),
        )

        col1, col2 = st.columns(2)

        with col1:
            approve_research = st.form_submit_button(
                "Approve research ✓",
                type="primary",
                use_container_width=True,
            )

        with col2:
            revise_research = st.form_submit_button(
                "Revise research",
                use_container_width=True,
            )

    if approve_research:
        with st.spinner("Writer agent is generating your blog..."):
            resume_graph("approve")
            st.rerun()

    if revise_research:
        if not research_feedback.strip():
            st.warning("Enter feedback before requesting a revision.")
        else:
            with st.spinner("Researcher agent is revising the outline..."):
                resume_graph(
                    "revise",
                    research_feedback.strip(),
                )
                st.rerun()


# STEP 3: Draft review
elif st.session_state.stage == "draft_review":

    values = current_values()

    st.subheader("Step 3 — Review your blog draft")
    st.caption(f"Topic: {st.session_state.topic}")

    st.markdown("### Blog draft")

    st.markdown(values.get("draft", "No draft available yet."))

    st.divider()

    revision_count = values.get("revision_count", 0)
    st.caption(f"Draft revisions used: {revision_count} / 3")

    with st.form("draft_review_form"):
        draft_feedback = st.text_area(
            "Feedback for the writer",
            placeholder=(
                "e.g. Make the introduction stronger, add examples, "
                "or simplify the language."
            ),
        )

        col1, col2 = st.columns(2)

        with col1:
            approve_draft = st.form_submit_button(
                "Approve and polish ✓",
                type="primary",
                use_container_width=True,
            )

        with col2:
            revise_draft = st.form_submit_button(
                "Request revision",
                use_container_width=True,
            )

    if approve_draft:
        with st.spinner("Editor agent is polishing your blog..."):
            resume_graph("approve")
            st.rerun()

    if revise_draft:
        if not draft_feedback.strip():
            st.warning("Enter feedback before requesting a revision.")
        elif revision_count >= 3:
            st.warning(
                "The revision limit has been reached. "
                "Approve the draft to continue to editing."
            )
        else:
            with st.spinner("Writer agent is revising your blog..."):
                resume_graph("revise", draft_feedback.strip())
                st.rerun()


# STEP 4: Final blog
elif st.session_state.stage == "done":

    values = current_values()
    final_blog = values.get("final_blog", "")

    st.subheader("Step 4 — Your published blog")
    st.success("Your blog has been generated and polished!")

    st.markdown(f"**Topic:** {st.session_state.topic}")
    st.markdown(f"**Audience:** {st.session_state.audience}")

    tab1, tab2 = st.tabs(["Preview", "Markdown"])

    with tab1:
        st.markdown(final_blog)

    with tab2:
        st.code(final_blog, language="markdown")

    st.download_button(
        label="Download blog (.md)",
        data=final_blog,
        file_name="generated_blog.md",
        mime="text/markdown",
        type="primary",
        use_container_width=True,
    )

    if st.button("Create another blog", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.stage = "input"
        st.session_state.topic = ""
        st.session_state.audience = ""
        st.session_state.error = None
        st.rerun()
