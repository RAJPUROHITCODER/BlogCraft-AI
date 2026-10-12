from langgraph.graph  import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
from typing import Literal
from state import BlogState
from agents import researcher_agent,writer_agent, editor_agent,get_llm

MAX_REVISION=3


def researcher_node(state:BlogState):
    """"
    Researcher agent generates (or revises) the research outlines
    """
    llm =get_llm()

    researcher_data=researcher_agent(
        llm=llm,
        topic=state.topic,
        audience=state.audience,
        feedback=state.research_feedback
    )
    state.research=researcher_data
    state.research_feedback=""
    
    return state

def human_review_research_node(state:BlogState):
    """
    Pause and ask the human to approve the research or send the feedback
    """
    decision=interrupt({
        "state":"researcher_Review",
        "research":state.research,
        "instructions":(
            "Reply with 'approve' to continue to writing",
            "or describe what to chnage to send it back to the researcher."
        )
    })
    if isinstance(decision,dict):
        action=decision.get("action","approve")
        feedback= decision.get("feedback","")
    else:
        text=str(decision)
        action="approve" if text.lower() in ["approve","approved","ok","yes","process",""] else "revise"
        feedback="" if action== "approve" else text
    state.research_feedback=feedback

    return state

def writer_node(state:BlogState):
    """"
    writer agent generates (or revises)
    """
    llm =get_llm()

    draft_data=writer_agent(
        llm=llm,
        topic=state.topic,
        audience=state.audience,
        research=state.research,
        feedback=state.draft_feedback
    )
    state.draft=draft_data
    state.draft_feedback=""
    
    return state


def human_review_draft_node(state:BlogState):
    """
    Pause and ask the human to approve the draft or send the feedback
    """
    decision=interrupt({
        "state":"draft_Review",
        "draft":state.draft,
        "instructions":(
            "Reply with 'approve' to continue to editor",
            "or describe what to chnage to send it back to the writer."
        )
    })
    if isinstance(decision,dict):
        action=decision.get("action","approve")
        feedback= decision.get("feedback","")
    else:
        text=str(decision)
        action="approve" if text.lower() in ["approve","approved","ok","yes","process",""] else "revise"
        feedback="" if action== "approve" else text

    state.draft_feedback=feedback
    if action == "revise" and feedback:
        state.revision_count += 1
    
    return state


def editor_node(state:BlogState):
    llm=get_llm()
    final=editor_agent(
        llm=llm,
        topic=state.topic,
        draft=state.draft
    )
    state.final_blog=final
    return state


#####  conditional edges

def route_after_research_review(state:BlogState) -> Literal["research","writer"]:
    if state.research_feedback:
        return "research"
    else:
        return "writer"

def route_after_draft_review(state:BlogState)-> Literal["editor","writer"]:
    if state.draft_feedback and state.revision_count<MAX_REVISION:
        return "writer"
    else:
        return "editor"

###  build  and compile the graph
def build_blog_graph():
    builder=StateGraph(BlogState)

    #add nodes
    builder.add_node("research",researcher_node)
    builder.add_node("review_research",human_review_research_node)
    builder.add_node("writer",writer_node)
    builder.add_node("review_draft",human_review_draft_node)
    builder.add_node("editor",editor_node)

    # add edge
    builder.add_edge(START,"research")
    builder.add_edge("research","review_research")
    builder.add_conditional_edges("review_research",route_after_research_review,
                                  {"research":"research","writer":"writer"})
    builder.add_edge("writer",'review_draft')
    builder.add_conditional_edges("review_draft",route_after_draft_review,
                                  {"writer":"writer","editor":"editor"}
                                  )
    builder.add_edge("editor",END)

    GRAPH=builder.compile(checkpointer=InMemorySaver())
    return GRAPH
    
    