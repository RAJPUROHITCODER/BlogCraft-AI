import os
from langchain_groq import ChatGroq
from langchain_core.prompts import  ChatPromptTemplate
from dotenv import load_dotenv
load_dotenv()

### Get llm
def get_llm(model_name: str ="openai/gpt-oss-20b", temperature: float =0.5):
    api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(model=model_name,temperature=temperature)
    return llm


researcher_prompt=ChatPromptTemplate.from_messages(
    [
        {"role":"system","content":"""
            'you are a researcher agent . Given a blog topic and target audience , produce a clear ,'
            structure research outline . Include: \n'
            '1. 5-7 key points the blog should cover \n'
            '2. Import facts, starts, or examples for each points \n'
            '3. suggested angle or hook\n'
            'be concise. use bullet points. Do not write the full blog yet'
        """},

        {"role":"user",'content':"topic:{topic}, Audience :{audience},{revision_hints},write the research outline now"}
    ]
)


def researcher_agent(llm:ChatGroq,topic:str,audience:str,feedback:str=""):
    revision_hints=f"The human proivded this feedback on your previous research - please address it {feedback}"
    if not feedback:
        revision_hints="this is you first attempt"
    chain = researcher_prompt | llm 
    result = chain.invoke({
        "topic":topic,
        "audience":audience,
        "revision_hints":revision_hints
    })
    return result.content              


writer_prompt=ChatPromptTemplate.from_messages(
    [
        {"role":"system","content":"""
            'you are a Blog writer agent. Using the research notes provided , write a complete engaging blog post: \n'
            'Rules:\n'
            '- Length 500-800 words\n'
            '- strucure catchy  title , intro hook , 3-5 sectors with H2 headings , conclusion \n'
            '- Tone: clear , friendly , suited to the target audience \n'
            '- use markdown formating\n'
            '- Do not add a "word count" line at the end'
        """},
        {"role":"user",'content':"""
            Topic:{topic},
            Audience:{audience},
            Research Notes: {research}
            {revision_hints}
            wrie the full blog post me
        """
         }
    ]
)



def writer_agent(llm:ChatGroq,topic:str,audience:str,research:str="", feedback:str=""):
    revision_hints=f"The human provided this feedback on your previous draft and asked for these changes:{feedback} - please apply these changes during writting the blog"
    if not feedback:
        revision_hints="this is you first attempt"
    chain = writer_prompt | llm 
    result = chain.invoke({
        "topic":topic,
        "audience":audience,
        "research":research,
        "revision_hints":revision_hints
    })
    return result.content              



editor_prompt=ChatPromptTemplate.from_messages(
    [
        {"role":"system","content":"""
            'you are a editor agent. the final quality gate before publishing \n'
            'Take the draft and produce the final polished version. specifically:\n'
            '- fix grammer,spelling, and awkward phrasing\n'
            '- Tighten wordy sentence \n'
            '- Improve flow and transition between sections\n'
            '- Make the title and intro more compelling if needed \n'
            'keep the same structure and markdown formatting \n'
            '-Blog wording should be in human wordings, bit a ai and dont use any special chars and complex words. \n'
            'Output only the final polished blog post - no commentary
        """},
        {"role":"user",'content':"""
            Topic:{topic},
            draft:{draft}
            Return the published blog post.
        """
         }
    ]
)


def editor_agent(llm:ChatGroq,topic:str,draft:str="")-> str:
    
    chain = editor_prompt | llm 
    result = chain.invoke({
        "topic":{topic},
        "draft":{draft},
    })
    return result.content              

