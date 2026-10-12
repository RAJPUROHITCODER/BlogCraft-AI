from pydantic import BaseModel

class BlogState(BaseModel):
    # user Input
    topic : str= ""
    audience : str =""

    ## Reacher Output
    research : str = ""
    research_feedback : str = ""


    #writer output

    draft : str = ""
    draft_feedback : str = ""


    #editor Output
    final_blog: str = ""

    revision_count : int =0
